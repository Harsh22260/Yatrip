"""
Canonical open-data HTTP clients for Yatrip.

Every outbound call to an open data source lives here so that the MCP server
and the Django API views share one implementation. Nothing in this module
talks to the database, which keeps it usable from any process.

Sources used (all free, no scraping of HTML pages):
  * OpenStreetMap Nominatim  - geocoding / reverse geocoding
  * OpenStreetMap Overpass   - place search around a coordinate
  * Open-Meteo               - weather + forecast
  * OSRM                     - road routing / directions
  * Tavily                   - general web search (optional, needs a key)

No credential is hardcoded. Optional keys are read from the environment and
the corresponding helper simply reports unavailability when a key is absent.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Iterable

import requests

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org"
#: Overpass mirrors, tried in order. The main instance rate-limits hard and has
#: been observed to refuse connections entirely, so every mirror is tried before
#: a query is declared failed. Override with OSM_OVERPASS_URLS (comma separated).
OVERPASS_URLS: list[str] = [
    u.strip()
    for u in os.getenv(
        "OSM_OVERPASS_URLS",
        ",".join(
            (
                "https://overpass-api.de/api/interpreter",
                "https://overpass.kumi.systems/api/interpreter",
                "https://overpass.private.coffee/api/interpreter",
                "https://overpass.osm.jp/api/interpreter",
            )
        ),
    ).split(",")
    if u.strip()
]
#: Backwards-compatible single-URL alias used elsewhere in the codebase.
OVERPASS_URL = OVERPASS_URLS[0]
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"

# OpenStreetMap's usage policy requires a descriptive, contactable
# User-Agent. Override it with OSM_USER_AGENT in your .env.
USER_AGENT = os.getenv("OSM_USER_AGENT", "Yatrip/1.0 (open-source travel assistant)")

NOMINATIM_TIMEOUT = int(os.getenv("NOMINATIM_TIMEOUT", "10"))
OVERPASS_TIMEOUT = int(os.getenv("OVERPASS_TIMEOUT", "45"))
WEATHER_TIMEOUT = int(os.getenv("WEATHER_TIMEOUT", "12"))
ROUTE_TIMEOUT = int(os.getenv("ROUTE_TIMEOUT", "20"))

# Overpass asks callers to stay well under 1 request/second.
OVERPASS_MIN_INTERVAL_SECONDS = float(os.getenv("OVERPASS_MIN_INTERVAL_SECONDS", "1.1"))

_last_overpass_call: float = 0.0


def _throttle_overpass() -> None:
    """Space out Overpass calls so we do not hammer the public instance."""
    global _last_overpass_call
    wait = _last_overpass_call + OVERPASS_MIN_INTERVAL_SECONDS - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_overpass_call = time.monotonic()


def _get(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: int = 15,
    retries: int = 2,
) -> Any:
    """
    GET with a retry budget for transient 429/5xx responses.

    The public Overpass instance rate-limits aggressively, and a 429 there means
    "you are asking too fast", not "come back in a second". The old fixed 1.5s
    backoff burned the whole budget and still failed. This honours Retry-After
    when present and backs off exponentially otherwise.
    """
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = requests.get(
                url,
                params=params,
                # The Accept header is not cosmetic here. Overpass answers a
                # request without it with 406/504 rather than JSON, which reads
                # exactly like the mirror being down and sent this project
                # chasing network problems that did not exist.
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001 - network layer is best-effort
            last_error = exc
            response = getattr(exc, "response", None)
            status = getattr(response, "status_code", None)
            if status not in (429, 500, 502, 503, 504) or attempt >= retries:
                break

            delay = None
            if response is not None:
                try:
                    delay = float(response.headers.get("Retry-After", ""))
                except (TypeError, ValueError):
                    delay = None
            if delay is None:
                delay = min(2.0 ** (attempt + 1), 30.0)

            time.sleep(delay)
    raise RuntimeError(f"GET {url} failed: {last_error}") from last_error


# ---------------------------------------------------------------------------
# Geocoding
# ---------------------------------------------------------------------------


def geocode(
    place_name: str,
    *,
    country_codes: str | None = "in",
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Forward geocode a free-form place name.

    Returns a list of matches sorted by Nominatim's own relevance ranking.
    An empty list means nothing matched, which is not an error.
    """
    if not place_name or not place_name.strip():
        return []

    params: dict[str, Any] = {"q": place_name, "format": "json", "limit": limit}
    if country_codes:
        params["countrycodes"] = country_codes

    try:
        matches = _get(
            f"{NOMINATIM_URL}/search",
            params=params,
            timeout=NOMINATIM_TIMEOUT,
        )
    except RuntimeError as exc:
        logger.warning("Nominatim search failed for %r: %s", place_name, exc)
        # Retry without the country restriction before giving up.
        params.pop("countrycodes", None)
        try:
            matches = _get(
                f"{NOMINATIM_URL}/search",
                params=params,
                timeout=NOMINATIM_TIMEOUT,
                retries=0,
            )
        except RuntimeError:
            return []

    return [_normalise_place(match) for match in matches or []]


def reverse_geocode(latitude: float, lon: float) -> dict[str, Any] | None:
    """Resolve a coordinate to the nearest address."""
    try:
        payload = _get(
            f"{NOMINATIM_URL}/reverse",
            params={"lat": latitude, "lon": lon, "format": "json"},
            timeout=NOMINATIM_TIMEOUT,
            retries=0,
        )
    except RuntimeError as exc:
        logger.warning("Nominatim reverse lookup failed: %s", exc)
        return None
    return _normalise_place(payload) if payload else None


def _normalise_place(payload: dict[str, Any]) -> dict[str, Any]:
    """Flatten a Nominatim result into the shape the rest of the app expects."""
    address = payload.get("address") or {}
    return {
        "name": payload.get("name")
        or payload.get("display_name", "").split(",")[0].strip(),
        "display_name": payload.get("display_name", ""),
        "type": payload.get("type") or payload.get("category") or "",
        "latitude": _to_float(payload.get("lat")),
        "longitude": _to_float(payload.get("lon")),
        "city": address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("suburb")
        or "",
        "state": address.get("state") or "",
        "country": address.get("country") or "",
        "country_code": (payload.get("addresscountrycode") or "").lower(),
    }


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Place search (Overpass)
# ---------------------------------------------------------------------------

# Maps our app-level place types onto valid Overpass QL key=value pairs.
# The previous implementation embedded a stray leading quote inside these
# values, which produced malformed queries like node["amenity"="restaurant"].
PLACE_TYPE_TAGS: dict[str, list[tuple[str, str]]] = {
    "restaurant": [("amenity", "restaurant"), ("amenity", "fast_food"), ("amenity", "cafe")],
    "hotel": [("tourism", "hotel"), ("tourism", "guest_house"), ("tourism", "hostel")],
    "attraction": [
        ("tourism", "attraction"),
        ("tourism", "museum"),
        ("historic", "memorial"),
        ("leisure", "park"),
        ("natural", "peak"),
        ("natural", "waterfall"),
    ],
    "temple": [
        ("amenity", "place_of_worship"),
        ("historic", "temple"),
    ],
    "museum": [("tourism", "museum"), ("tourism", "gallery")],
    "park": [
        ("leisure", "park"),
        ("leisure", "garden"),
        ("leisure", "nature_reserve"),
    ],
    "cafe": [("amenity", "cafe")],
    "bus_stop": [("highway", "bus_stop")],
    "metro": [("railway", "station"), ("station", "subway")],
    "taxi_stand": [("amenity", "taxi")],
    "pharmacy": [("amenity", "pharmacy"), ("amenity", "hospital")],
    "atm": [("amenity", "atm"), ("amenity", "bank")],
    "shop": [("shop", "supermarket"), ("shop", "mall"), ("shop", "convenience")],
}

DEFAULT_PLACE_TYPE = "attraction"


def _overpass_selectors(tag_pairs: Iterable[tuple[str, str]]) -> str:
    """Build a valid Overpass selector union from (key, value) pairs."""
    return "".join(f'["{key}"="{value}"]' for key, value in tag_pairs)


def search_nearby_places(
    latitude: float,
    longitude: float,
    *,
    place_type: str = DEFAULT_PLACE_TYPE,
    radius_meters: int = 1500,
    limit: int = 15,
) -> list[dict[str, Any]]:
    """
    Find places of a given type around a coordinate using Overpass.

    Queries both nodes and ways so that large structures (stadiums, parks)
    are included, and de-duplicates by display name.
    """
    tag_pairs = PLACE_TYPE_TAGS.get(place_type)
    if not tag_pairs:
        tag_pairs = PLACE_TYPE_TAGS[DEFAULT_PLACE_TYPE]

    selector = _overpass_selectors(tag_pairs)
    query = (
        "[out:json][timeout:25];\n"
        f"(node{selector}(around:{radius_meters},{latitude},{longitude});\n"
        f" way{selector}(around:{radius_meters},{latitude},{longitude});\n"
        ");\n"
        "out center tags %d;\n" % max(limit * 4, 40)
    )

    try:
        _throttle_overpass()
        response = requests.post(
            OVERPASS_URL,
            data={"data": query},
            headers={"User-Agent": USER_AGENT},
            timeout=OVERPASS_TIMEOUT,
        )
        response.raise_for_status()
        elements = response.json().get("elements", [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("Overpass query failed for %s: %s", place_type, exc)
        return []

    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    for element in elements:
        tags = element.get("tags") or {}
        name = tags.get("name") or tags.get("name:en")
        if not name or name in seen:
            continue
        seen.add(name)

        latitude_out = element.get("lat") or (element.get("center") or {}).get("lat")
        longitude_out = element.get("lon") or (element.get("center") or {}).get("lon")

        results.append(
            {
                "name": name,
                "osm_type": element.get("type"),
                "osm_id": f"{element.get('type')}/{element.get('id')}",
                "latitude": latitude_out,
                "longitude": longitude_out,
                "place_type": tags.get("tourism")
                or tags.get("amenity")
                or tags.get("shop")
                or tags.get("historic")
                or place_type,
                "cuisine": tags.get("cuisine"),
                "opening_hours": tags.get("opening_hours"),
                "phone": tags.get("phone") or tags.get("contact:phone"),
                "website": tags.get("website") or tags.get("url"),
                "address": _format_osm_address(tags),
            }
        )
        if len(results) >= limit:
            break

    return results


def _format_osm_address(tags: dict[str, str]) -> str:
    parts = [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:suburb") or tags.get("addr:city"),
        tags.get("addr:state"),
    ]
    return ", ".join(part for part in parts if part)


# ---------------------------------------------------------------------------
# Weather
# ---------------------------------------------------------------------------

WMO_CONDITIONS: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def describe_weather_code(code: Any) -> str:
    try:
        return WMO_CONDITIONS.get(int(code), "Unknown conditions")
    except (TypeError, ValueError):
        return "Unknown conditions"


def get_weather(city: str, *, forecast_days: int = 3) -> dict[str, Any] | None:
    """
    Current conditions plus a short daily forecast for an Indian city.

    Resolves the city through Nominatim first, then queries Open-Meteo.
    Returns None when the city cannot be resolved or the forecast is
    unavailable, so callers can degrade gracefully.
    """
    if not city or not city.strip():
        return None

    matches = geocode(f"{city}, India", country_codes="in", limit=1)
    if not matches:
        return None

    latitude = matches[0]["latitude"]
    longitude = matches[0]["longitude"]
    if latitude is None or longitude is None:
        return None

    try:
        payload = _get(
            OPEN_METEO_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "Asia/Kolkata",
                "forecast_days": forecast_days,
            },
            timeout=WEATHER_TIMEOUT,
            retries=1,
        )
    except RuntimeError as exc:
        logger.warning("Open-Meteo forecast failed for %s: %s", city, exc)
        return None

    current = payload.get("current") or {}
    daily = payload.get("daily") or {}
    dates = daily.get("time") or []

    return {
        "city": city,
        "resolved_place": matches[0]["display_name"],
        "latitude": latitude,
        "longitude": longitude,
        "temperature_c": current.get("temperature_2m"),
        "humidity_percent": current.get("relative_humidity_2m"),
        "wind_speed_kmh": current.get("wind_speed_10m"),
        "condition": describe_weather_code(current.get("weather_code")),
        "forecast": [
            {
                "date": dates[index],
                "max_c": (daily.get("temperature_2m_max") or [None] * len(dates))[index],
                "min_c": (daily.get("temperature_2m_min") or [None] * len(dates))[index],
                "precipitation_mm": (daily.get("precipitation_sum") or [None] * len(dates))[index],
            }
            for index in range(min(forecast_days, len(dates)))
        ],
    }


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


#: OSRM demo server exposes one router per transport mode. A walker, a cyclist
#: and a car genuinely get different legal paths -- a car cannot use the footpath
#: shortcut through a park that the walking profile uses -- so the profile has to
#: travel with the request rather than being hard-coded to driving.
OSRM_PROFILES: dict[str, str] = {
    "car": "driving",
    "driving": "driving",
    "auto": "driving",
    "bike": "cycling",
    "bicycle": "cycling",
    "cycling": "cycling",
    "walk": "walking",
    "walking": "walking",
    "foot": "walking",
}

#: Real routing endpoints per mode, tried in order.
#:
#: The public demo host (router.project-osrm.org) only has the *car* dataset
#: mounted, and silently answers /walking/ and /cycling/ with car data --
#: verified: all three returned an identical 6.78 km / 7.4 min for the same trip,
#: while routing.openstreetmap.de returned 4.75 km for bike and 5.03 km / 67 min
#: for foot. So each mode needs its own host, and the path segment stays
#: "driving" on all of them. The demo host is kept last as a fallback.
OSRM_ENDPOINTS: dict[str, list[str]] = {
    "driving": [
        "https://routing.openstreetmap.de/routed-car/route/v1/driving",
        "https://router.project-osrm.org/route/v1/driving",
    ],
    "cycling": [
        "https://routing.openstreetmap.de/routed-bike/route/v1/driving",
    ],
    "walking": [
        "https://routing.openstreetmap.de/routed-foot/route/v1/driving",
    ],
}


def get_directions(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    profile: str = "car",
) -> dict[str, Any] | None:
    """
    Real route between two coordinates via OSRM, for a given travel mode.

    Returns distance in km, duration in minutes and the GeoJSON geometry so
    callers can draw the path on a map. Returns None on failure.
    """
    return get_multi_directions(
        [(start_lat, start_lon), (end_lat, end_lon)], profile=profile
    )


def get_multi_directions(
    points: list[tuple[float, float]],
    profile: str = "car",
) -> dict[str, Any] | None:
    """
    Route through an ordered list of waypoints.

    OSRM treats everything between the first and last point as a via-route, so
    one request covers a whole multi-stop trip. ``steps=true`` also returns turn
    instructions, which is what makes the route genuinely follow-able rather than
    just a line.
    """
    if len(points) < 2:
        return None

    mode = OSRM_PROFILES.get(str(profile).lower())
    if mode is None:
        logger.warning("unknown routing profile %r, falling back to driving", profile)
        mode = "driving"

    coordinates = ";".join(f"{lon},{lat}" for lat, lon in points)
    payload = None
    for base in OSRM_ENDPOINTS.get(mode, []):
        try:
            payload = _get(
                f"{base}/{coordinates}",
                params={
                    "overview": "full",
                    "geometries": "geojson",
                    "steps": "true",
                },
                timeout=ROUTE_TIMEOUT,
                retries=0,
            )
            break
        except RuntimeError as exc:
            logger.warning("OSRM %s routing failed on %s: %s", mode, base, exc)

    if payload is None:
        return None

    routes = payload.get("routes") or []
    if not routes:
        return None

    route = routes[0]
    legs = []
    for leg in route.get("legs") or []:
        legs.append(
            {
                "distance_km": round(leg.get("distance", 0) / 1000, 2),
                "duration_min": round(leg.get("duration", 0) / 60, 1),
                "steps": [
                    {
                        "instruction": _manoeuvre(s),
                        "distance_m": round(s.get("distance", 0)),
                        "duration_min": round(s.get("duration", 0) / 60, 1),
                        "mode": (s.get("maneuver") or {}).get("type", ""),
                        "modifier": (s.get("maneuver") or {}).get("modifier", ""),
                    }
                    for s in leg.get("steps") or []
                ],
            }
        )

    return {
        "profile": mode,
        "distance_km": round(route.get("distance", 0) / 1000, 2),
        "duration_min": round(route.get("duration", 0) / 60, 1),
        "geometry": route.get("geometry"),
        "legs": legs,
    }


def _manoeuvre(step: dict[str, Any]) -> str:
    """Human turn instruction from an OSRM step."""
    maneuver = step.get("maneuver") or {}
    verb = (maneuver.get("type") or "").replace("_", " ")
    modifier = (maneuver.get("modifier") or "").replace("_", " ")
    name = step.get("name") or ""
    if not name:
        return verb.capitalize()
    return f"{verb} {modifier} onto {name}".strip().capitalize()


# ---------------------------------------------------------------------------
# Web search (optional)
# ---------------------------------------------------------------------------


def web_search(query: str, *, max_results: int = 5) -> dict[str, Any]:
    """
    General web search through Tavily.

    Returns {'available': False, 'reason': ...} when no API key is
    configured, so the caller can fall back to the model's own knowledge.
    """
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        return {"available": False, "reason": "TAVILY_API_KEY is not configured"}

    try:
        from tavily import TavilyClient
    except ImportError:
        return {"available": False, "reason": "tavily-python is not installed"}

    try:
        client = TavilyClient(api_key=api_key)
        results = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",
            include_answer=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Tavily search failed for %r: %s", query, exc)
        return {"available": False, "reason": f"search failed: {exc}"}

    return {
        "available": True,
        "answer": results.get("answer"),
        "results": [
            {
                "title": item.get("title"),
                "snippet": (item.get("content") or "")[:300],
                "url": item.get("url"),
            }
            for item in (results.get("results") or [])[:max_results]
        ],
    }
