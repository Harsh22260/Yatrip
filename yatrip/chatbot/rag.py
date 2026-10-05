"""
Shared RAG ingestion for the Yatrip knowledge base.

Both ``manage.py ingest_data`` and ``manage.py sync_rag`` delegate here, so
the write side and the query side can never disagree about which embedding
model or index they are using.

Key invariants:
  * The embedding model and index dimension come from ``django.conf.settings``
    (env driven). Writing with one model and reading with another silently
    ruins retrieval, so there is exactly one place they are defined.
  * Every document gets a deterministic id, so re-running a sync upserts
    instead of accumulating near-duplicate vectors.
  * ``source`` metadata is a single canonical vocabulary shared with the MCP
    ``search_knowledge_base`` tool.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Callable, Iterable, Sequence

from django.conf import settings
from django.db.models import Model, QuerySet

from yatrip.retry import call_with_backoff

logger = logging.getLogger(__name__)

# Single source of truth for metadata labels.
SOURCES = {
    "hotel": "hotel",
    "food": "food",
    "attraction": "attraction",
    "rental": "rental",
    "transport": "transport",
}

CHOICES = tuple(SOURCES) + ("all",)

BATCH_SIZE = int(os.getenv("RAG_BATCH_SIZE", "50"))
# Gemini's free tier allows ~100 embed requests/minute, so pace the batches and
# back off hard whenever the quota is exhausted.
REQUEST_INTERVAL_SECONDS = float(os.getenv("RAG_REQUEST_INTERVAL", "0.8"))
MAX_RETRIES = int(os.getenv("RAG_MAX_RETRIES", "6"))


# ---------------------------------------------------------------------------
# Vector store plumbing
# ---------------------------------------------------------------------------


class RagConfigurationError(RuntimeError):
    """Raised when the knowledge base cannot be used as configured."""


def ensure_configured() -> None:
    missing = [
        name
        for name, value in (
            ("PINECONE_API_KEY", settings.PINECONE_API_KEY),
            ("GEMINI_API_KEY", settings.GEMINI_API_KEY),
        )
        if not value
    ]
    if missing:
        raise RagConfigurationError(
            "Missing API keys in .env: " + ", ".join(missing)
        )


def get_embeddings():
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(
        model=settings.GEMINI_EMBEDDING_MODEL,
        google_api_key=settings.GEMINI_API_KEY,
    )


def get_vector_store():
    from langchain_pinecone import PineconeVectorStore

    return PineconeVectorStore(
        index_name=settings.PINECONE_INDEX_NAME,
        embedding=get_embeddings(),
        pinecone_api_key=settings.PINECONE_API_KEY,
    )


def get_pinecone_client():
    from pinecone import Pinecone

    return Pinecone(api_key=settings.PINECONE_API_KEY)


def ensure_index(*, recreate: bool = False) -> dict[str, Any]:
    """
    Make sure the Pinecone index exists and matches the configured dimension.

    Returns a small status dict describing what happened.
    """
    ensure_configured()
    client = get_pinecone_client()
    index_name = settings.PINECONE_INDEX_NAME
    expected = settings.PINECONE_EMBEDDING_DIMENSION

    existing = [entry["name"] for entry in client.list_indexes()]

    if index_name in existing:
        stats = client.describe_index(index_name)
        if stats.dimension != expected:
            if not recreate:
                raise RagConfigurationError(
                    f"Index {index_name!r} has dimension {stats.dimension} but "
                    f"{settings.GEMINI_EMBEDDING_MODEL} produces {expected}-dim "
                    f"vectors. Re-run with --recreate to rebuild the index."
                )
            logger.warning(
                "Dropping index %s: dimension %s != %s", index_name, stats.dimension, expected
            )
            client.delete_index(index_name)
            existing = [name for name in existing if name != index_name]

    if index_name not in existing:
        from pinecone import ServerlessSpec

        logger.info(
            "Creating index %s (dimension=%s, metric=cosine)",
            index_name,
            expected,
        )
        client.create_index(
            name=index_name,
            dimension=expected,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        return {"created": True, "dimension": expected}

    return {"created": False, "dimension": expected}


# ---------------------------------------------------------------------------
# Document builders
# ---------------------------------------------------------------------------


def _fmt(value: Any, suffix: str = "") -> str:
    if value in (None, ""):
        return ""
    return f"{value}{suffix}"


def _hotel_documents(queryset: QuerySet) -> list[dict[str, Any]]:
    documents = []
    for hotel in queryset.prefetch_related("room_types__rate_plans"):
        lines = [
            f"Hotel: {hotel.name}",
            f"Address: {hotel.address}",
            f"Rating: {hotel.rating or 0} / 5",
            f"Verified listing: {'yes' if hotel.is_verified else 'no'}",
        ]
        if hotel.description:
            lines.append(f"Description: {hotel.description.strip()}")

        rooms = list(hotel.room_types.all())
        if rooms:
            lines.append("Rooms and rates:")
            for room in rooms:
                line = (
                    f"- {room.name}: Rs {room.base_price} per night, "
                    f"sleeps {room.capacity}, {room.total_units} units"
                )
                plans = list(room.rate_plans.all())
                if plans:
                    plan_text = ", ".join(
                        f"{plan.name} (Rs {plan.get_final_price()}, "
                        f"{'refundable' if plan.refundable else 'non-refundable'})"
                        for plan in plans
                    )
                    line += f". Rate plans: {plan_text}"
                lines.append(line)
        else:
            lines.append("No room types have been published for this hotel yet.")

        documents.append(
            {
                "id": f"hotel-{hotel.pk}",
                "page_content": "\n".join(lines),
                "metadata": {
                    "source": SOURCES["hotel"],
                    "id": hotel.pk,
                    "title": hotel.name,
                    "city": hotel.address,
                    "price_inr": str(
                        min(
                            (room.base_price for room in rooms if room.base_price is not None),
                            default="",
                        )
                    ),
                    "url": f"/hotels/{hotel.pk}",
                },
            }
        )
    return documents


def _attraction_documents(queryset: QuerySet) -> list[dict[str, Any]]:
    documents = []
    for attraction in queryset:
        fee = (
            "Free entry"
            if attraction.is_free
            else _fmt(attraction.entry_fee, " INR entry fee")
            or "Paid entry (fee unknown)"
        )
        lines = [
            f"Attraction: {attraction.name}",
            f"Category: {attraction.get_category_display()}",
            f"Address: {attraction.address}",
            f"Location: {attraction.city}, {attraction.state}, {attraction.country}",
            f"Rating: {attraction.rating or 0} / 5 from {attraction.review_count} reviews",
            f"Entry: {fee}",
        ]
        hours = (attraction.opening_hours or {}).get("raw")
        if hours:
            lines.append(f"Opening hours: {hours}")
        if attraction.phone:
            lines.append(f"Phone: {attraction.phone}")
        if attraction.description:
            lines.append(f"Description: {attraction.description.strip()[:600]}")

        documents.append(
            {
                "id": f"attraction-{attraction.pk}",
                "page_content": "\n".join(lines),
                "metadata": {
                    "source": SOURCES["attraction"],
                    "id": attraction.pk,
                    "title": attraction.name,
                    "city": attraction.city,
                    "category": attraction.category,
                    "url": f"/attractions/{attraction.pk}",
                },
            }
        )
    return documents


def _food_documents(queryset: QuerySet) -> list[dict[str, Any]]:
    documents = []
    for place in queryset:
        veg = {True: "vegetarian", False: "non-vegetarian", None: "vegetarian and non-vegetarian"}[
            place.is_veg
        ]
        lines = [
            f"Food place: {place.name}",
            f"Type: {place.get_category_display()}",
            f"Cuisine: {place.get_cuisine_display()}",
            f"Address: {place.address}",
            f"Location: {place.city}, {place.state}",
            f"Rating: {place.rating or 0} / 5 from {place.review_count} reviews",
            f"Price level: {'Rs' * place.price_level if place.price_level else 'Rs'}",
            f"Diet: {veg}",
        ]
        if place.avg_cost_for_two:
            lines.append(f"Average cost for two: Rs {place.avg_cost_for_two}")
        if place.is_open_now:
            lines.append("Currently marked open")
        if place.home_delivery:
            lines.append("Offers home delivery")
        if place.takeaway:
            lines.append("Offers takeaway")
        hours = (place.opening_hours or {}).get("raw")
        if hours:
            lines.append(f"Opening hours: {hours}")
        if place.description:
            lines.append(f"Description: {place.description.strip()[:400]}")

        documents.append(
            {
                "id": f"food-{place.pk}",
                "page_content": "\n".join(lines),
                "metadata": {
                    "source": SOURCES["food"],
                    "id": place.pk,
                    "title": place.name,
                    "city": place.city,
                    "category": place.category,
                    "cuisine": place.cuisine,
                    "url": f"/food/{place.pk}",
                },
            }
        )
    return documents


def _rental_documents(queryset: QuerySet) -> list[dict[str, Any]]:
    documents = []
    for rental in queryset.prefetch_related("amenities"):
        amenities = [amenity.name for amenity in rental.amenities.all()]
        lines = [
            f"Rental: {rental.name}",
            f"Type: {rental.get_rental_type_display()}",
            f"Address: {rental.address}",
            f"Monthly rent: Rs {rental.price_per_month}",
            f"Rooms available: {rental.available_rooms}",
            f"Verified listing: {'yes' if rental.is_verified else 'no'}",
        ]
        if amenities:
            lines.append(f"Amenities: {', '.join(amenities)}")
        if rental.description:
            lines.append(f"Description: {rental.description.strip()[:400]}")

        documents.append(
            {
                "id": f"rental-{rental.pk}",
                "page_content": "\n".join(lines),
                "metadata": {
                    "source": SOURCES["rental"],
                    "id": rental.pk,
                    "title": rental.name,
                    "city": rental.address,
                    "price_inr": str(rental.price_per_month),
                    "url": f"/rentals/{rental.pk}",
                },
            }
        )
    return documents


def _transport_documents(queryset: QuerySet) -> list[dict[str, Any]]:
    documents = []
    for node in queryset:
        lines = [
            f"Transport hub: {node.name}",
            f"Type: {node.get_node_type_display()}",
            f"City: {node.city}",
        ]
        if node.address:
            lines.append(f"Address: {node.address}")

        documents.append(
            {
                "id": f"transport-{node.pk}",
                "page_content": "\n".join(lines),
                "metadata": {
                    "source": SOURCES["transport"],
                    "id": node.pk,
                    "title": node.name,
                    "city": node.city,
                    "node_type": node.node_type,
                    "url": "/transport",
                },
            }
        )
    return documents


# ---------------------------------------------------------------------------
# Sync entry point
# ---------------------------------------------------------------------------


def _active_queryset(model_name: str) -> QuerySet:
    """Only index records the app considers live."""
    from attractions.models import Attraction
    from food.models import FoodPlace
    from hotels.models import Hotel
    from rentals.models import Rental
    from transport.models import TransportNode

    model_map: dict[str, Model] = {
        "hotel": Hotel,
        "food": FoodPlace,
        "attraction": Attraction,
        "rental": Rental,
        "transport": TransportNode,
    }
    model = model_map[model_name]
    if hasattr(model, "is_active"):
        return model.objects.filter(is_active=True)
    return model.objects.all()


def sync(models: Sequence[str] = ("all",), *, recreate: bool = False) -> dict[str, int]:
    """
    Embed the selected models into Pinecone and return per-model counts.

    ``models`` accepts any of 'hotel', 'food', 'attraction', 'rental',
    'transport' or 'all'.
    """
    ensure_index(recreate=recreate)

    requested = list(dict.fromkeys(models)) or ["all"]
    if "all" in requested:
        requested = list(SOURCES)

    builders: dict[str, Callable[[QuerySet], list[dict[str, Any]]]] = {
        "hotel": _hotel_documents,
        "food": _food_documents,
        "attraction": _attraction_documents,
        "rental": _rental_documents,
        "transport": _transport_documents,
    }

    vector_store = get_vector_store()
    counts: dict[str, int] = {}

    for name in requested:
        builder = builders.get(name)
        if builder is None:
            logger.warning("Unknown model %r, skipping", name)
            continue

        try:
            payload = builder(_active_queryset(name))
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to read %s rows: %s", name, exc)
            counts[name] = 0
            continue

        if not payload:
            counts[name] = 0
            continue

        _upsert(vector_store, payload, name)
        counts[name] = len(payload)

    return counts


def _upsert(vector_store, payload: list[dict[str, Any]], label: str) -> None:
    """
    Upsert documents by their deterministic ids.

    Pinecone requires the ids to be unique per namespace, so they are
    de-duplicated here before batching.
    """
    from langchain_core.documents import Document

    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for item in payload:
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        unique.append(item)

    for start in range(0, len(unique), BATCH_SIZE):
        batch = unique[start : start + BATCH_SIZE]
        documents = [
            Document(
                page_content=item["page_content"],
                metadata=item["metadata"],
                id=item["id"],
            )
            for item in batch
        ]
        ids = [item["id"] for item in batch]
        call_with_backoff(
            lambda docs=documents, doc_ids=ids: vector_store.add_documents(docs, ids=doc_ids),
            label=f"{label} batch {start // BATCH_SIZE + 1}",
            max_retries=MAX_RETRIES,
        )
        logger.info("%s: embedded %d-%d", label, start + 1, start + len(batch))
        time.sleep(REQUEST_INTERVAL_SECONDS)


def count_indexed_vectors() -> int:
    """Total vectors currently in the index, or 0 if it cannot be read."""
    try:
        client = get_pinecone_client()
        stats = client.Index(settings.PINECONE_INDEX_NAME).describe_index_stats()
        return int(stats.get("total_vector_count", 0))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not read index stats: %s", exc)
        return 0


def iter_sources() -> Iterable[str]:
    return SOURCES.keys()
