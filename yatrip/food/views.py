from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Q
import math, random, logging

from .models import FoodPlace, FoodCategory, CuisineType
from .serializers import FoodPlaceListSerializer, FoodPlaceDetailSerializer
from .services.osm_food_service import (
    fetch_food_near, fetch_random_food, search_food_by_location
)

logger = logging.getLogger(__name__)
EARTH_R = 6371


def _haversine(lat1, lon1, lat2, lon2):
    rl1, rlo1, rl2, rlo2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = rl2 - rl1, rlo2 - rlo1
    a = math.sin(dlat/2)**2 + math.cos(rl1)*math.cos(rl2)*math.sin(dlon/2)**2
    return 2 * EARTH_R * math.asin(math.sqrt(a))


def _save_food(osm_list: list, default_city=''):
    saved = 0
    for item in osm_list:
        osm_id = item.get('osm_id')
        if not osm_id:
            continue
        try:
            FoodPlace.objects.update_or_create(
                osm_id=osm_id,
                defaults={
                    'name':        item['name'],
                    'category':    item['category'],
                    'cuisine':     item['cuisine'],
                    'latitude':    item['latitude'],
                    'longitude':   item['longitude'],
                    'address':     item.get('address', ''),
                    'city':        item.get('city') or default_city,
                    'state':       item.get('state', ''),
                    'country':     item.get('country', 'India'),
                    'description': item.get('description', ''),
                    'website':     item.get('website', ''),
                    'phone':       item.get('phone', ''),
                    'image_url':   item.get('image_url', ''),
                    'opening_hours': item.get('opening_hours', {}),
                    'price_level': item.get('price_level', 1),
                    'is_veg':      item.get('is_veg'),
                    'takeaway':    item.get('takeaway', False),
                    'outdoor_seating': item.get('outdoor_seating', False),
                    'home_delivery':   item.get('home_delivery', False),
                    'osm_type':    item.get('osm_type', ''),
                    'is_active':   True,
                }
            )
            saved += 1
        except Exception as e:
            logger.warning(f"Skip food place {item.get('name')}: {e}")
    return saved


class FoodPlaceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Food places API — street food, restaurants, cafes, dhabas etc.

    Query params:
      lat, lon          — user coordinates
      radius            — km (default 10 for food, 400 max)
      category          — street_food|restaurant|cafe|dhaba|bakery|sweet_shop|juice_bar|fast_food|other|all
      cuisine           — north_indian|south_indian|chinese|mughlai|...
      search            — name search
      location_search   — city/place name
      is_veg            — true|false
      min_rating        — float
      delivery          — true (home delivery only)
      price_level       — 1|2|3|4
      sort_by           — distance|rating|name
      page, page_size
    """
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        return FoodPlaceDetailSerializer if self.action == 'retrieve' else FoodPlaceListSerializer

    def get_queryset(self):
        return FoodPlace.objects.filter(is_active=True)

    def list(self, request, *args, **kwargs):
        p = request.query_params

        # Parse location
        try:
            user_lat = float(p.get('lat', 0))
            user_lon = float(p.get('lon', 0))
            has_location = bool(user_lat and user_lon)
        except (ValueError, TypeError):
            has_location = False
            user_lat = user_lon = 0

        # Parse filters
        category        = p.get('category', 'all').lower()
        cuisine         = p.get('cuisine', '').lower()
        search          = p.get('search', '').strip()
        location_search = p.get('location_search', '').strip()
        is_veg          = p.get('is_veg', '').lower()
        min_rating      = p.get('min_rating', '')
        delivery        = p.get('delivery', '').lower()
        price_level     = p.get('price_level', '')
        sort_by         = p.get('sort_by', 'distance' if has_location else 'rating')
        radius_km       = int(p.get('radius', 10 if has_location else 400))
        fetch_live      = p.get('fetch_live', '').lower() == 'true'
        page            = int(p.get('page', 1))
        page_size       = min(int(p.get('page_size', 20)), 100)

        # ── Fetch live OSM data if needed ──
        if location_search:
            osm = search_food_by_location(location_search)
            if osm:
                _save_food(osm, default_city=location_search)

        elif has_location and fetch_live:
            osm = fetch_food_near(user_lat, user_lon, radius_km=min(radius_km, 10))
            if osm:
                _save_food(osm)

        elif not has_location and not search:
            if FoodPlace.objects.filter(is_active=True).count() < 50:
                osm = fetch_random_food(count=100)
                if osm:
                    _save_food(osm)

        # ── Build queryset ──
        qs = FoodPlace.objects.filter(is_active=True)

        if category and category != 'all':
            qs = qs.filter(category=category)
        if cuisine:
            qs = qs.filter(cuisine=cuisine)
        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(city__icontains=search) |
                Q(cuisine__icontains=search) |
                Q(description__icontains=search)
            )
        if location_search:
            qs = qs.filter(
                Q(city__icontains=location_search) |
                Q(state__icontains=location_search) |
                Q(address__icontains=location_search)
            )
        if is_veg == 'true':
            qs = qs.filter(is_veg=True)
        elif is_veg == 'false':
            qs = qs.filter(is_veg=False)
        if delivery == 'true':
            qs = qs.filter(home_delivery=True)
        if min_rating:
            try:
                qs = qs.filter(rating__gte=float(min_rating))
            except ValueError:
                pass
        if price_level:
            try:
                qs = qs.filter(price_level=int(price_level))
            except ValueError:
                pass

        # ── Distance filter + sort ──
        all_results = list(qs)

        if has_location:
            for fp in all_results:
                fp._distance_km = _haversine(user_lat, user_lon, fp.latitude, fp.longitude)
            all_results = [fp for fp in all_results if fp._distance_km <= radius_km]
            if sort_by == 'distance':
                all_results.sort(key=lambda x: x._distance_km)
            elif sort_by == 'rating':
                all_results.sort(key=lambda x: (-x.rating, x._distance_km))
            else:
                all_results.sort(key=lambda x: x.name)
        else:
            if sort_by == 'rating':
                all_results.sort(key=lambda x: -x.rating)
            elif sort_by == 'name':
                all_results.sort(key=lambda x: x.name)
            else:
                random.shuffle(all_results)

        total = len(all_results)
        start = (page - 1) * page_size
        paginated = all_results[start:start + page_size]

        serializer = FoodPlaceListSerializer(paginated, many=True, context={'request': request})
        return Response({
            'total':        total,
            'page':         page,
            'page_size':    page_size,
            'total_pages':  math.ceil(total / page_size) if total else 0,
            'has_location': has_location,
            'results':      serializer.data,
        })

    def retrieve(self, request, pk=None):
        try:
            obj = FoodPlace.objects.get(pk=pk, is_active=True)
        except FoodPlace.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(FoodPlaceDetailSerializer(obj, context={'request': request}).data)

    @action(detail=False, methods=['get'], url_path='nearby')
    def nearby(self, request):
        try:
            lat = float(request.query_params.get('lat'))
            lon = float(request.query_params.get('lon'))
        except (TypeError, ValueError):
            return Response({'error': 'lat and lon required'}, status=400)

        radius   = int(request.query_params.get('radius', 10))
        category = request.query_params.get('category', 'all').lower()

        qs = FoodPlace.objects.filter(is_active=True)
        if category != 'all':
            qs = qs.filter(category=category)

        nearby = []
        for fp in qs:
            d = _haversine(lat, lon, fp.latitude, fp.longitude)
            if d <= radius:
                fp._distance_km = d
                nearby.append(fp)

        if len(nearby) < 5:
            osm = fetch_food_near(lat, lon, radius_km=radius)
            if osm:
                _save_food(osm)
                qs2 = FoodPlace.objects.filter(is_active=True)
                if category != 'all':
                    qs2 = qs2.filter(category=category)
                nearby = []
                for fp in qs2:
                    d = _haversine(lat, lon, fp.latitude, fp.longitude)
                    if d <= radius:
                        fp._distance_km = d
                        nearby.append(fp)

        nearby.sort(key=lambda x: x._distance_km)
        serializer = FoodPlaceListSerializer(nearby, many=True, context={'request': request})
        return Response({'total': len(nearby), 'radius_km': radius, 'results': serializer.data})

    @action(detail=False, methods=['get'], url_path='categories')
    def categories(self, request):
        icons = {
            'all': '🍴', 'street_food': '🥘', 'restaurant': '🍽️',
            'cafe': '☕', 'dhaba': '🍛', 'bakery': '🥐',
            'sweet_shop': '🍬', 'juice_bar': '🥤', 'fast_food': '🍔', 'other': '🍴',
        }
        result = []
        for cat in FoodCategory.choices:
            key = cat[0]
            count = (FoodPlace.objects.filter(is_active=True).count()
                     if key == 'all'
                     else FoodPlace.objects.filter(is_active=True, category=key).count())
            result.append({'key': key, 'label': cat[1], 'icon': icons.get(key,'🍴'), 'count': count})
        return Response(result)

    @action(detail=False, methods=['get'], url_path='cuisines')
    def cuisines(self, request):
        result = [{'key': c[0], 'label': c[1]} for c in CuisineType.choices]
        return Response(result)

    @action(detail=False, methods=['get'], url_path='random')
    def random_food(self, request):
        count    = int(request.query_params.get('count', 20))
        category = request.query_params.get('category', 'all').lower()
        qs = FoodPlace.objects.filter(is_active=True)
        if category != 'all':
            qs = qs.filter(category=category)
        if qs.count() < 20:
            _save_food(fetch_random_food(100))
            qs = FoodPlace.objects.filter(is_active=True)
            if category != 'all':
                qs = qs.filter(category=category)
        pks    = list(qs.values_list('pk', flat=True))
        sample = random.sample(pks, min(count, len(pks)))
        results = list(FoodPlace.objects.filter(pk__in=sample))
        random.shuffle(results)
        return Response({'results': FoodPlaceListSerializer(results, many=True, context={'request': request}).data})