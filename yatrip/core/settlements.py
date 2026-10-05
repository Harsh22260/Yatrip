"""
India settlement index.

The catalogue has to cover "every small town", so the sync cannot be a
hand-written list of cities. This module pulls the settlement index straight
from OpenStreetMap via Overpass and keeps it in the database, ordered by
population, so the ingestion sweep can work through it in priority order and
resume where it left off.

India has roughly 650k villages. A full village-level sweep is a multi-day
crawl against a rate-limited public endpoint, so the index is built in pages
and the sweep is explicitly resumable and interruptible.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Iterator

from django.db import transaction

from yatrip import opendata

logger = logging.getLogger(__name__)

#: Overpass chokes on a single unbounded query for a country the size of
#: India, and the public endpoint returns 504 for anything large. The index is
#: therefore built from a grid of small bounding boxes, which each answer in a
#: few seconds. India spans roughly 6.7N-37.1N and 68E-97.5E.
INDIA_BBOX = (6.5, 68.0, 37.5, 97.5)
BAND_DEGREES = 1.5

#: Feature classes worth indexing, cheapest-first so a partial run is still
#: useful. ``village`` is last because it is enormous.
FEATURE_TIERS = (
    ("city", "town"),
    ("city", "town", "village"),
)


def _cells() -> Iterator[tuple[float, float, float, float]]:
    """Yield (south, west, north, east) cells covering India."""
    south, west, north, east = INDIA_BBOX
    step = BAND_DEGREES
    lat = south
    while lat < north:
        nxt = min(lat + step, north)
        lon = west
        while lon < east:
            yield (lat, lon, nxt, min(lon + 6.0, east))
            lon += 6.0
        lat = nxt


def _query(places: tuple[str, ...], cell: tuple[float, float, float, float],
           limit: int) -> dict[str, Any]:
    south, west, north, east = cell
    place_re = "|".join(places)
    q = (
        f"[out:json][timeout:120];\n"
        f'node["place"~"^({place_re})$"]({south},{west},{north},{east});\n'
        f"out body {limit};"
    )
    return opendata._get(
        opendata.OVERPASS_URL,
        params={"data": q},
        timeout=150,
        retries=2,
    )


def iter_settlements(
    places: tuple[str, ...] = ("city", "town"),
    *,
    max_cells: int | None = None,
    limit_per_cell: int = 500,
) -> Iterator[dict[str, Any]]:
    """
    Yield settlement dicts from a grid sweep over India, de-duplicated.

    Cells that time out are skipped rather than aborting the run, so a
    partially loaded index is still produced and the command can be re-run to
    fill the gaps.
    """
    seen: set[str] = set()
    cells = list(_cells())
    for index, cell in enumerate(cells):
        if max_cells is not None and index >= max_cells:
            return
        try:
            payload = _query(places, cell, limit_per_cell)
        except RuntimeError as exc:
            logger.warning("Overpass cell %s failed: %s", cell, str(exc)[:80])
            continue

        for el in payload.get("elements") or []:
            tags = el.get("tags") or {}
            name = tags.get("name") or tags.get("name:en")
            lat, lon = el.get("lat"), el.get("lon")
            if not name or lat is None or lon is None:
                continue
            osm_id = f"{el.get('type', 'node')}/{el.get('id')}"
            if osm_id in seen:
                continue
            seen.add(osm_id)
            yield {
                "name": name,
                "latitude": float(lat),
                "longitude": float(lon),
                "place_type": tags.get("place", ""),
                "population": int(tags["population"]) if str(tags.get("population", "")).isdigit() else None,
                "state": tags.get("state") or "",
                "osm_id": osm_id,
            }


@transaction.atomic
def store_settlements(rows: list[dict[str, Any]], replace: bool = False) -> int:
    from core.models import Settlement

    if replace:
        Settlement.objects.all().delete()

    written = 0
    batch: list[Settlement] = []
    for row in rows:
        batch.append(Settlement(**row))
    Settlement.objects.bulk_create(batch, ignore_conflicts=True, batch_size=1000)
    written = len(batch)
    return written


def top_settlements(limit: int = 50, place_type: str | None = None) -> list:
    from core.models import Settlement

    qs = Settlement.objects.all()
    if place_type:
        qs = qs.filter(place_type=place_type)
    return list(qs.order_by(*models_order())[:limit])


def models_order():
    """Settlements with a known population first, then largest first."""
    from django.db.models import Case, IntegerField, Value, When

    return (
        Case(
            When(population__isnull=False, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        ).desc(),
        "-population",
        "name",
    )
