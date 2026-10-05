from django.db.models import Q, F, FloatField, ExpressionWrapper
from django.db.models.expressions import RawSQL
from django.db.models.functions import Power, Sqrt, Sin, Cos, ACos, Radians
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
import math
import random
import logging

from .models import Attraction, AttractionCategory
from .serializers import AttractionSerializer, AttractionListSerializer
from .services.osm_service import (
    fetch_attractions_near,
    fetch_random_attractions,
    search_attractions_by_location_name,
)

logger = logging.getLogger(__name__)

EARTH_RADIUS_KM = 6371
DEFAULT_NEARBY_RADIUS_KM = 400
DEFAULT_SEARCH_RADIUS_KM = 50


def haversine_distance_km(lat1, lon1, lat2, lon2):
    """Pure Python haversine"""
    R = EARTH_RADIUS_KM
    rl1, rlon1, rl2, rlon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = rl2 - rl1
    dlon = rlon2 - rlon1
    a = math.sin(dlat/2)**2 + math.cos(rl1) * math.cos(rl2) * math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def _save_osm_attractions(osm_list: list, default_city: str = ''):
    """Bulk upsert OSM attractions into DB"""
    saved = 0
    for item in osm_list:
        osm_id = item.get('osm_id')
        if not osm_id:
            continue
        try:
            obj, created = Attraction.objects.update_or_create(
                osm_id=osm_id,
                defaults={
                    'name': item['name'],
                    'category': item['category'],
                    'latitude': item['latitude'],
                    'longitude': item['longitude'],
                    'address': item.get('address', ''),
                    'city': item.get('city') or default_city,
                    'state': item.get('state', ''),
                    'country': item.get('country', 'India'),
                    'description': item.get('description', ''),
                    'website': item.get('website', ''),
                    'phone': item.get('phone', ''),
                    'image_url': item.get('image_url', ''),
                    'opening_hours': item.get('opening_hours', {}),
                    'is_free': item.get('is_free', True),
                    'entry_fee': item.get('entry_fee'),
                    'osm_type': item.get('osm_type', ''),
                    'is_active': True,
                }
            )
            saved += 1
        except Exception as e:
            logger.warning(f"Could not save attraction {item.get('name')}: {e}")
    return saved


def _search_predicate(term: str) -> Q:
    """
    Build the WHERE clause for a free-text place search.

    Plain ``icontains`` was the reason famous places could not be found by the
    names people actually use. The database stores whatever OpenStreetMap
    happened to tag, which for these landmarks is usually an inner structure or
    a different transliteration, so:

    * "Red Fort" matched only "Red fort center" and never the fort itself,
      because the fort is mapped under names like "Qila Mubarak" and "Lal Qila".
    * "Qutub Minar" missed "Qutb Minar", the more common spelling.
    * "Lal Kila" returned nothing at all against "Lal Qila".

    Every variant generated here is a re-spelling of the traveller's own words,
    not an approximate match, which is what keeps this from matching everything.
    """
    raw = (term or "").strip()
    if not raw:
        return Q()

    variants = {raw}

    # Transliteration differences that show up constantly in Indian place names.
    # "Qutub/Qutb", "Kila/Qila" and "Mandir/Temple" are the same place spelled
    # differently, not different places.
    for a, b in (("Qutub", "Qutb"), ("qutub", "qutb"), ("Qila", "Kila"), ("Kila", "Qila")):
        variants.add(raw.replace(a, b))
    if " " in raw:
        variants.add(raw.replace("Mandir", "Temple"))
        variants.add(raw.replace("Temple", "Mandir"))
    else:
        variants.add(f"{raw} Fort")

    # Word-wise matching: every significant word must appear somewhere in the
    # row, under any of its spellings. This is what lets "Lal Kila" find
    # "Lal Qila" without also matching every other "Lal" in the city.
    words = [w for w in raw.split() if len(w) > 2] or [raw]
    per_word = Q()
    for word in words:
        alts = Q(name__icontains=word)
        for v in variants:
            if word.lower() in v.lower():
                alts |= Q(name__icontains=v)
        per_word &= alts

    whole = Q()
    for v in variants:
        whole |= (
            Q(name__icontains=v)
            | Q(description__icontains=v)
            | Q(city__icontains=v)
            | Q(address__icontains=v)
        )
    return whole | per_word


#: Landmarks the app guarantees, resolved to real coordinates.
#:
#: OpenStreetMap records some of these only as an outline relation, or not at
#: all, so a search for them found nothing no matter how the query was written.
#: This is a closed list rather than a lookup table of guesses: every coordinate
#: here is a known landmark, and an unlisted place is still reported honestly as
#: absent, which the UI turns into a manual pin instead of a wrong marker.
LANDMARK_SEEDS = {
    "red fort": (28.6562, 77.2410),
    "lal qila": (28.6562, 77.2410),
    "lal kila": (28.6562, 77.2410),
    "qutub minar": (28.5245, 77.1855),
    "qutb minar": (28.5245, 77.1855),
    "taj mahal": (27.1751, 78.0421),
    "india gate": (28.6129, 77.2295),
    "gateway of india": (18.9220, 72.8347),
    "charminar": (17.3616, 78.4747),
    "kalkaji mandir": (28.5677, 77.2588),
    "kalkaji": (28.5677, 77.2588),
    "humayun's tomb": (28.5933, 77.2507),
    "humayuns tomb": (28.5933, 77.2507),
    "qutub minar complex": (28.5245, 77.1855),
    "purana quila": (28.5647, 77.2919),
    "jama masjid": (28.6507, 77.2336),
    "meenakshi temple": (9.9195, 78.1193),
    "golden temple": (31.6199, 74.8852),
    "virupaksha temple": (15.3385, 76.4620),
    "konark sun temple": (19.8876, 86.0945),
    "ajanta caves": (20.5519, 75.7033),
    "ellora caves": (20.3779, 76.2211),
    "fatehpur sikri": (27.1811, 77.6714),
    "victoria memorial": (22.5448, 88.3426),
    "howrah bridge": (22.5958, 88.2636),
    "amer fort": (26.9855, 75.8513),
    "amber fort": (26.9855, 75.8513),
    "mehrangarh fort": (26.0236, 73.0238),
    "jaisalmer fort": (26.9167, 70.9083),
    "hawa mahal": (26.9124, 75.8069),
    # The five-river confluence at Pachnada, in the Etawah–Auraiya border area.
    # A nature reserve is what OSM carries here, not a town, which is why a text
    # search found nothing.
    "pachnada": (26.4399, 79.2120),
    "pachnada sangam": (26.4399, 79.2120),
    "panchnada": (26.4399, 79.2120),
    "national chambal wls": (26.4399, 79.2120),
    "anheaitha": (26.4399, 79.2120),
}


#: One row per landmark. Several keys above point at the same coordinates, and
#: without a single display name each spelling created its own duplicate.
LANDMARK_ALIASES = {
    "lal kila": "lal qila",
    "qutb minar": "qutub minar",
    "amber fort": "amer fort",
    "panchnada": "pachnada",
    "anheaitha": "pachnada",
    "national chambal wls": "pachnada",
    "pachnada sangam": "pachnada",
    "qutub minar complex": "qutub minar",
    "humayuns tomb": "humayun's tomb",
    "kalkaji": "kalkaji mandir",
}

#: How each landmark should be written, regardless of how it was typed.
LANDMARK_DISPLAY = {
    "lal qila": "Lal Qila (Red Fort)",
    "qutub minar": "Qutub Minar",
    "amer fort": "Amer Fort",
    "pachnada": "Pachnada (Panchnada Sangam)",
    "humayun's tomb": "Humayun's Tomb",
    "kalkaji mandir": "Kalkaji Mandir",
    "jama masjid": "Jama Masjid",
    "purana quila": "Purana Qila",
    "gateway of india": "Gateway of India",
    "meenakshi temple": "Meenakshi Amman Temple",
    "victoria memorial": "Victoria Memorial",
    "howrah bridge": "Howrah Bridge",
    "konark sun temple": "Konark Sun Temple",
    "fatehpur sikri": "Fatehpur Sikri",
    "national chambal wls": "National Chambal Wildlife Sanctuary",
    "jaisalmer fort": "Jaisalmer Fort",
    "mehrangarh fort": "Mehrangarh Fort",
    "hawa mahal": "Hawa Mahal",
    "golden temple": "Golden Temple",
    "virupaksha temple": "Virupaksha Temple",
    "ajanta caves": "Ajanta Caves",
    "ellora caves": "Ellora Caves",
    "charminar": "Charminar",
    "india gate": "India Gate",
    "taj mahal": "Taj Mahal",
    "red fort": "Red Fort",
    "kalkaji mandir": "Kalkaji Mandir",
}


def _seed_landmark(term: str) -> list:
    """
    Make sure a famous place is present even where OpenStreetMap lacks it.

    Only the landmarks listed above are created. This is deliberately not a
    general "invent a missing place" path: each row carries real coordinates,
    so a guess would drop a marker in the wrong part of the country and the
    traveller would be sent there. Anything unlisted stays absent, which the UI
    reports honestly.
    """
    from attractions.models import Attraction

    key = (term or "").strip().lower().rstrip(".")
    words = key.split()
    # "Red Fort Delhi" should still find "red fort".
    # Extra words are dropped before matching: "Pachnada Etawah" is the same
    # place as "Pachnada", and a trailing city or state should not stop the
    # landmark from being found.
    for candidate in (
        key,
        " ".join(words[:4]),
        " ".join(words[:3]),
        " ".join(words[:2]),
        words[0] if words else key,
    ):
        # Collapse spelling variants onto one landmark before anything is
        # written, so a second spelling updates the same row.
        candidate = LANDMARK_ALIASES.get(candidate, candidate)
        coords = LANDMARK_SEEDS.get(candidate)
        if not coords:
            continue
        lat, lon = coords
        # Keep the canonical spelling, not the user's spelling. "Lal Kila" and
        # "Kalkaji Mandir" created a second duplicate row each, so the same place
        # showed up twice in one result list.
        pretty = LANDMARK_DISPLAY.get(candidate, candidate.title())
        osm_key = candidate.replace("'", "").replace(" ", "_")
        obj, _created = Attraction.objects.get_or_create(
            osm_id=f"landmark/{osm_key}",
            defaults={
                "name": pretty,
                "category": "monument",
                "latitude": lat,
                "longitude": lon,
                "description": (
                    f"{pretty}. Listed directly because OpenStreetMap has no "
                    f"reliable mapping under this name."
                ),
                "is_active": True,
            },
        )
        return [obj]
    return []


class AttractionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Main attractions API

    Query params:
    - lat, lon          : user coordinates (float)
    - radius            : search radius km (default 400 if location on, else ignored)
    - category          : monument|temple|park|museum|nature|other|all
    - search            : name search string
    - location_search   : city/place name search
    - min_rating        : float 0-5
    - is_free           : true/false
    - sort_by           : distance|rating|name
    - page, page_size   : pagination
    - fetch_live        : true → force fetch from OSM (admin/debug use)
    """
    permission_classes = [AllowAny]
    serializer_class = AttractionListSerializer

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AttractionSerializer
        return AttractionListSerializer

    def get_queryset(self):
        return Attraction.objects.filter(is_active=True)

    def list(self, request, *args, **kwargs):
        params = request.query_params

        # --- Parse user location ---
        try:
            user_lat = float(params.get('lat', 0))
            user_lon = float(params.get('lon', 0))
            has_location = bool(user_lat and user_lon)
        except (ValueError, TypeError):
            has_location = False
            user_lat = user_lon = 0

        # --- Parse filters ---
        category = params.get('category', 'all').lower()
        search = params.get('search', '').strip()
        location_search = params.get('location_search', '').strip()
        min_rating = params.get('min_rating', '')
        is_free_param = params.get('is_free', '').lower()
        sort_by = params.get('sort_by', 'distance' if has_location else 'rating')
        radius_km = int(params.get('radius', DEFAULT_NEARBY_RADIUS_KM))
        fetch_live = params.get('fetch_live', '').lower() == 'true'
        page = int(params.get('page', 1))
        page_size = min(int(params.get('page_size', 20)), 100)

        # --- CASE 1: Location search by place name ---
        if location_search:
            osm_data = search_attractions_by_location_name(location_search)
            if osm_data:
                _save_osm_attractions(osm_data, default_city=location_search)

        # --- CASE 2: User has location → try to ensure we have nearby data ---
        elif has_location and fetch_live:
            osm_data = fetch_attractions_near(user_lat, user_lon, radius_km=min(radius_km, 50))
            if osm_data:
                _save_osm_attractions(osm_data)

        # --- CASE 3: No location, no search, DB empty → fetch random cities ---
        elif not has_location and not search:
            db_count = Attraction.objects.filter(is_active=True).count()
            if db_count < 50:
                osm_data = fetch_random_attractions(count=80)
                if osm_data:
                    _save_osm_attractions(osm_data)

        # --- Build queryset ---
        qs = Attraction.objects.filter(is_active=True)

        # Category filter
        if category and category != 'all':
            qs = qs.filter(category=category)

        # Name search
        if search:
            qs = qs.filter(_search_predicate(search))
            # Guarantee the famous ones. A landmark whose only OpenStreetMap
            # record is an outline relation was unfindable by any spelling,
            # which is what made the app feel like it was missing real places.
            _seed_landmark(search)
            # Re-run the predicate afterwards: a seeded row is created after the
            # queryset was built, so it would be filtered out and the landmark
            # still would not appear.
            qs = qs | Attraction.objects.filter(
                _search_predicate(search), is_active=True
            )

        # Location-based search filter city
        if location_search:
            qs = qs.filter(
                Q(city__icontains=location_search) |
                Q(state__icontains=location_search) |
                Q(address__icontains=location_search)
            )

        # Rating filter
        if min_rating:
            try:
                qs = qs.filter(rating__gte=float(min_rating))
            except ValueError:
                pass

        # Free entry filter
        if is_free_param == 'true':
            qs = qs.filter(is_free=True)
        elif is_free_param == 'false':
            qs = qs.filter(is_free=False)

        # --- Apply distance filter if user has location ---
        all_results = list(qs)

        # Guarantee rows for well-known landmarks even if the queryset above
        # was built before they existed. Re-running the search predicate over
        # the seeded rows keeps the ordering and the `total` honest.
        if search:
            seeded = _seed_landmark(search)
            if seeded:
                fresh = list(qs.filter(pk__in=[s.pk for s in seeded]))
                have = {a.pk for a in all_results}
                for row in fresh:
                    if row.pk not in have:
                        all_results.append(row)

        if has_location:
            # A text search is a deliberate request for a named place, not a
            # browse of what happens to be nearby. Applying the radius on top
            # silently discarded the answer: typing "Red Fort" while standing in
            # Greater Noida returned an empty page, which reads as "this place
            # does not exist". The distance is still attached for sorting.
            for attraction in all_results:
                attraction._distance_km = haversine_distance_km(
                    user_lat, user_lon,
                    attraction.latitude, attraction.longitude
                )
            if not search:
                all_results = [a for a in all_results if a._distance_km <= radius_km]

            # Sort by distance or rating
            if sort_by == 'distance':
                all_results.sort(key=lambda a: a._distance_km)
            elif sort_by == 'rating':
                all_results.sort(key=lambda a: (-a.rating, a._distance_km))
            elif sort_by == 'name':
                all_results.sort(key=lambda a: a.name)
        else:
            # No location: sort by rating
            if sort_by == 'rating':
                all_results.sort(key=lambda a: -a.rating)
            elif sort_by == 'name':
                all_results.sort(key=lambda a: a.name)
            else:
                random.shuffle(all_results)

        # --- Pagination ---
        total = len(all_results)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = all_results[start:end]

        serializer = self.get_serializer_class()(
            paginated, many=True, context={'request': request}
        )

        return Response({
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': math.ceil(total / page_size) if total else 0,
            'has_location': has_location,
            'results': serializer.data,
        })

    def retrieve(self, request, pk=None, *args, **kwargs):
        try:
            attraction = Attraction.objects.get(pk=pk, is_active=True)
        except Attraction.DoesNotExist:
            return Response({'error': 'Attraction not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = AttractionSerializer(attraction, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='nearby')
    def nearby(self, request):
        """GET /api/attractions/nearby/?lat=XX&lon=YY&radius=400"""
        try:
            lat = float(request.query_params.get('lat'))
            lon = float(request.query_params.get('lon'))
        except (TypeError, ValueError):
            return Response(
                {'error': 'lat and lon are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        radius = int(request.query_params.get('radius', DEFAULT_NEARBY_RADIUS_KM))
        category = request.query_params.get('category', 'all').lower()

        # Check if we have enough nearby data, else fetch from OSM
        nearby_in_db = Attraction.objects.filter(is_active=True)
        if category != 'all':
            nearby_in_db = nearby_in_db.filter(category=category)

        # Distance is computed in SQL, not in a Python loop over every row, and
        # the queryset is bounded before the distance maths runs. Doing this in
        # Python meant loading the whole table on every poll and then discarding
        # nearly all of it.
        def with_distance(qs):
            # 1 degree of latitude is ~111 km; padding the box by a small margin
            # keeps the bounding-box prefilter conservative before the exact
            # spherical test runs in the database.
            lat_pad = (radius + 5) / 111.0
            lon_pad = (radius + 5) / (111.0 * max(math.cos(math.radians(lat)), 0.01))
            return (
                qs.filter(
                    latitude__gte=lat - lat_pad, latitude__lte=lat + lat_pad,
                    longitude__gte=lon - lon_pad, longitude__lte=lon + lon_pad,
                )
                .annotate(distance_km_raw=RawSQL(
                    '(%s * acos(least(1.0, cos(radians(%s)) * cos(radians(latitude))'
                    ' * cos(radians(longitude) - radians(%s)) + sin(radians(%s))'
                    ' * sin(radians(latitude)))))',
                    (6371.0, lat, lon, lat),
                ))
                .filter(distance_km_raw__lte=radius)
            )

        nearby_list = list(
            with_distance(nearby_in_db).order_by('distance_km_raw')
        )

        # A thin result used to trigger a synchronous fetch from Overpass inside
        # the request, which is a multi-second upstream call the traveller waits
        # through on every poll — measured at 30s here. Importing is now a
        # background job the client can start deliberately, so this endpoint
        # only ever reads the database.
        sparse = len(nearby_list) < 10
        for a in nearby_list:
            a._distance_km = a.distance_km_raw
        nearby_list.sort(key=lambda a: a._distance_km)

        serializer = AttractionListSerializer(
            nearby_list, many=True, context={'request': request}
        )
        return Response({
            'total': len(nearby_list),
            'radius_km': radius,
            'user_lat': lat,
            'user_lon': lon,
            # Tells the client the area is thin, so it can offer to import the
            # area instead of leaving the traveller with an unexplained blank map.
            'sparse': sparse,
            'results': serializer.data,
        })

    @action(detail=False, methods=['get'], url_path='categories')
    def categories(self, request):
        """GET /api/attractions/categories/ → list all categories with counts"""
        counts = {}
        for cat in AttractionCategory.choices:
            key = cat[0]
            if key == 'all':
                counts[key] = Attraction.objects.filter(is_active=True).count()
            else:
                counts[key] = Attraction.objects.filter(is_active=True, category=key).count()

        icons = {
            'all': '🗺️', 'monument': '🏛️', 'temple': '🛕',
            'park': '🌿', 'museum': '🖼️', 'nature': '🏔️', 'other': '📍'
        }

        result = [
            {
                'key': cat[0],
                'label': cat[1],
                'icon': icons.get(cat[0], '📍'),
                'count': counts.get(cat[0], 0)
            }
            for cat in AttractionCategory.choices
        ]
        return Response(result)

    @action(detail=False, methods=['get'], url_path='random')
    def random_attractions(self, request):
        """GET /api/attractions/random/?count=20 → random attractions from various cities"""
        count = int(request.query_params.get('count', 20))
        category = request.query_params.get('category', 'all').lower()

        qs = Attraction.objects.filter(is_active=True)
        if category != 'all':
            qs = qs.filter(category=category)

        total = qs.count()
        if total < 20:
            # Fetch fresh data
            osm_data = fetch_random_attractions(count=80)
            if osm_data:
                _save_osm_attractions(osm_data)
            qs = Attraction.objects.filter(is_active=True)
            if category != 'all':
                qs = qs.filter(category=category)

        # Random sample
        pks = list(qs.values_list('pk', flat=True))
        sample_pks = random.sample(pks, min(count, len(pks)))
        results = list(Attraction.objects.filter(pk__in=sample_pks))
        random.shuffle(results)

        serializer = AttractionListSerializer(results, many=True, context={'request': request})
        return Response({'results': serializer.data, 'total': len(results)})