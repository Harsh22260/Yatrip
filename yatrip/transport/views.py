from __future__ import annotations

import hashlib
import logging
import threading
from collections import Counter

from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.core.cache import cache
from django.db.models import Count, FloatField
from django.db.models.functions import Cast
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from yatrip import opendata

from .models import TransportNode
from .serializers import TransportNodeSerializer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Background area imports
# ---------------------------------------------------------------------------
# An Overpass sync is a few hundred rate-limited HTTP requests; for a 25 km area
# that is minutes, not seconds. Running it inside the request meant the browser
# simply gave up first and showed "Could not load transport for this area", even
# when the import went on to succeed server-side. The work is therefore handed
# to a worker thread and the client polls for the outcome.
#
# Progress lives in the Django cache, so with Redis configured several workers
# see the same job; without it the LocMem fallback still works for a single
# process. A real deployment should point this at Celery, which is already
# configured, but a thread keeps the feature working on a bare dev machine with
# no broker running.
JOBS_TTL_SEC = 60 * 60
_jobs_lock = threading.Lock()


def _job_key(job_id: str) -> str:
    return f"transport:job:{job_id}"


def _job_id_for(lat: float, lon: float, radius_km: float, place: str) -> str:
    """Stable id for an area, so a second click joins the running job."""
    raw = f"{lat:.3f},{lon:.3f},{radius_km:.1f},{(place or '').lower()}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def _run_import(job_id: str, lat, lon, radius_km: float, place: str) -> None:
    from .services import osm_transport

    def publish(**fields):
        state = _job_read(job_id) or {}
        state.update(fields)
        cache.set(_job_key(job_id), state, JOBS_TTL_SEC)
        return state

    publish(status="running", message="Asking OpenStreetMap for every stop in this area…")
    try:
        if lat is not None and lon is not None:
            result = osm_transport.fetch_near(float(lat), float(lon), radius_km, city=place)
        else:
            result = osm_transport.fetch_for_city(place, radius_km)
    except Exception as exc:  # noqa: BLE001
        logger.exception("On-demand transport import failed for %r", place or (lat, lon))
        publish(
            status="error",
            # The traveller's action did fail, so say so rather than implying
            # the map is simply empty because the place has no stops.
            message=f"Could not reach the OpenStreetMap data source: {str(exc)[:160]}",
        )
        return

    # The import just added rows, so every cached neighbourhood query around
    # this point is now stale. Without this the client would poll, see the old
    # empty count, and conclude nothing had loaded.
    _invalidate_nearby(float(lat), float(lon) if lon is not None else None)

    publish(
        status="done",
        created=result.get("created", 0),
        updated=result.get("updated", 0),
        message=(
            f"Added {result.get('created', 0)} new stops "
            f"and refreshed {result.get('updated', 0)}."
        ),
    )


def _job_read(job_id: str) -> dict | None:
    return cache.get(_job_key(job_id))


def _invalidate_nearby(lat: float, lon: float | None) -> None:
    """Drop cached nearby payloads around a point that just changed."""
    if lon is None:
        return
    centre = "transport:nearby:%s:%s:" % (f"{lat:.3f}", f"{lon:.3f}")
    try:
        from django.db import connection

        # The key embeds rounded centre and radius, so it cannot be deleted by
        # exact match. The cache prefix is matched the only way a plain key-value
        # store allows: re-deriving the handful of radii the app actually asks
        # for, which the client never varies.
        for radius in (2, 5, 10, 15, 20, 25, 50):
            for limit in (100, 300):
                cache.delete(f"{centre}{radius:.1f}:{limit}")
    except Exception:  # noqa: BLE001
        logger.warning("could not invalidate nearby cache", exc_info=True)
    finally:
        connection.close()


def _coord(request, name: str) -> float | None:
    raw = request.query_params.get(name)
    if raw in (None, ""):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number, got {raw!r}")


class TransportNodeViewSet(viewsets.ModelViewSet):
    queryset = TransportNode.objects.all().order_by("-created_at")
    serializer_class = TransportNodeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @action(detail=False, methods=["get"])
    def nearby(self, request):
        """
        Transport hubs around a point, with a real radius and per-type counts.

        The legend counts the things the user can actually reach, so the API
        returns the type breakdown alongside the rows. Previously the radius was
        ignored and the result was capped at a flat 20 with no way for the UI
        to tell "no bus stands here" from "there are some, just not in the
        first 20".
        """
        try:
            lat = _coord(request, "lat")
            lon = _coord(request, "lon")
        except ValueError as exc:
            return Response({"error": str(exc), "code": "bad_coords"}, status=status.HTTP_400_BAD_REQUEST)
        if lat is None or lon is None:
            return Response(
                {"error": "lat and lon are required", "code": "missing_coords"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not -90 <= lat <= 90 or not -180 <= lon <= 180:
            return Response(
                {"error": "lat must be -90..90 and lon -180..180", "code": "bad_coords"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            radius_km = float(request.query_params.get("radius_km", 10))
        except (TypeError, ValueError):
            radius_km = 10.0
        radius_km = max(0.1, min(radius_km, 100.0))

        try:
            limit = int(request.query_params.get("limit", 200))
        except (TypeError, ValueError):
            limit = 200
        limit = max(1, min(limit, 500))

        return self._nearby_payload(lat, lon, radius_km, limit)

    def _nearby_payload(
        self, lat: float, lon: float, radius_km: float, limit: int
    ) -> Response:
        """
        Shared by ``nearby`` and ``load_area``.

        Extracted so the on-demand import can return exactly what the client
        would have got from a follow-up GET. It previously tried to fake this by
        writing back to ``request.query_params``, which is a read-only property
        on a DRF request and raised on every call.
        """
        user_location = Point(lon, lat, srid=4326)

        # A traveller standing still polls this endpoint every few seconds, and
        # each poll was a full spatial query. Rounding the centre to ~100 m and
        # the radius to 0.5 km means those repeat calls share one cache entry.
        # With Redis configured this is shared across workers; without it, the
        # LocMem fallback still absorbs the repeats within this process.
        cache_key = "transport:nearby:%s:%s:%s:%s" % (
            f"{lat:.3f}",
            f"{lon:.3f}",
            f"{radius_km:.1f}",
            limit,
        )
        cached = cache.get(cache_key)
        if cached is not None:
            cached["cached"] = True
            return Response(cached)

        qs = TransportNode.objects.filter(
            is_active=True,
            location__distance_lte=(user_location, radius_km * 1000),
        )
        nodes = list(
            qs.annotate(
                # Cast is required: naming an alias `distance_m` collides with
                # the Distance function in the annotation namespace, so Django
                # hands back the function object and round() raises
                # "type Distance doesn't define __round__".
                distance_m=Cast(Distance("location", user_location), FloatField())
            )
            .order_by("distance_m")[:limit]
        )

        data = self.get_serializer(nodes, many=True).data
        for row, node in zip(data, nodes):
            # Distance comes back in the units of the geography field, so it is
            # metres here. Surfacing it as a raw float was unhelpful.
            row["distance_m"] = round(float(getattr(node, "distance_m", 0) or 0), 1)
            row["distance_km"] = round(row["distance_m"] / 1000, 2)

        # Counted over the whole radius, not over the truncated result page.
        # Counting the page is what made the legend claim 0 for a type that had
        # stops nearby, purely because they fell past the limit.
        by_type = dict(
            qs.values_list("node_type", flat=True)
            .annotate(n=Count("id"))
            .values_list("node_type", "n")
        )
        total_in_radius = sum(by_type.values())

        payload = {
            "count": len(data),
            "total_in_radius": total_in_radius,
            "radius_km": radius_km,
            "by_type": by_type,
            "results": data,
            "cached": False,
        }
        cache.set(cache_key, payload, settings.CACHE_TTL_NEARBY)
        return Response(payload)

    @action(
        detail=False,
        methods=["post"],
        # The rest of the transport tab is readable without an account, so the
        # on-demand import is too. It only ever adds public OpenStreetMap data
        # to a shared cache; it does not write anything user-owned.
        permission_classes=[permissions.AllowAny],
    )
    def load_area(self, request):
        """
        Start (or join) a background import of transport hubs for a place.

        The catalogue is only as good as what has been imported, so a traveller
        arriving somewhere new needs the app to pull that area in rather than
        show an empty map.

        This deliberately does not wait for the import. A 25 km area is a few
        hundred rate-limited Overpass requests, so doing it inline meant the
        client's request died long before the work did and the UI reported a
        failure for an import that had actually succeeded. The caller gets a job
        id immediately and polls ``load_area_status``.
        """
        # Accept the parameters from the JSON body or the query string.
        # Reading only `request.data` meant a caller that passed them as a URL —
        # curl, a bookmark, a quick test in the browser — got
        # "Provide either lat/lon or a place name" even though it had done
        # nothing wrong.
        sources = [request.data if request.data else {}]
        if request.query_params:
            sources.append(request.query_params)

        def pick(key, default=None):
            for src in sources:
                value = src.get(key)
                if value not in (None, ""):
                    return value
            return default

        lat = pick("lat")
        lon = pick("lon")
        place = str(pick("place") or "").strip()

        try:
            radius_km = float(pick("radius_km", 25))
        except (TypeError, ValueError):
            radius_km = 25.0
        radius_km = max(1.0, min(radius_km, 100.0))

        if lat is None or lon is None:
            if not place:
                return Response(
                    {"error": "Provide either lat/lon or a place name.",
                     "code": "missing_location"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Resolve the name to a centre so the worker and the client agree on
            # which area is being imported.
            try:
                hit = opendata.geocode(place)
            except Exception:  # noqa: BLE001
                hit = None
            if not hit:
                return Response(
                    {"error": f"Could not find “{place}” on the map.",
                     "code": "place_not_found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            lat, lon = float(hit["lat"]), float(hit["lon"])

        lat, lon = float(lat), float(lon)
        job_id = _job_id_for(lat, lon, radius_km, place)
        with _jobs_lock:
            state = _job_read(job_id)
            if state and state.get("status") == "running":
                # Already importing this exact area; let the caller follow along
                # instead of launching a duplicate burst against Overpass.
                return Response(
                    {"job_id": job_id, "status": "running", "message": state.get("message", "")},
                    status=status.HTTP_202_ACCEPTED,
                )
            cache.set(
                _job_key(job_id),
                {"status": "queued", "message": "Starting…"},
                JOBS_TTL_SEC,
            )
            threading.Thread(
                target=_run_import,
                args=(job_id, lat, lon, radius_km, place),
                daemon=True,
            ).start()

        return Response(
            {
                "job_id": job_id,
                "status": "running",
                "lat": lat,
                "lon": lon,
                "radius_km": radius_km,
                "message": "Importing in the background. This can take a couple of minutes.",
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def load_area_status(self, request):
        """Poll the outcome of a background import started by ``load_area``."""
        job_id = (request.query_params.get("job_id") or "").strip()
        if not job_id:
            return Response(
                {"error": "job_id is required.", "code": "missing_job_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        state = _job_read(job_id)
        if not state:
            return Response(
                {"error": "That job is no longer known. Try loading again.",
                 "code": "job_expired"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"job_id": job_id, **state})

    @action(detail=False, methods=["get"])
    def route(self, request):
        """
        Route for a chosen travel mode, across an optional multi-stop trip.

        Accepts either the original start/end pair, or ``waypoints`` as a
        semicolon-separated "lat,lon;lat,lon;..." list, which is how a map app
        plans a trip with several stops in order. ``profile`` selects the OSRM
        router, because a pedestrian and a car do not get the same legal path.
        """
        profile = (request.query_params.get("profile") or "car").lower()
        if profile not in opendata.OSRM_PROFILES:
            return Response(
                {
                    "error": f"Unknown profile {profile!r}. Use one of: "
                             + ", ".join(sorted(opendata.OSRM_PROFILES)),
                    "code": "bad_profile",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        raw_waypoints = request.query_params.get("waypoints")
        points: list[tuple[float, float]] = []

        if raw_waypoints:
            try:
                for chunk in raw_waypoints.split(";"):
                    chunk = chunk.strip()
                    if not chunk:
                        continue
                    lat_s, _, lon_s = chunk.partition(",")
                    points.append((float(lat_s), float(lon_s)))
            except (TypeError, ValueError):
                return Response(
                    {"error": "waypoints must look like 'lat,lon;lat,lon;...'",
                     "code": "bad_coords"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            try:
                start_lat = _coord(request, "start_lat")
                start_lon = _coord(request, "start_lon")
                end_lat = _coord(request, "end_lat")
                end_lon = _coord(request, "end_lon")
            except ValueError as exc:
                return Response({"error": str(exc), "code": "bad_coords"},
                                status=status.HTTP_400_BAD_REQUEST)

            if None in (start_lat, start_lon, end_lat, end_lon):
                return Response(
                    {"error": "start_lat, start_lon, end_lat and end_lon are all required "
                              "(or pass ?waypoints=lat,lon;lat,lon)",
                     "code": "missing_coords"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            points = [(start_lat, start_lon), (end_lat, end_lon)]

        for lat, lon in points:
            if not -90 <= lat <= 90 or not -180 <= lon <= 180:
                return Response({"error": "coordinates out of range", "code": "bad_coords"},
                                status=status.HTTP_400_BAD_REQUEST)

        if len(points) < 2:
            return Response(
                {"error": "At least two points are needed to plan a route.",
                 "code": "missing_coords"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(points) > 25:
            return Response(
                {"error": "Too many stops (max 25).", "code": "too_many_waypoints"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            route = opendata.get_multi_directions(points, profile=profile)
        except Exception:  # noqa: BLE001
            logger.exception("Routing failed for %s points (%s)", len(points), profile)
            route = None

        if not route:
            return Response(
                {
                    "error": "The routing service is unavailable right now. Please try again.",
                    "code": "routing_unavailable",
                    "waypoints": [[lat, lon] for lat, lon in points],
                    "profile": profile,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "start": list(points[0]),
                "end": list(points[-1]),
                "waypoints": [[lat, lon] for lat, lon in points],
                "profile": profile,
                "router": route["profile"],
                "distance_km": route["distance_km"],
                "duration_min": route["duration_min"],
                "geometry": route.get("geometry"),
                "legs": route.get("legs") or [],
                "source": "OSRM",
            }
        )
