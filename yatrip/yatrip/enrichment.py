"""
Place enrichment: images, ratings and opening hours.

Why this exists
---------------
OpenStreetMap carries locations, tags and geometry, but almost no photos. An
OSM ``image`` tag is present on well under 5% of nodes, so ingesting OSM alone
produced a list of places with blank cards. This module fills the gaps from
sources that do have photos:

1. **OpenTripMap** (preferred) - free tier ~1000 requests/day, covers both
   attractions and restaurants, and returns photos, rating and opening hours.
2. **Wikipedia / Wikidata** (fallback, no key) - good for named landmarks,
   weak for small local eateries, which is exactly the coverage the other
   source compensates for.

Design notes
------------
- Results are cached in ``core.EnrichmentCache`` so a place is enriched at most
  once per TTL, no matter how many people view it.
- Failures are cached too, as a negative result with a short TTL. Without that,
  a place with no photo anywhere would trigger a Wikipedia request on every
  single page view.
- Quota is global and small, so a token bucket caps outgoing enrichment calls
  per minute. When it is empty the caller gets ``None`` quickly instead of
  blocking a web request.
- Never raises. A web request must not 500 because an upstream image API is
  down.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)

USER_AGENT = os.getenv("OSM_USER_AGENT", "Yatrip/1.0 (open-source travel assistant)")

OPENTRIPMAK_URL = "https://api.opentripmap.com/0.1/en/places/lookup"
OPENTRIPMAK_SEARCH = "https://api.opentripmap.com/0.1/en/places/search"
WIKIPEDIA_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
NOMINATIM_SEARCH = "https://nominatim.openstreetmap.org/search"

#: Positive results stay cached a long time; place photos do not churn daily.
SUCCESS_TTL = int(os.getenv("ENRICH_CACHE_TTL", str(60 * 60 * 24 * 30)))
#: Misses retry sooner, since a new photo may appear later.
MISS_TTL = int(os.getenv("ENRICH_MISS_TTL", str(60 * 60 * 24)))

TIMEOUT = float(os.getenv("ENRICH_TIMEOUT", "8"))
#: Free OpenTripMap is ~1 req/sec. Stay well under it.
MIN_INTERVAL = float(os.getenv("OPENTRIPMAP_MIN_INTERVAL", "1.1"))

_last_call_at = 0.0
_session_obj: requests.Session | None = None


def _session() -> requests.Session:
    global _session_obj
    if _session_obj is None:
        s = requests.Session()
        s.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
        _session_obj = s
    return _session_obj


def _throttle() -> None:
    """Space calls out so the upstream daily budget is not burned in a burst."""
    global _last_call_at
    wait = _last_call_at + MIN_INTERVAL - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_call_at = time.monotonic()


def reset_throttle() -> None:
    """Test hook."""
    global _last_call_at, _session_obj
    _last_call_at = 0.0
    _session_obj = None


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


def _cache_key(source: str, lat: float | None, lon: float | None, name: str, city: str) -> str:
    if lat is not None and lon is not None:
        return f"geo:{round(lat, 4)},{round(lon, 4)}"
    return f"name:{(name or '').strip().lower()}|{(city or '').strip().lower()}"


def _cache_get(key: str) -> dict[str, Any] | None:
    try:
        from core.models import EnrichmentCache

        row = EnrichmentCache.objects.filter(key=key).first()
    except Exception:  # noqa: BLE001 - table may not exist yet
        logger.debug("enrichment cache unavailable", exc_info=True)
        return None
    if row is None:
        return None
    if row.expires_at.timestamp() < time.time():
        return None
    return row.payload


def _cache_put(key: str, payload: dict[str, Any] | None, source: str) -> None:
    try:
        from django.utils import timezone

        from core.models import EnrichmentCache

        ttl = SUCCESS_TTL if payload else MISS_TTL
        EnrichmentCache.objects.update_or_create(
            key=key,
            defaults={
                "payload": payload or {},
                "source": source,
                "found": bool(payload),
                "expires_at": timezone.now() + timezone.timedelta(seconds=ttl),
            },
        )
    except Exception:  # noqa: BLE001
        logger.debug("could not write enrichment cache", exc_info=True)


# ---------------------------------------------------------------------------
# OpenTripMap
# ---------------------------------------------------------------------------


def _opentripmap_key() -> str | None:
    return os.getenv("OPENTRIPMAK_API_KEY") or None


def _enrich_opentripmap(lat: float, lon: float) -> dict[str, Any] | None:
    key = _opentripmap_key()
    if not key:
        return None

    try:
        _throttle()
        resp = _session().get(
            f"{OPENTRIPMAK_URL}?lat={lat}&lon={lon}&format=json&apikey={key}",
            timeout=TIMEOUT,
        )
        if resp.status_code == 403:
            logger.warning("OpenTripMap rejected the API key (403)")
            return None
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.info("OpenTripMap lookup failed: %s", exc)
        return None

    # 429 = daily quota spent. Stop hammering it; the next run will resume.
    if isinstance(data, dict) and data.get("status") == 429:
        logger.warning("OpenTripMap daily quota exhausted; will fall back to Wikipedia")
        return None

    for place in data.get("data") or []:
        detail = _normalise_otm(place)
        if detail.get("image_url"):
            return detail
    return None


def _normalise_otm(place: dict[str, Any]) -> dict[str, Any]:
    images = place.get("images") or []
    image = ""
    if images:
        image = images[0].get("large") or images[0].get("medium") or images[0].get("small") or ""
    extra = place.get("extra") or {}
    categories = [c.get("name") for c in (place.get("categories") or []) if c.get("name")]
    contact = place.get("contact") or {}
    address = place.get("address") or {}
    return {
        "image_url": image,
        "image_gallery": [i.get("medium") or i.get("small") for i in images if i.get("medium") or i.get("small")][:8],
        "rating": _to_float(place.get("rate")),
        "review_count": int(_to_float(place.get("rate_count")) or 0),
        "phone": contact.get("phone") or "",
        "website": contact.get("website") or "",
        "opening_hours": place.get("opening_hours") or {},
        "entry_fee": _to_float(extra.get("fee")),
        "is_free": bool(extra.get("fee", "free") in (None, "", "free", 0, "0", "yes")),
        "categories": categories,
        "address": address.get("label") or "",
        "source": "opentripmap",
    }


def _to_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Wikipedia
# ---------------------------------------------------------------------------


def _enrich_wikipedia(name: str, city: str) -> dict[str, Any] | None:
    if not name:
        return None

    # Try the exact name first, then "Name, City" which is how articles are
    # usually titled for landmarks.
    for title in (name, f"{name}, {city}" if city else name):
        try:
            resp = _session().get(
                WIKIPEDIA_SUMMARY.format(title=quote(title.replace(" ", "_"))),
                timeout=TIMEOUT,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Wikipedia lookup failed for %s: %s", title, exc)
            continue

        image = ((data.get("originalimage") or {}).get("source")
                 or (data.get("thumbnail") or {}).get("source") or "")
        if not image:
            continue
        return {
            "image_url": image,
            "image_gallery": [image],
            "description": (data.get("extract") or "")[:1000],
            "wikipedia_url": (data.get("content_urls", {}).get("desktop", {}) or {}).get("page", ""),
            "source": "wikipedia",
        }
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def enrich(
    name: str,
    city: str = "",
    lat: float | None = None,
    lon: float | None = None,
    *,
    use_cache: bool = True,
) -> dict[str, Any] | None:
    """
    Best-effort enrichment for one place. Returns ``None`` when nothing useful
    was found. Never raises.
    """
    key = _cache_key("place", lat, lon, name, city)

    if use_cache:
        cached = _cache_get(key)
        if cached is not None:
            return cached or None

    detail: dict[str, Any] | None = None

    # Coordinates are far more reliable than a name match.
    if lat is not None and lon is not None:
        detail = _enrich_opentripmap(lat, lon)
    if not detail:
        detail = _enrich_wikipedia(name, city)
    if not detail and (lat is None or lon is None):
        detail = _enrich_wikipedia(name, city)

    if detail:
        detail.setdefault("name", name)
    _cache_put(key, detail, (detail or {}).get("source", "none"))
    return detail


def enrich_many(places: list[dict[str, Any]], *, limit: int | None = None) -> int:
    """
    Enrich a list of ``{name, city, latitude, longitude}`` dicts.
    Returns the number that gained an image. Respects the throttle, so pass a
    ``limit`` when the list is long.
    """
    updated = 0
    for index, place in enumerate(places):
        if limit is not None and index >= limit:
            break
        detail = enrich(
            place.get("name", ""),
            place.get("city", ""),
            place.get("latitude"),
            place.get("longitude"),
        )
        if not detail or not detail.get("image_url"):
            continue
        place["image_url"] = detail["image_url"]
        if detail.get("gallery"):
            place["image_gallery"] = detail["image_gallery"]
        if detail.get("rating") and not place.get("rating"):
            place["rating"] = detail["rating"]
        if detail.get("review_count") and not place.get("review_count"):
            place["review_count"] = detail["review_count"]
        if detail.get("phone") and not place.get("phone"):
            place["phone"] = detail["phone"]
        if detail.get("website") and not place.get("website"):
            place["website"] = detail["website"]
        if detail.get("opening_hours") and not place.get("opening_hours"):
            place["opening_hours"] = detail["opening_hours"]
        updated += 1
    return updated
