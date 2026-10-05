"""
Yatrip MCP Server
=================

Exposes Yatrip's own catalogue (PostgreSQL/PostGIS via the Django ORM) and a
handful of free open-data sources as Model Context Protocol tools. The
chatbot in ``chatbot/agent.py`` consumes this server through the official
MCP client instead of scraping data in-process.

Run it standalone:

    python -m yatrip.mcp_server                       # stdio
    python manage.py mcp_server --transport stdio    # same thing, via Django
    python manage.py mcp_server --transport streamable-http --port 8000

Tool groups
    Yatrip catalogue : search_hotels, get_hotel_details,
                       check_room_availability, search_attractions,
                       search_food, search_rentals,
                       find_transport_nodes, nearby_transport_nodes
    Open data        : geocode_place, reverse_geocode, search_nearby_places,
                       get_weather, get_directions, web_search
    Knowledge base   : search_knowledge_base (Pinecone RAG)

Every tool returns a JSON-serialisable dict. Failures are reported as
``{"error": "..."}`` rather than raised, so a flaky upstream degrades the
conversation instead of breaking it.
"""

from __future__ import annotations

import functools
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Bootstrap Django before touching models. Harmless when launched from a
# management command where Django is already configured.
# ---------------------------------------------------------------------------

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "yatrip.settings")

import django  # noqa: E402
from django.apps import apps as django_apps  # noqa: E402

if not django_apps.ready:
    django.setup()

from asgiref.sync import sync_to_async
from django.conf import settings  # noqa: E402
from django.contrib.gis.db.models.functions import Distance  # noqa: E402
from django.contrib.gis.geos import Point  # noqa: E402
from django.db import close_old_connections  # noqa: E402
from django.db.models import Q  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402

from yatrip import opendata  # noqa: E402

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("yatrip.mcp")

SERVER_NAME = "yatrip"
SERVER_INSTRUCTIONS = (
    "Authoritative travel data for the Yatrip platform. Use search_hotels / "
    "search_attractions / search_food / search_rentals for listings that are "
    "actually on the platform, and geocode_place / search_nearby_places / "
    "get_weather / get_directions for open map and weather data. All prices "
    "are in Indian Rupees (INR)."
)

mcp = FastMCP(SERVER_NAME, instructions=SERVER_INSTRUCTIONS)


def blocking_tool(**tool_kwargs):
    """
    Register a blocking tool function, running it off the event loop.

    FastMCP invokes ``def`` tools directly on the event loop, which breaks
    Django's ORM (it refuses sync queries from an async context) and would
    block the loop on every outbound HTTP call. Wrapping the body in
    ``sync_to_async(thread_sensitive=True)`` fixes both and keeps all queries
    on a single dedicated thread so the DB connection is reused.
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await sync_to_async(func, thread_sensitive=True)(*args, **kwargs)

        return mcp.tool(**tool_kwargs)(wrapper)

    return decorator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok(payload: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, **payload}


def _fail(message: str) -> dict[str, Any]:
    logger.warning("MCP tool failure: %s", message)
    return {"ok": False, "error": message}


def _parse_date(value: str | None, field: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date (YYYY-MM-DD), got {value!r}") from exc


def _money(value: Any) -> float | None:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


# ===========================================================================
# Yatrip catalogue tools
# ===========================================================================


@blocking_tool(
    name="search_hotels",
    description=(
        "Search hotels that are actually listed on Yatrip. Filter by city, "
        "name, minimum rating or maximum nightly price. Returns the cheapest "
        "available room type for each hotel, priced in INR."
    ),
)
def search_hotels(
    city: str | None = None,
    name: str | None = None,
    min_rating: float | None = None,
    max_price_per_night: float | None = None,
    limit: int = 8,
) -> dict[str, Any]:
    from hotels.models import Hotel, RoomType

    close_old_connections()
    try:
        hotels = Hotel.objects.prefetch_related("room_types").order_by("-rating")

        if city:
            hotels = hotels.filter(address__icontains=city)
        if name:
            hotels = hotels.filter(name__icontains=name)
        if min_rating is not None:
            hotels = hotels.filter(rating__gte=min_rating)

        hotels = list(hotels[: max(limit * 4, 20)])

        results = []
        for hotel in hotels:
            room_types = list(hotel.room_types.all())
            prices = [
                _money(room.base_price)
                for room in room_types
                if _money(room.base_price) is not None
            ]
            if max_price_per_night is not None:
                if not prices:
                    continue
                cheapest = min(prices)
                if cheapest > max_price_per_night:
                    continue

            results.append(
                {
                    "id": hotel.id,
                    "name": hotel.name,
                    "address": hotel.address,
                    "rating": hotel.rating,
                    "is_verified": hotel.is_verified,
                    "description": (hotel.description or "")[:400],
                    "location": _point_payload(hotel.location),
                    "starting_price_inr": min(prices) if prices else None,
                    "room_type_count": len(room_types),
                    "room_types": [
                        {
                            "name": room.name,
                            "capacity": room.capacity,
                            "base_price_inr": _money(room.base_price),
                            "total_units": room.total_units,
                        }
                        for room in room_types[:6]
                    ],
                }
            )
            if len(results) >= limit:
                break

        if not results:
            return _ok({"count": 0, "results": [], "message": "No Yatrip hotels matched."})
        return _ok({"count": len(results), "results": results})
    except ValueError as exc:
        return _fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        return _fail(f"hotel search failed: {exc}")
    finally:
        close_old_connections()


@blocking_tool(
    name="get_hotel_details",
    description="Full detail for one Yatrip hotel including every room type, rate plan and the next 30 days of availability.",
)
def get_hotel_details(hotel_id: int) -> dict[str, Any]:
    from hotels.models import Hotel

    close_old_connections()
    try:
        hotel = Hotel.objects.prefetch_related(
            "room_types__rate_plans", "room_types__availability"
        ).filter(pk=hotel_id).first()
        if hotel is None:
            return _fail(f"No hotel with id {hotel_id}.")

        today = date.today()
        horizon = today + timedelta(days=30)
        availability_counts: dict[str, dict[str, int]] = {}
        for availability in hotel.room_types.all():
            for row in availability.availability.filter(date__range=(today, horizon)):
                bucket = availability_counts.setdefault(
                    str(row.date), {"available": 0, "booked": 0}
                )
                if row.is_booked:
                    bucket["booked"] += 1
                else:
                    bucket["available"] += row.available_units

        room_types = []
        for room in hotel.room_types.all():
            room_types.append(
                {
                    "id": room.id,
                    "name": room.name,
                    "description": room.description,
                    "capacity": room.capacity,
                    "base_price_inr": _money(room.base_price),
                    "total_units": room.total_units,
                    "rate_plans": [
                        {
                            "name": plan.name,
                            "price_inr": _money(plan.get_final_price()),
                            "refundable": plan.refundable,
                            "breakfast_included": plan.breakfast_included,
                            "discount_percent": plan.discount_percent,
                            "min_stay": plan.min_stay,
                        }
                        for plan in room.rate_plans.all()
                    ],
                }
            )

        return _ok(
            {
                "id": hotel.id,
                "name": hotel.name,
                "address": hotel.address,
                "rating": hotel.rating,
                "is_verified": hotel.is_verified,
                "description": hotel.description,
                "location": _point_payload(hotel.location),
                "room_types": room_types,
                "availability_next_30_days": availability_counts,
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _fail(f"could not load hotel {hotel_id}: {exc}")
    finally:
        close_old_connections()


@blocking_tool(
    name="check_room_availability",
    description=(
        "Check whether a Yatrip hotel has rooms free for a stay. Pass "
        "check_in/check_out as YYYY-MM-DD. Returns per-room-type free unit "
        "counts and the total price in INR."
    ),
)
def check_room_availability(
    hotel_id: int,
    check_in: str,
    check_out: str,
) -> dict[str, Any]:
    from hotels.models import Hotel, RoomType

    close_old_connections()
    try:
        arrival = _parse_date(check_in, "check_in")
        departure = _parse_date(check_out, "check_out")
        if arrival is None or departure is None:
            return _fail("check_in and check_out are both required (YYYY-MM-DD).")
        if departure <= arrival:
            return _fail("check_out must be after check_in.")
        if arrival < date.today():
            return _fail("check_in cannot be in the past.")

        hotel = Hotel.objects.filter(pk=hotel_id).first()
        if hotel is None:
            return _fail(f"No hotel with id {hotel_id}.")

        nights = (departure - arrival).days
        room_reports = []
        for room in RoomType.objects.filter(hotel=hotel).prefetch_related("availability"):
            days = list(
                room.availability.filter(date__gte=arrival, date__lt=departure)
            )
            # Absent rows mean the room was not loaded for that date yet,
            # so fall back to the physical unit count rather than reporting 0.
            free = min(
                (row.available_units for row in days),
                default=room.total_units,
            )
            room_reports.append(
                {
                    "room_type_id": room.id,
                    "name": room.name,
                    "capacity": room.capacity,
                    "base_price_inr": _money(room.base_price),
                    "free_units_for_stay": free,
                    "is_available": free > 0,
                    "stay_total_inr": _money((_money(room.base_price) or 0) * nights),
                    "nights": nights,
                }
            )

        available = [room for room in room_reports if room["is_available"]]
        cheapest = min(
            (room["stay_total_inr"] for room in available if room["stay_total_inr"]),
            default=None,
        )
        return _ok(
            {
                "hotel": {"id": hotel.id, "name": hotel.name, "address": hotel.address},
                "check_in": arrival.isoformat(),
                "check_out": departure.isoformat(),
                "nights": nights,
                "has_availability": bool(available),
                "cheapest_stay_total_inr": cheapest,
                "room_types": room_reports,
            }
        )
    except ValueError as exc:
        return _fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        return _fail(f"availability check failed: {exc}")
    finally:
        close_old_connections()


@blocking_tool(
    name="search_attractions",
    description=(
        "Search tourist attractions in the Yatrip catalogue by city, name or "
        "category (monument, temple, park, museum, nature, other). Optionally "
        "sort by distance from a coordinate."
    ),
)
def search_attractions(
    city: str | None = None,
    name: str | None = None,
    category: str | None = None,
    free_only: bool = False,
    min_rating: float | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    radius_km: float | None = None,
    limit: int = 8,
) -> dict[str, Any]:
    from attractions.models import Attraction

    close_old_connections()
    try:
        queryset = Attraction.objects.filter(is_active=True)
        if city:
            queryset = queryset.filter(city__iexact=city) | queryset.filter(
                state__iexact=city
            )
            queryset = queryset.distinct()
        if name:
            queryset = queryset.filter(name__icontains=name)
        if category and category != "all":
            queryset = queryset.filter(category=category)
        if free_only:
            queryset = queryset.filter(is_free=True)
        if min_rating is not None:
            queryset = queryset.filter(rating__gte=min_rating)

        candidates = list(queryset[: max(limit * 4, 20)])

        if latitude is not None and longitude is not None:
            for attraction in candidates:
                attraction._distance_km = attraction.distance_from(latitude, longitude)
            candidates.sort(key=lambda item: item._distance_km)
            if radius_km is not None:
                candidates = [
                    item for item in candidates if item._distance_km <= radius_km
                ]
        else:
            candidates.sort(key=lambda item: -item.rating)

        results = [
            {
                "id": attraction.id,
                "name": attraction.name,
                "category": attraction.get_category_display(),
                "address": attraction.address,
                "city": attraction.city,
                "state": attraction.state,
                "rating": attraction.rating,
                "review_count": attraction.review_count,
                "entry_fee_inr": _money(attraction.entry_fee) if not attraction.is_free else 0.0,
                "is_free": attraction.is_free,
                "opening_hours": (attraction.opening_hours or {}).get("raw"),
                "latitude": attraction.latitude,
                "longitude": attraction.longitude,
                "distance_km": round(getattr(attraction, "_distance_km", 0.0), 2)
                if (latitude is not None and longitude is not None)
                else None,
            }
            for attraction in candidates[:limit]
        ]

        if not results:
            return _ok({"count": 0, "results": [], "message": "No attractions matched."})
        return _ok({"count": len(results), "results": results})
    except Exception as exc:  # noqa: BLE001
        return _fail(f"attraction search failed: {exc}")
    finally:
        close_old_connections()


@blocking_tool(
    name="search_food",
    description=(
        "Search restaurants, cafes, dhabas and street food in the Yatrip "
        "catalogue. Filter by city, name, cuisine, category, veg-only or "
        "maximum cost for two."
    ),
)
def search_food(
    city: str | None = None,
    name: str | None = None,
    cuisine: str | None = None,
    category: str | None = None,
    veg_only: bool = False,
    max_cost_for_two: int | None = None,
    min_rating: float | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    radius_km: float | None = None,
    limit: int = 8,
) -> dict[str, Any]:
    from food.models import FoodPlace

    close_old_connections()
    try:
        queryset = FoodPlace.objects.filter(is_active=True)
        if city:
            queryset = queryset.filter(city__iexact=city).distinct()
        if name:
            queryset = queryset.filter(name__icontains=name)
        if cuisine and cuisine != "all":
            queryset = queryset.filter(cuisine=cuisine)
        if category and category != "all":
            queryset = queryset.filter(category=category)
        if veg_only:
            queryset = queryset.filter(is_veg=True)
        if max_cost_for_two is not None:
            queryset = queryset.filter(
                Q(avg_cost_for_two__lte=max_cost_for_two) | Q(avg_cost_for_two__isnull=True)
            )
        if min_rating is not None:
            queryset = queryset.filter(rating__gte=min_rating)

        candidates = list(queryset[: max(limit * 4, 20)])

        if latitude is not None and longitude is not None:
            for place in candidates:
                place._distance_km = place.distance_from(latitude, longitude)
            candidates.sort(key=lambda item: item._distance_km)
            if radius_km is not None:
                candidates = [item for item in candidates if item._distance_km <= radius_km]
        else:
            candidates.sort(key=lambda item: -item.rating)

        results = [
            {
                "id": place.id,
                "name": place.name,
                "category": place.get_category_display(),
                "cuisine": place.get_cuisine_display(),
                "address": place.address,
                "city": place.city,
                "rating": place.rating,
                "review_count": place.review_count,
                "price_level": "₹" * place.price_level if place.price_level else "₹",
                "avg_cost_for_two_inr": place.avg_cost_for_two,
                "is_veg": place.is_veg,
                "is_open_now": place.is_open_now,
                "home_delivery": place.home_delivery,
                "takeaway": place.takeaway,
                "opening_hours": (place.opening_hours or {}).get("raw"),
                "distance_km": round(getattr(place, "_distance_km", 0.0), 2)
                if (latitude is not None and longitude is not None)
                else None,
            }
            for place in candidates[:limit]
        ]

        if not results:
            return _ok({"count": 0, "results": [], "message": "No food places matched."})
        return _ok({"count": len(results), "results": results})
    except Exception as exc:  # noqa: BLE001
        return _fail(f"food search failed: {exc}")
    finally:
        close_old_connections()


@blocking_tool(
    name="search_rentals",
    description=(
        "Search long-term rentals on Yatrip: homestays, paying-guest rooms and "
        "hostels. Filter by city, rental type, maximum monthly rent and "
        "minimum available rooms. Monthly prices are in INR."
    ),
)
def search_rentals(
    city: str | None = None,
    name: str | None = None,
    rental_type: str | None = None,
    max_price_per_month: float | None = None,
    min_available_rooms: int | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    radius_km: float | None = None,
    limit: int = 8,
) -> dict[str, Any]:
    from rentals.models import Rental

    close_old_connections()
    try:
        queryset = Rental.objects.prefetch_related("amenities")
        if city:
            queryset = queryset.filter(address__icontains=city)
        if name:
            queryset = queryset.filter(name__icontains=name)
        if rental_type and rental_type != "all":
            queryset = queryset.filter(rental_type=rental_type)
        if max_price_per_month is not None:
            queryset = queryset.filter(price_per_month__lte=max_price_per_month)
        if min_available_rooms is not None:
            queryset = queryset.filter(available_rooms__gte=min_available_rooms)

        candidates = list(queryset[: max(limit * 4, 20)])

        if latitude is not None and longitude is not None:
            scored = []
            for rental in candidates:
                if rental.location is None:
                    continue
                rental._distance_km = rental.location.distance(
                    Point(longitude, latitude, srid=4326)
                ) / 1000.0
                scored.append(rental)
            if radius_km is not None:
                scored = [item for item in scored if item._distance_km <= radius_km]
            candidates = sorted(scored, key=lambda item: item._distance_km)
        else:
            candidates = sorted(candidates, key=lambda item: -(item.price_per_month or 0))

        results = [
            {
                "id": rental.id,
                "name": rental.name,
                "rental_type": rental.get_rental_type_display(),
                "address": rental.address,
                "price_per_month_inr": _money(rental.price_per_month),
                "available_rooms": rental.available_rooms,
                "is_verified": rental.is_verified,
                "description": (rental.description or "")[:300],
                "amenities": [amenity.name for amenity in rental.amenities.all()],
                "owner_email": rental.owner.email if rental.owner_id else None,
                "distance_km": round(getattr(rental, "_distance_km", 0.0), 2)
                if (latitude is not None and longitude is not None)
                else None,
            }
            for rental in candidates[:limit]
        ]

        if not results:
            return _ok({"count": 0, "results": [], "message": "No rentals matched."})
        return _ok({"count": len(results), "results": results})
    except Exception as exc:  # noqa: BLE001
        return _fail(f"rental search failed: {exc}")
    finally:
        close_old_connections()


@blocking_tool(
    name="find_transport_nodes",
    description=(
        "Search transport hubs in the Yatrip database: bus stands, auto stands, "
        "metro stations and taxi stands. Filter by city, node type or name."
    ),
)
def find_transport_nodes(
    city: str | None = None,
    node_type: str | None = None,
    name: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    from transport.models import TransportNode

    close_old_connections()
    try:
        queryset = TransportNode.objects.all()
        if city:
            queryset = queryset.filter(city__iexact=city)
        if node_type and node_type != "all":
            queryset = queryset.filter(node_type=node_type)
        if name:
            queryset = queryset.filter(name__icontains=name)

        results = [
            {
                "id": node.id,
                "name": node.name,
                "node_type": node.get_node_type_display(),
                "city": node.city,
                "address": node.address,
                "location": _point_payload(node.location),
            }
            for node in queryset[:limit]
        ]
        if not results:
            return _ok({"count": 0, "results": [], "message": "No transport nodes matched."})
        return _ok({"count": len(results), "results": results})
    except Exception as exc:  # noqa: BLE001
        return _fail(f"transport search failed: {exc}")
    finally:
        close_old_connections()


@blocking_tool(
    name="nearby_transport_nodes",
    description=(
        "Find the closest bus stands, auto stands, metro stations and taxi "
        "stands to a coordinate, using a PostGIS distance query."
    ),
)
def nearby_transport_nodes(
    latitude: float,
    longitude: float,
    node_type: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    from transport.models import TransportNode

    close_old_connections()
    try:
        origin = Point(longitude, latitude, srid=4326)
        queryset = TransportNode.objects.annotate(
            distance_m=Distance("location", origin)
        )
        if node_type and node_type != "all":
            queryset = queryset.filter(node_type=node_type)
        queryset = queryset.order_by("distance_m")[:limit]

        results = [
            {
                "id": node.id,
                "name": node.name,
                "node_type": node.get_node_type_display(),
                "city": node.city,
                "address": node.address,
                "distance_km": round((node.distance_m or 0) / 1000.0, 2),
                "location": _point_payload(node.location),
            }
            for node in queryset
        ]
        return _ok({"count": len(results), "results": results})
    except Exception as exc:  # noqa: BLE001
        return _fail(f"nearby transport lookup failed: {exc}")
    finally:
        close_old_connections()


# ===========================================================================
# Open data tools
# ===========================================================================


@blocking_tool(
    name="geocode_place",
    description=(
        "Turn a place name or address into coordinates using OpenStreetMap "
        "Nominatim. Returns up to 5 ranked matches with city, state and country."
    ),
)
def geocode_place(place_name: str, country_code: str | None = "in") -> dict[str, Any]:
    try:
        matches = opendata.geocode(place_name, country_codes=country_code)
        if not matches:
            return _ok(
                {
                    "count": 0,
                    "results": [],
                    "message": f"No location matched {place_name!r}.",
                }
            )
        return _ok({"count": len(matches), "results": matches})
    except Exception as exc:  # noqa: BLE001
        return _fail(f"geocoding failed: {exc}")


@blocking_tool(
    name="reverse_geocode",
    description="Resolve a latitude/longitude into the nearest street address using OpenStreetMap Nominatim.",
)
def reverse_geocode(latitude: float, longitude: float) -> dict[str, Any]:
    try:
        place = opendata.reverse_geocode(latitude, longitude)
        if not place:
            return _fail("No address found for that coordinate.")
        return _ok(place)
    except Exception as exc:  # noqa: BLE001
        return _fail(f"reverse geocoding failed: {exc}")


@blocking_tool(
    name="search_nearby_places",
    description=(
        "Find real-world places around a coordinate using OpenStreetMap "
        "Overpass. place_type accepts: restaurant, hotel, attraction, temple, "
        "museum, park, cafe, bus_stop, metro, taxi_stand, pharmacy, atm, shop."
    ),
)
def search_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "attraction",
    radius_meters: int = 1500,
    limit: int = 10,
) -> dict[str, Any]:
    try:
        places = opendata.search_nearby_places(
            latitude,
            longitude,
            place_type=place_type,
            radius_meters=radius_meters,
            limit=limit,
        )
        if not places:
            return _ok(
                {
                    "count": 0,
                    "results": [],
                    "message": f"No {place_type} found within {radius_meters}m.",
                }
            )
        return _ok(
            {"count": len(places), "place_type": place_type, "results": places}
        )
    except Exception as exc:  # noqa: BLE001
        return _fail(f"nearby place search failed: {exc}")


@blocking_tool(
    name="get_weather",
    description=(
        "Current weather plus a 3-day forecast for an Indian city, from "
        "Open-Meteo. Free and needs no API key."
    ),
)
def get_weather(city: str, forecast_days: int = 3) -> dict[str, Any]:
    try:
        forecast = opendata.get_weather(city, forecast_days=forecast_days)
        if not forecast:
            return _fail(f"No weather data available for {city!r}.")
        return _ok(forecast)
    except Exception as exc:  # noqa: BLE001
        return _fail(f"weather lookup failed: {exc}")


@blocking_tool(
    name="get_directions",
    description=(
        "Real road route between two coordinates via OSRM. Returns distance in "
        "km, duration in minutes and a GeoJSON geometry that can be drawn on "
        "a map."
    ),
)
def get_directions(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
) -> dict[str, Any]:
    try:
        route = opendata.get_directions(start_lat, start_lon, end_lat, end_lon)
        if not route:
            return _fail("No route found between those points.")
        return _ok(route)
    except Exception as exc:  # noqa: BLE001
        return _fail(f"routing failed: {exc}")


@blocking_tool(
    name="web_search",
    description=(
        "Search the live web for time-sensitive travel information: recent "
        "reviews, opening hours, prices, events, visa rules. Returns "
        "ok=False with a reason when no search key is configured."
    ),
)
def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    payload = opendata.web_search(query, max_results=max_results)
    if not payload.get("available"):
        return _fail(payload.get("reason", "web search unavailable"))
    return _ok(
        {"answer": payload.get("answer"), "results": payload.get("results", [])}
    )


# ===========================================================================
# Knowledge base
# ===========================================================================


@blocking_tool(
    name="search_knowledge_base",
    description=(
        "Semantic search over the Yatrip Pinecone knowledge base. Returns "
        "documents about listed hotels, attractions, food and rentals."
    ),
)
def search_knowledge_base(query: str, k: int = 4) -> dict[str, Any]:
    if not settings.PINECONE_API_KEY or not settings.GEMINI_API_KEY:
        return _fail("Knowledge base is not configured (PINECONE_API_KEY / GEMINI_API_KEY missing).")

    try:
        from langchain_core.documents import Document
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        from langchain_pinecone import PineconeVectorStore

        vector_store = PineconeVectorStore(
            index_name=settings.PINECONE_INDEX_NAME,
            embedding=GoogleGenerativeAIEmbeddings(
                model=settings.GEMINI_EMBEDDING_MODEL,
                google_api_key=settings.GEMINI_API_KEY,
            ),
            pinecone_api_key=settings.PINECONE_API_KEY,
        )
        documents = vector_store.similarity_search(query, k=k)
        return _ok(
            {
                "count": len(documents),
                "results": [
                    {
                        "source": (document.metadata or {}).get("source", "yatrip"),
                        "title": (document.metadata or {}).get("title", "Listing"),
                        "excerpt": document.page_content[:500],
                    }
                    for document in documents
                ],
            }
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Knowledge base search failed: %s", exc)
        return _fail("Knowledge base search is currently unavailable.")


# ---------------------------------------------------------------------------
# Small serialisation helper
# ---------------------------------------------------------------------------


def _point_payload(point: Any) -> dict[str, float] | None:
    if point is None:
        return None
    try:
        return {"latitude": round(point.y, 6), "longitude": round(point.x, 6)}
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Entrypoints
# ---------------------------------------------------------------------------


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run the Yatrip MCP server.")
    parser.add_argument(
        "--transport",
        default=settings.MCP_SERVER_TRANSPORT,
        choices=["stdio", "sse", "streamable-http"],
        help="Transport to serve on (default from MCP_SERVER_TRANSPORT).",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host for HTTP transports.")
    parser.add_argument(
        "--port", type=int, default=8000, help="Bind port for HTTP transports."
    )
    args = parser.parse_args()

    logger.info(
        "Starting Yatrip MCP server on %s (db=%s)",
        args.transport,
        settings.DATABASES["default"]["NAME"],
    )

    if args.transport == "stdio":
        mcp.run(transport="stdio")
        return

    mcp.settings.host = args.host
    mcp.settings.port = args.port
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
