from django.db.models import Q, F, FloatField, ExpressionWrapper
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
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(city__icontains=search) |
                Q(description__icontains=search)
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

        if has_location:
            # Annotate distance and filter within radius
            for attraction in all_results:
                attraction._distance_km = haversine_distance_km(
                    user_lat, user_lon,
                    attraction.latitude, attraction.longitude
                )
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

        nearby_list = []
        for a in nearby_in_db:
            d = haversine_distance_km(lat, lon, a.latitude, a.longitude)
            if d <= radius:
                a._distance_km = d
                nearby_list.append(a)

        # If less than 10 results, fetch live from OSM
        if len(nearby_list) < 10:
            osm_data = fetch_attractions_near(lat, lon, radius_km=min(radius, 100))
            if osm_data:
                _save_osm_attractions(osm_data)
                # Re-query
                nearby_in_db = Attraction.objects.filter(is_active=True)
                if category != 'all':
                    nearby_in_db = nearby_in_db.filter(category=category)
                nearby_list = []
                for a in nearby_in_db:
                    d = haversine_distance_km(lat, lon, a.latitude, a.longitude)
                    if d <= radius:
                        a._distance_km = d
                        nearby_list.append(a)

        nearby_list.sort(key=lambda a: a._distance_km)

        serializer = AttractionListSerializer(
            nearby_list, many=True, context={'request': request}
        )
        return Response({
            'total': len(nearby_list),
            'radius_km': radius,
            'user_lat': lat,
            'user_lon': lon,
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