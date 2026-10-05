"""
Transport hubs from OpenStreetMap.

The proposal needs bus stands, auto stands, shared taxis, metro, railway and
airports. OSM tags these inconsistently across India, so rather than one
guess this builds a tag matrix and keeps whatever matches.

Run for one city:

    python manage.py fetch_transport --city Bengaluru
    python manage.py fetch_transport --lat 12.97 --lon 77.59 --radius 25
"""

from __future__ import annotations

import json
import logging
import math
import re
import tempfile
import time
from pathlib import Path
from typing import Any

import requests
from django.utils import timezone

from yatrip import opendata

from ..models import TransportNode

logger = logging.getLogger(__name__)

#: Our node_type -> list of (osm selector, tag key, expected value) rules.
#: The first rule that matches decides the type.
#:
#: Order matters. ``public_transport=station`` is deliberately *not* a metro
#: rule: in OSM it also covers bus stations, so putting it early labelled 400+
#: Bengaluru bus stops as "metro". Metro is identified by ``station=subway``.
TAG_MATRIX: tuple[tuple[str, str, str], ...] = (
    ("metro", "station", "subway"),
    ("rail", "railway", "station"),
    ("rail", "railway", "halt"),
    ("rail", "amenity", "railway_station"),
    ("airport", "aeroway", "aerodrome"),
    ("airport", "amenity", "aerodrome"),
    ("ferry", "amenity", "ferry_terminal"),
    ("auto", "amenity", "taxi_stand"),
    ("bus", "amenity", "bus_station"),
)

#: Generic fallback tags. These are checked *last*, after the operator and name
#: hints, because ``public_transport=platform`` matches almost every bus stop and
#: would otherwise shadow the operator ("BMTC", "KSRTC") that identifies it.
#: Checked only after the mode flags have had their chance, so a real
#: ``public_transport=platform`` with ``bus=yes`` never lands here.
WEAK_TAG_RULES: tuple[tuple[str, str, str], ...] = (
    ("bus", "public_transport", "station"),
    ("other", "public_transport", "platform"),
    ("other", "public_transport", "stop_position"),
)

#: Queried separately from the matrix: entrance nodes are one-per-street-door
#: and would multiply every station by 4-8, so they are only taken when the
#: parent station is absent.
ENTRANCE_RULE = ("metro", "railway", "subway_entrance")

#: Bus stops and other plain stops are extremely numerous — a dense Indian city
#: has thousands inside a 25 km box. The cap exists only so one response cannot
#: exhaust memory and the mirror's rate budget; it is deliberately high because
#: the requirement is "show all stops", not "show the interchange list".
STOP_MAX_PER_QUERY = 4000

#: Pause between Overpass queries within one area sync. Generous on purpose:
#: the public instance answers 429 when a burst arrives, and a rejected tile
#: means missing bus stops for the traveller.
OVERPASS_PATIENCE_SEC = 6.0

#: Base for the exponential wait after a 429/504. Doubles per attempt, so the
#: retries for one chunk span roughly 6s, 12s and 24s.
OVERPASS_BACKOFF_SEC = 6.0

#: Edge length of one tile in the high-cardinality stop sweep. Small enough
#: that a dense city tile still answers in a couple of seconds.
STOP_TILE_KM = 7.5

AMENITY_KEYS = (
    "atm", "wc", "toilets", "waiting_room", "waiting_area", "bench", "shelter",
    "parking", "bicycle_parking", "cafe", "food_court", "shop", "ticket",
)


#: State transport operators. A stop tagged only ``public_transport=platform``
#: is unclassifiable on tags alone, but nearly every Indian bus stop names its
#: operator, and those operators are bus companies.
BUS_OPERATOR_HINTS = (
    "bmtc", "ksrtc", "tsrtc", "apsrtc", "gsrtc", "msrtc", "ksrtc", "apsrtc",
    "best underpass", "mysore", "northwestern", "karnataka", "andhra pradesh",
    "tamil nadu", "gujarat", "maharashtra", "rajasthan", "uttar pradesh",
    "bihar", "west bengal", "kerala", "punjab", "haryana", "odisha",
    "telangana", "mp transport", "m.p. transport", "goa", "assam", "jharkhand",
    "chhattisgarh", "uttarakhand", "himachal", "j&k", "ladakh", "goa transport",
)

#: Keywords in a hub name that identify a road auto-rickshaw stand.
AUTO_NAME_HINTS = ("auto", "rickshaw", "autorickshaw", "e-rickshaw", "phool", "three wheeler")


def _classify(tags: dict[str, str]) -> str | None:
    for node_type, key, value in TAG_MATRIX:
        if tags.get(key) == value:
            return node_type

    # Nothing specific matched. Infer from the operator and name, because a
    # stop tagged only ``public_transport=platform`` is unclassifiable on tags
    # alone yet almost always names a bus company.
    blob = " ".join(
        str(tags.get(k, "")) for k in ("operator", "name", "name:en")
    ).lower()
    if any(h in blob for h in BUS_OPERATOR_HINTS):
        return "bus"
    if any(h in blob for h in AUTO_NAME_HINTS):
        return "auto"

    # Mode flags before the weak fallback: ``public_transport=platform`` on its
    # own is a dead end, and letting it win first is what used to bury 29 real
    # bus stops and 16 metro platforms in the "other" bucket.
    by_mode = _classify_by_mode(tags)
    if by_mode:
        return by_mode

    if tags.get("highway") == "bus_stop":
        return "bus"

    for node_type, key, value in WEAK_TAG_RULES:
        if tags.get(key) == value:
            return node_type
    return None


#: Ordered because a stop can serve more than one mode, and a shared
#: auto/bus platform is far more useful to a traveller as a bus stop than as an
#: ambiguous "other".
MODE_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("metro", ("subway", "light_rail", "monorail", "tram")),
    ("rail", ("train", "light_rail", "rail")),
    ("auto", ("rickshaw",)),
    ("bus", ("bus", "coach", "trolleybus")),
    ("ferry", ("ferry", "ship")),
)


def _classify_by_mode(tags: dict[str, str]) -> str | None:
    """
    Classify a stop from the mode flags OSM hangs off it.

    ``public_transport=platform`` on its own says nothing, which is why a plain
    read of the tag dumped every kerbside stop into "other". The mode keys
    (``bus=yes``, ``train=yes``, …) are the discriminating signal and they are
    present on the great majority of real stops.
    """
    for node_type, modes in MODE_RULES:
        for mode in modes:
            if str(tags.get(mode, "")).strip().lower() in ("yes", "true", "1"):
                return node_type
    return None


def _bbox(lat: float, lon: float, radius_km: float) -> tuple[float, float, float, float]:
    # 1 degree latitude ~= 111 km; longitude shrinks with latitude.
    import math

    dlat = radius_km / 111.0
    dlon = radius_km / max(1e-6, 111.0 * math.cos(math.radians(lat)))
    return (lon - dlon, lat - dlat, lon + dlon, lat + dlat)


def _live_mirrors() -> list[str]:
    """Overpass endpoints that are actually reachable right now.

    A hardcoded list is not enough. Dead entries cost more than they save: each
    one burns a full connect timeout per query, and a query that spends its time
    on an unresolvable host looks identical to an overloaded server. Measured on
    this machine only ``overpass-api.de`` and ``overpass.osm.ch`` answered, while
    ``overpass.osm.jp`` failed DNS outright and silently wiped out 41 tiles.

    The probe is cheap and cached for the process, so a long sync pays it once.
    """
    global _MIRROR_CACHE
    if _MIRROR_CACHE is None:
        alive: list[str] = []
        for url in opendata.OVERPASS_URLS:
            try:
                opendata._get(url, params={"data": _MIRROR_PROBE}, timeout=45, retries=0)
                alive.append(url)
            except Exception:
                continue
        # Never end up with nothing: fall back to the primary so a network blip
        # during the probe cannot produce a misleading "no mirrors" error.
        _MIRROR_CACHE = alive or [opendata.OVERPASS_URLS[0]]
    return _MIRROR_CACHE


#: Probed against a single city block, where the answer is known to be tiny, so
#: the probe measures reachability rather than loading up the server.
_MIRROR_PROBE = '[out:json][timeout:25];node(28.474,77.504,28.484,77.514)["amenity"="cafe"];out center 5;'

#: Process-lifetime cache for :func:`_live_mirrors`.
_MIRROR_CACHE: list[str] | None = None


def _overpass(query: str, timeout: int = 120) -> dict[str, Any]:
    """Run an Overpass query, failing over between mirrors.

    A 429 or 504 means the instance is rate limiting or briefly overloaded, and
    the polite response is to wait and retry the same endpoint. Failing over
    immediately instead spreads one user's load across every mirror and tends
    to get all of them throttled at once.
    """
    last: Exception | None = None
    for url in _live_mirrors():
        for attempt in range(4):
            try:
                # retries=1 so a 429/504 gets the exponential backoff honoured
                # instead of instantly dropping this chunk on the floor, which
                # is how every bus stop went missing from the map.
                return opendata._get(url, params={"data": query}, timeout=timeout, retries=1)
            except RuntimeError as exc:
                last = exc
                throttled = "429" in str(exc) or "504" in str(exc)
                # Only back off on a throttled reply. A connect timeout to an
                # already-probed mirror is not going to improve by waiting, so
                # move on and let another mirror take this chunk.
                if throttled and attempt < 3:
                    time.sleep(OVERPASS_BACKOFF_SEC * (2**attempt))
                    continue
                logger.warning(
                    "overpass mirror %s failed (attempt %d): %s", url, attempt + 1, exc
                )
                break
    raise RuntimeError(f"all overpass mirrors failed: {last}")


#: Station-like modes where OSM records one physical place as several elements
#: (the station node plus a platform per direction plus a stop_position per side).
#: Left alone, a single metro station appears nine times on the map, which is
#: noise rather than information. Modes absent from this set — bus stops
#: especially — are genuinely distinct places and are never merged.
STATION_LIKE_TYPES = frozenset({"metro", "rail", "airport", "ferry"})

#: Two same-named elements closer than this are the same place.
STATION_DEDUPE_M = 400.0

_NAME_NOISE = re.compile(r"[^a-z0-9 ]+")


def _norm_name(name: str) -> str:
    """Collapse case, punctuation and spacing so 'Alpha 1' == 'alpha-1'."""
    return " ".join(_NAME_NOISE.sub(" ", (name or "").lower()).split())


def _dedupe_stations(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Collapse the several OSM elements of one station into a single entry.

    A metro station is mapped as a station node, one platform per side and a
    stop_position per side. Those are useful for mapping accuracy and useless
    as a list a traveller reads, so only the station-like modes are merged, and
    only when the names agree and they sit together.
    """
    keep: list[dict[str, Any]] = []
    # name -> index into keep, so the comparison stays linear per name instead
    # of scanning every previously seen station.
    buckets: dict[tuple[str, str], list[int]] = {}

    for el in elements:
        tags = el.get("tags") or {}
        node_type = _classify(tags) or _classify_by_mode(tags) or "other"
        name = (tags.get("name") or tags.get("name:en") or "").strip()
        coords = _centroid(el)

        if (
            node_type not in STATION_LIKE_TYPES
            or not name
            or coords is None
        ):
            keep.append(el)
            continue

        key = (node_type, _norm_name(name))
        merged = False
        for i in reversed(buckets.get(key, [])):
            other = keep[i]
            oc = _centroid(other)
            if oc is None:
                continue
            # ~111 km per degree of latitude, corrected for longitude.
            import math as _m

            dlat = (coords[0] - oc[0]) * 111_000
            dlon = (coords[1] - oc[1]) * 111_000 * _m.cos(_m.radians(oc[0]))
            if dlat * dlat + dlon * dlon <= STATION_DEDUPE_M**2:
                merged = True
                break
        if merged:
            continue

        buckets.setdefault(key, []).append(len(keep))
        keep.append(el)

    if len(keep) != len(elements):
        logger.info("deduped %d station elements down to %d", len(elements), len(keep))
    return keep


def _tile(
    bbox: tuple[float, float, float, float], max_km: float
) -> list[tuple[float, float, float, float]]:
    """
    Split a bbox into a grid of at most ``max_km`` squares.

    A single 50 km query for every bus stop times out no matter how patiently it
    is retried, because the result set is genuinely huge. Tiling the same area
    into small squares returns the same data in a handful of cheap queries, and
    a failure then costs one tile instead of the whole city.
    """
    west, south, east, north = bbox
    dlat_km = (north - south) * 111.0
    dlon_km = (east - west) * 111.0
    rows = max(1, math.ceil(dlat_km / max_km))
    cols = max(1, math.ceil(dlon_km / max_km))
    out: list[tuple[float, float, float, float]] = []
    for r in range(rows):
        s = south + (north - south) * r / rows
        n = south + (north - south) * (r + 1) / rows
        for c in range(cols):
            w = west + (east - west) * c / cols
            e = west + (east - west) * (c + 1) / cols
            out.append((w, s, e, n))
    return out


#: Completed-tile checkpoint for an area sync. A 25 km sync is a few hundred
#: rate-limited Overpass requests, so the run is long enough that starting over
#: after a throttle is the normal case rather than the exception. Only tiles that
#: returned successfully are recorded; a throttled tile stays pending and is
#: retried on the next run.
TILE_CHECKPOINT = Path(tempfile.gettempdir()) / "yatrip_transport_tiles.json"


def _load_done(key: str) -> set[tuple[int, int]]:
    try:
        raw = json.loads(TILE_CHECKPOINT.read_text())
    except (OSError, ValueError):
        return set()
    tiles = raw.get(key)
    if not isinstance(tiles, list):
        return set()
    return {(int(g), int(t)) for g, t in tiles if isinstance(t, (list, tuple)) and len(t) == 2}


def _save_done(key: str, done: set[tuple[int, int]]) -> None:
    try:
        TILE_CHECKPOINT.write_text(
            json.dumps({key: [list(t) for t in sorted(done)]}), encoding="utf-8"
        )
    except OSError:
        # Losing the checkpoint only costs a re-run; never fail the sync for it.
        logger.warning("could not write transport tile checkpoint %s", TILE_CHECKPOINT)


def _query(
    bbox: tuple[float, float, float, float],
    done: set[tuple[int, int]] | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch hubs in a bbox.

    The tag matrix is split into a few smaller queries on purpose: a single
    16-way ``nwr`` union over a 50 km box reliably timed out, while the same
    tags queried in groups come back in seconds. Splitting also means one
    saturated group does not lose the whole result.
    """
    west, south, east, north = bbox
    # Kept deliberately small and few. Every extra union is another request
    # against a shared rate limit, and firing a dozen of them in a row is what
    # produced 429s. Rare modes are merged into one union because asking for
    # "ferry_terminal" on its own costs a full request to learn that a landlocked
    # district has no ferries.
    groups: list[list[tuple[str, str, str]]] = [
        [("metro", "station", "subway"), ("metro", "station", "light_rail"),
         ("rail", "railway", "station"), ("rail", "railway", "halt")],
        [("bus", "amenity", "bus_station"), ("bus", "public_transport", "station"),
         ("airport", "aeroway", "aerodrome"), ("auto", "amenity", "taxi_stand")],
        [("bus", "highway", "bus_stop"), ("other", "public_transport", "platform"),
         ("other", "public_transport", "stop_position"), ("auto", "amenity", "taxi")],
        [("airport", "amenity", "aerodrome"), ("rail", "amenity", "railway_station"),
         ("ferry", "amenity", "ferry_terminal"), ("rail", "railway", "tram_stop"),
         ("other", "aerialway", "station")],
    ]

    seen: set[tuple[str, int]] = set()
    elements: list[dict[str, Any]] = []
    failed: list[str] = []
    done = done if done is not None else set()
    # The stop-heavy group is tiled; the station/hub groups are small enough to
    # query in one piece even over a 50 km box.
    for idx, part in enumerate(groups):
        tiles = _tile(bbox, STOP_TILE_KM) if idx == 2 else [bbox]
        for tile_no, box in enumerate(tiles):
            tw, ts, te, tn = box
            # Skip tiles an earlier run already confirmed empty or filled. A full
            # sync is hundreds of rate-limited requests, so restarting from zero
            # after one 429 mostly re-earns tiles that already succeeded.
            if (idx, tile_no) in done:
                continue
            selectors = "\n".join(
                f'  nwr["{key}"="{value}"]({ts},{tw},{tn},{te});'
                for _t, key, value in part
            )
            # Only the high-cardinality group needs a cap; capping the rest would
            # silently drop stations.
            tail = f"out center tags {STOP_MAX_PER_QUERY};" if idx == 2 else "out center tags;"
            q = f"[out:json][timeout:180];\n(\n{selectors}\n);\n{tail}"
            try:
                payload = _overpass(q, timeout=180)
            except RuntimeError as exc:
                logger.warning(
                    "transport group %d tile %d/%d failed for %s: %s",
                    idx, tile_no + 1, len(tiles), box, exc,
                )
                failed.append(f"group {idx} tile {tile_no + 1}/{len(tiles)}")
                continue
            for el in payload.get("elements") or []:
                key = (el.get("type", "node"), el.get("id"))
                if key in seen:
                    continue
                seen.add(key)
                elements.append(el)
            # Only a completed tile is worth recording: a tile that returned an
            # error must be retried next run.
            done.add((idx, tile_no))
            # Be a good citizen: Overpass is a shared free resource and bursting
            # requests at it is how the whole sync gets 429'd.
            if (idx, tile_no) < (len(groups) - 1, len(tiles) - 1):
                time.sleep(OVERPASS_PATIENCE_SEC)
    if failed:
        # Surfaced rather than swallowed, so a partially completed area is never
        # reported to the traveller as a fully loaded map.
        logger.warning("%d transport tiles still incomplete: %s", len(failed), ", ".join(failed))
    return _dedupe_stations(elements)


def _centroid(el: dict[str, Any]) -> tuple[float, float] | None:
    lat, lon = el.get("lat"), el.get("lon")
    if lat is not None and lon is not None:
        return float(lat), float(lon)
    center = el.get("center") or {}
    lat, lon = center.get("lat"), center.get("lon")
    if lat is not None and lon is not None:
        return float(lat), float(lon)
    return None


def _name_for(tags: dict[str, str], node_type: str) -> str:
    name = tags.get("name") or tags.get("name:en") or tags.get("name:hi")
    if name:
        return name
    ref = tags.get("ref") or tags.get("operator:ref")
    if ref:
        return f"{node_type.title()} {ref}"
    return f"{node_type.title()} (unnamed)"


def fetch_near(
    lat: float,
    lon: float,
    radius_km: float = 25.0,
    city: str = "",
    state: str = "",
) -> dict[str, int]:
    """Fetch and upsert transport hubs around a point."""
    from django.contrib.gis.geos import Point

    box = _bbox(lat, lon, radius_km)
    # Keyed on the rounded centre and radius, so resuming a sync means resuming
    # the same area rather than quietly mixing in a differently placed one.
    key = f"{round(lat, 2)},{round(lon, 2)},{round(radius_km, 1)}"
    done = _load_done(key)
    elements = _query(box, done)
    _save_done(key, done)

    created = updated = skipped = 0
    for el in elements:
        tags = el.get("tags") or {}
        node_type = _classify(tags) or _classify_by_mode(tags)
        if not node_type:
            continue
        coords = _centroid(el)
        if not coords:
            continue
        clat, clon = coords
        osm_type = el.get("type", "node")
        osm_id = f"{osm_type}/{el.get('id')}"

        defaults = {
            "name": _name_for(tags, node_type)[:200],
            "node_type": node_type,
            "city": city or tags.get("addr:city", ""),
            "state": state or tags.get("addr:state", ""),
            "address": tags.get("addr:full") or tags.get("addr:street") or None,
            "location": Point(clon, clat, srid=4326),
            "image_url": tags.get("image") or tags.get("wikimedia_commons", "") or "",
            "operator": (tags.get("operator") or "")[:120],
            "phone": (tags.get("phone") or tags.get("contact:phone") or "")[:30],
            "code": (tags.get("ref") or tags.get("iata") or "")[:20],
            "amenities": [k for k in AMENITY_KEYS if tags.get(k) in ("yes", "true")],
            "route_refs": [r for r in (tags.get("ref") or "").split(";") if r][:10],
            "is_active": True,
        }
        if tags.get("opening_hours"):
            defaults["opening_hours"] = {"raw": tags["opening_hours"]}

        obj, made = TransportNode.objects.update_or_create(
            osm_id=osm_id, defaults=defaults
        )
        if made:
            created += 1
        else:
            updated += 1

    if not created and not updated:
        skipped = len(elements)
    logger.info(
        "transport near %s,%s: %s new, %s updated (%s raw elements)",
        lat, lon, created, updated, len(elements),
    )
    return {"created": created, "updated": updated, "raw": len(elements)}


#: Nominatim's transport POI classes. Anything outside this set is a place that
#: merely shares a word with transport ("Other 8", "Knowledge Park II") and was
#: being stored as a stop.
TRANSPORT_NOMINATIM_CLASSES = frozenset({
    "public_transport", "railway", "transport", "aeroway", "highway",
})

#: The OSM ``class`` values that specifically mean a boarding point.
TRANSPORT_NOMINATIM_KINDS = frozenset({
    "station", "halt", "stop_position", "platform", "bus_station", "subway",
    "train_station", "light_rail", "tram_stop", "ferry_terminal",
    "taxi", "aerodrome", "airport", "transportation", "bus_stop",
})


def _nominatim_queries() -> list[str]:
    return [
        "bus station", "bus stand", "bus terminal", "bus depot",
        "auto rickshaw stand", "auto stand", "rickshaw stand",
        "metro station", "subway station", "metro rail",
        "railway station", "rail station", "train station",
        "airport", "airport terminal", "aerodrome",
        "taxi stand", "cab stand",
    ]


def _harvest_via_nominatim(
    lat: float, lon: float, radius_km: float, city: str = ""
) -> dict[str, int]:
    """
    Fallback harvester using Nominatim search.

    Overpass is the better source, but it rate-limits hard and its mirrors have
    been observed to refuse connections outright, which leaves a traveller
    staring at an empty map. Nominatim is a different service on different
    infrastructure and stays reachable, so it is used to seed the same tables
    when Overpass cannot be reached.

    It finds *named* hubs, which is exactly what a traveller needs: "Majestic
    Bus Stand", "Sector 18 Metro" rather than anonymous kerbside platforms.
    """
    from django.contrib.gis.geos import Point

    # Nominatim has no radius filter, so the viewbox is a square around the
    # point sized to the requested radius, and results are distance-filtered
    # afterwards.
    import math

    dlat = radius_km / 111.0
    dlon = radius_km / max(1e-6, 111.0 * math.cos(math.radians(lat)))
    viewbox = f"{lon - dlon},{lat + dlat},{lon + dlon},{lat - dlat}"

    created = 0
    seen: set[str] = set()
    for term in _nominatim_queries():
        try:
            payload = opendata._get(
                f"{opendata.NOMINATIM_URL}/search",
                params={
                    "q": f"{term} {city}".strip() if city else term,
                    "format": "jsonv2",
                    "limit": 20,
                    "viewbox": viewbox,
                    # "bounded" keeps the viewbox authoritative instead of
                    # letting Nominatim widen the search across the country.
                    "bounded": 1,
                    "addressdetails": 1,
                    "extratags": 1,
                },
                timeout=20,
                retries=1,
            )
        except RuntimeError as exc:
            logger.warning("Nominatim harvest failed for %r: %s", term, exc)
            continue

        for hit in payload or []:
            # Nominatim answers any free-text query, so without a class filter
            # a search for "bus station" happily returns "Knowledge Park II" and
            # a bus stop it is not. Only genuine transport POIs are kept.
            klass = (hit.get("class") or hit.get("category") or "").lower()
            if klass not in TRANSPORT_NOMINATIM_CLASSES:
                continue
            kind = (hit.get("type") or "").lower()
            if kind and kind not in TRANSPORT_NOMINATIM_KINDS:
                continue

            try:
                hlat = float(hit["lat"])
                hlon = float(hit["lon"])
            except (KeyError, TypeError, ValueError):
                continue

            name = (hit.get("name") or hit.get("display_name", "").split(",")[0]).strip()
            if not name:
                continue

            # Rough radius check; Nominatim's own viewbox is generous.
            if (hlat - lat) ** 2 + ((hlon - lon) * math.cos(math.radians(lat))) ** 2 > (
                radius_km / 111.0
            ) ** 2:
                continue

            osm_type = hit.get("osm_type") or "node"
            osm_id = f"nominatim/{osm_type}/{hit.get('osm_id') or abs(hash(name))}"
            if osm_id in seen:
                continue
            seen.add(osm_id)

            node_type = _classify(
                {
                    "amenity": hit.get("category") or "",
                    "railway": hit.get("type") or "",
                    "aeroway": (hit.get("category") or "")
                    if hit.get("class") == "aeroway" else "",
                    "name": name,
                }
            ) or _guess_type_from_name(name)

            address = hit.get("address") or {}
            _obj, made = TransportNode.objects.update_or_create(
                osm_id=osm_id,
                defaults={
                    "name": name[:200],
                    "node_type": node_type,
                    "city": city or address.get("city") or address.get("town") or "",
                    "state": address.get("state") or "",
                    "address": address.get("road") or address.get("suburb") or None,
                    "location": Point(hlon, hlat, srid=4326),
                    "operator": (hit.get("name") if node_type == "bus" else "")[:120],
                    "amenities": [],
                    "is_active": True,
                },
            )
            if made:
                created += 1

    logger.info("nominatim harvest near %s,%s: %s new hubs", lat, lon, created)
    return {"created": created, "updated": 0, "raw": len(seen)}


def _guess_type_from_name(name: str) -> str:
    """Classify a named hub from its name when tags are unhelpful."""
    blob = name.lower()
    if "metro" in blob or "subway" in blob:
        return "metro"
    if "airport" in blob or "aerodrome" in blob or "terminal" in blob and "air" in blob:
        return "airport"
    if any(k in blob for k in ("railway", "rail station", "train station", "junction")):
        return "rail"
    if any(k in blob for k in ("auto", "rickshaw", "e-rickshaw")):
        return "auto"
    if any(k in blob for k in ("taxi", "cab stand")):
        return "taxi"
    if any(k in blob for k in ("bus", "coach", "transport")):
        return "bus"
    return "other"


def load_area(
    lat: float, lon: float, radius_km: float = 25.0, city: str = ""
) -> dict[str, Any]:
    """
    Best-effort import of transport hubs around a point.

    Tries Overpass first because it is the richer source, then falls back to
    Nominatim when Overpass yields nothing. Both are public endpoints that rate
    limit without warning, and an empty map is a worse outcome than a partially
    populated one, so the fallback matters.
    """
    result = {"created": 0, "updated": 0, "raw": 0, "source": "overpass"}
    try:
        result = fetch_near(lat, lon, radius_km, city=city)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Overpass load_area failed, trying Nominatim: %s", exc)
        result = {"created": 0, "updated": 0, "raw": 0, "source": "overpass_failed"}

    if result.get("created", 0) == 0:
        fallback = _harvest_via_nominatim(lat, lon, radius_km, city=city)
        logger.info(
            "area %s,%s -> overpass %s new, nominatim fallback %s new",
            lat, lon, result.get("created"), fallback["created"],
        )
        return {
            "created": fallback["created"],
            "updated": result.get("updated", 0),
            "raw": result.get("raw", 0) + fallback["raw"],
            "source": "nominatim" if fallback["created"] else result.get("source"),
        }

    return result


def reclassify_stored() -> dict[str, int]:
    """
    Re-run the operator/name inference over already-stored rows.

    OSM tags are not stored on the model, so rows written before the operator
    hints existed are stuck in the ``other`` bucket even though their operator
    ("BMTC", "KSRTC", ...) identifies them. This is safe to run any time.
    """
    changed = 0
    qs = TransportNode.objects.filter(node_type__in=["other", "bus", "auto"])
    for obj in qs.iterator(chunk_size=500):
        inferred = _classify(
            {
                "operator": obj.operator,
                "name": obj.name,
                "public_transport": "platform",
            }
        )
        if inferred and inferred != obj.node_type:
            obj.node_type = inferred
            obj.save(update_fields=["node_type"])
            changed += 1
    return {"reclassified": changed}


def fetch_for_city(city: str, radius_km: float = 30.0) -> dict[str, int]:
    """Geocode a city, then fetch the hubs around its centre."""
    hits = opendata.geocode(city)
    if not hits:
        logger.warning("could not geocode %r", city)
        return {"created": 0, "updated": 0, "raw": 0}
    first = hits[0]
    lat = first.get("latitude")
    lon = first.get("longitude")
    if lat is None or lon is None:
        logger.warning("geocoded %r has no coordinates: %r", city, first)
        return {"created": 0, "updated": 0, "raw": 0}
    return fetch_near(lat, lon, radius_km, city=city, state=first.get("state", ""))
