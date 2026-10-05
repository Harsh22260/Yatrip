from django.core.cache import cache
from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, UserRateThrottle
import logging
import math
import random

from .models import FoodPlace, FoodCategory, CuisineType, MenuItem
from .serializers import (
    FoodPlaceDetailSerializer,
    FoodPlaceListSerializer,
    FoodPlaceWriteSerializer,
    MenuItemSerializer,
)
from .services.osm_food_service import (
    fetch_food_near,
    search_food_by_location,
)

logger = logging.getLogger(__name__)
EARTH_R = 6371

#: A "city" string is whatever Nominatim resolved, not free text, so the key is
#: built from the geocoded name rather than the raw query the user typed.
OSM_IMPORT_LOCK_TTL = 300

CATEGORY_ICONS = {
    'all': '🍴', 'street_food': '🥘', 'restaurant': '🍽️',
    'cafe': '☕', 'dhaba': '🍛', 'bakery': '🥐',
    'sweet_shop': '🍬', 'juice_bar': '🥤', 'fast_food': '🍔', 'other': '🍴',
}


def _haversine(lat1, lon1, lat2, lon2):
    rl1, rlo1, rl2, rlo2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = rl2 - rl1, rlo2 - rlo1
    a = math.sin(dlat/2)**2 + math.cos(rl1)*math.cos(rl2)*math.sin(dlon/2)**2
    return 2 * EARTH_R * math.asin(math.sqrt(a))


def _int_param(params, key, default, *, minimum=None, maximum=None):
    """
    Read an int query param without ever raising.

    ``int(request.query_params['page'])`` turned a stray ``?page=abc`` into a
    500 on the whole endpoint. Garbage in, default out.
    """
    try:
        value = int(params.get(key, default))
    except (TypeError, ValueError):
        return default
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def _bool_param(params, key):
    return str(params.get(key, '')).strip().lower() in {'1', 'true', 'yes', 'on'}


def _float_param(params, key):
    try:
        return float(params.get(key))
    except (TypeError, ValueError):
        return None


def _save_food(osm_list: list, default_city=''):
    """
    Upsert OSM rows.

    ``rating``/``review_count`` are deliberately not written: Overpass carries no
    ratings, and the old fetch command pushed a hardcoded ``0.0`` over any real
    rating on every re-sync. Fields absent from the payload keep their current
    value for the same reason.
    """
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
                    'country':     item.get('country') or 'India',
                    'description': item.get('description', ''),
                    'website':     item.get('website', ''),
                    'phone':       item.get('phone', ''),
                    'image_url':   item.get('image_url', ''),
                    'image_credit': item.get('image_credit', ''),
                    'opening_hours': item.get('opening_hours') or {},
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
            logger.warning("Skip food place %s: %s", item.get('name'), e)
    return saved


def _is_locked(key):
    """
    One in-flight import per area.

    Without this, every request that found a thin area issued its own Overpass
    call, so N concurrent page loads became N upstream requests and all of them
    waited on it.
    """
    return cache.add(key, '1', OSM_IMPORT_LOCK_TTL) is False


def _unlock(key):
    """Release the lock once the import finished (or failed)."""
    cache.delete(key)


class ScopedThrottle(ScopedRateThrottle):
    """
    ScopedRateThrottle with its scope bound in the constructor.

    The scope is a class attribute on the stock throttle, so the only way to get
    two different budgets out of it is a subclass. Instantiating
    ``ScopedRateThrottle(scope=...)`` passes an unexpected keyword straight to
    ``SimpleRateThrottle.__init__`` and raises at request time.
    """

    def __init__(self, scope):
        self.scope = scope
        super().__init__()


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level write restriction.

    ``IsAuthenticatedOrReadOnly`` alone only checks *that* someone is signed in,
    not *who*: any authenticated user could PATCH or DELETE another owner's
    outlet, or an OSM-imported row, because ``update_or_create`` rows have
    ``owner = NULL``. So ownership is checked per object here.
    """

    message = 'You can only change food places that you own.'

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        owner_id = getattr(obj, 'owner_id', None)
        return owner_id is not None and owner_id == request.user.id


class FoodPlaceViewSet(viewsets.ModelViewSet):
    """
    Food places API — street food, restaurants, cafes, dhabas etc.

    GET is public. Writes require authentication and are restricted to the
    owning user, which is what ``RegisterFoodPage`` and ``MyFoodPlacesPage`` need.

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
      mine              — true (own listings only)
      page, page_size
    """

    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    # Browsing food is a plain database read and gets the same budget as the rest
    # of the API. Overpass-backed import gets its own, much tighter scope, applied
    # in get_throttles().
    throttle_classes = [AnonRateThrottle, UserRateThrottle]
    import_scope = 'food_import'

    def get_serializer_class(self):
        if self.action in {'create', 'update', 'partial_update'}:
            return FoodPlaceWriteSerializer
        if self.action == 'retrieve':
            return FoodPlaceDetailSerializer
        if self.action == 'menu_items':
            return MenuItemSerializer
        return FoodPlaceListSerializer

    def get_throttles(self):
        # Only the import endpoints fan out to Overpass, so they get the tighter
        # budget on top of the normal ones. The scope has to be passed in: a bare
        # ScopedRateThrottle() has `scope = None` and would silently throttle
        # nothing at all.
        throttles = super().get_throttles()
        if self.action in {'import_area', 'search_import'}:
            throttles.append(ScopedThrottle(scope=self.import_scope))
        return throttles

    def get_queryset(self):
        qs = FoodPlace.objects.filter(is_active=True)
        if _bool_param(self.request.query_params, 'mine'):
            if self.request.user.is_authenticated:
                qs = qs.filter(owner=self.request.user)
            else:
                qs = qs.none()
        return qs

    # ── Write permissions ──────────────────────────────────────────
    def perform_create(self, serializer):
        # owner is always the logged-in user, never whatever the client sent.
        serializer.save(owner=self.request.user, is_verified=False)

    def perform_update(self, serializer):
        serializer.save()

    def list(self, request, *args, **kwargs):
        p = request.query_params

        user_lat = _float_param(p, 'lat')
        user_lon = _float_param(p, 'lon')
        has_location = (
            user_lat is not None
            and user_lon is not None
            and -90 <= user_lat <= 90
            and -180 <= user_lon <= 180
        )

        category        = (p.get('category') or 'all').lower()
        cuisine         = (p.get('cuisine') or '').lower()
        search          = (p.get('search') or '').strip()
        location_search = (p.get('location_search') or '').strip()
        is_veg          = (p.get('is_veg') or '').lower()
        min_rating      = p.get('min_rating', '')
        delivery        = (p.get('delivery') or '').lower()
        price_level     = p.get('price_level', '')
        sort_by         = p.get('sort_by') or ('distance' if has_location else 'rating')
        radius_km       = _int_param(p, 'radius', 10 if has_location else 400, minimum=1, maximum=400)
        page            = _int_param(p, 'page', 1, minimum=1)
        page_size       = _int_param(p, 'page_size', 20, minimum=1, maximum=100)

        # `mine=true` has to be honoured here too: list() overrides the default
        # implementation, so get_queryset() never runs and MyFoodPlacesPage would
        # otherwise receive the whole public catalogue.
        mine = _bool_param(p, 'mine')
        qs = FoodPlace.objects.filter(is_active=True)
        if mine:
            qs = qs.filter(owner=request.user) if request.user.is_authenticated else qs.none()

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
            # "Non-veg" has to include rows whose diet is unknown (NULL).
            # `is_veg=False` alone dropped every OSM import that simply has no
            # diet tag, so the filter returned almost nothing.
            qs = qs.filter(Q(is_veg=False) | Q(is_veg__isnull=True))
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

        # Bound the query in the database before doing any Python distance maths.
        # `list(qs)` on the whole table on every request was the other half of
        # the slow-response problem.
        if has_location:
            lat_pad = (radius_km + 5) / 111.0
            lon_pad = (radius_km + 5) / (111.0 * max(math.cos(math.radians(user_lat)), 0.01))
            qs = qs.filter(
                latitude__gte=user_lat - lat_pad, latitude__lte=user_lat + lat_pad,
                longitude__gte=user_lon - lon_pad, longitude__lte=user_lon + lon_pad,
            )

        candidates = list(qs[:500])

        if has_location:
            nearby = []
            for fp in candidates:
                distance = _haversine(user_lat, user_lon, fp.latitude, fp.longitude)
                if distance <= radius_km:
                    fp._distance_km = distance
                    nearby.append(fp)
            if sort_by == 'distance':
                nearby.sort(key=lambda x: x._distance_km)
            elif sort_by == 'rating':
                nearby.sort(key=lambda x: (-x.rating, x._distance_km))
            else:
                nearby.sort(key=lambda x: x.name)
            all_results = nearby
        else:
            if sort_by == 'name':
                candidates.sort(key=lambda x: x.name)
            elif sort_by == 'rating':
                candidates.sort(key=lambda x: -x.rating)
            else:
                random.shuffle(candidates)
            all_results = candidates

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
            # Lets the client offer "import this area" instead of looking broken
            # when a small town has almost nothing in the database yet.
            'sparse':       total < 5,
            'results':      serializer.data,
        })

    def retrieve(self, request, pk=None):
        obj = self.get_object()
        return Response(FoodPlaceDetailSerializer(obj, context={'request': request}).data)

    # ── Owner: menu items ─────────────────────────────────────────
    @action(detail=True, methods=['get', 'post'], url_path='menu-items')
    def menu_items(self, request, pk=None):
        """GET/POST /api/food/{id}/menu-items/ — the menu on the detail page."""
        place = self.get_object()

        if request.method == 'GET':
            items = place.menu_items.all()
            return Response(MenuItemSerializer(items, many=True).data)

        # get_object() runs the object permission above, so an OSM row (owner
        # NULL) or another user's outlet is already rejected with 403 here.
        self.check_object_permissions(request, place)
        serializer = MenuItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(food_place=place)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='menu-items/(?P<item_id>[0-9]+)')
    def delete_menu_item(self, request, pk=None, item_id=None):
        place = self.get_object()
        self.check_object_permissions(request, place)
        # Scoped to the place as well, so an item id from a different outlet
        # cannot be deleted through this path.
        item = MenuItem.objects.filter(pk=item_id, food_place=place).first()
        if not item:
            return Response({'error': 'Menu item not found'}, status=status.HTTP_404_NOT_FOUND)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── Reads that only touch the database ────────────────────────
    @action(detail=False, methods=['get'], url_path='nearby')
    def nearby(self, request):
        lat = _float_param(request.query_params, 'lat')
        lon = _float_param(request.query_params, 'lon')
        if lat is None or lon is None:
            return Response({'error': 'lat and lon are required'}, status=status.HTTP_400_BAD_REQUEST)

        radius   = _int_param(request.query_params, 'radius', 10, minimum=1, maximum=100)
        category = (request.query_params.get('category') or 'all').lower()

        qs = self.get_queryset()
        if category != 'all':
            qs = qs.filter(category=category)

        lat_pad = (radius + 5) / 111.0
        lon_pad = (radius + 5) / (111.0 * max(math.cos(math.radians(lat)), 0.01))
        qs = qs.filter(
            latitude__gte=lat - lat_pad, latitude__lte=lat + lat_pad,
            longitude__gte=lon - lon_pad, longitude__lte=lon + lon_pad,
        )

        nearby = []
        for fp in qs:
            distance = _haversine(lat, lon, fp.latitude, fp.longitude)
            if distance <= radius:
                fp._distance_km = distance
                nearby.append(fp)
        nearby.sort(key=lambda x: x._distance_km)

        serializer = FoodPlaceListSerializer(nearby, many=True, context={'request': request})
        return Response({
            'total':     len(nearby),
            'radius_km': radius,
            # Thin coverage used to trigger a blocking Overpass fetch here. The
            # client is told instead, and can start an import deliberately.
            'sparse':    len(nearby) < 5,
            'results':   serializer.data,
        })

    @action(detail=False, methods=['get'], url_path='categories')
    def categories(self, request):
        total = FoodPlace.objects.filter(is_active=True).count()
        result = [{
            'key': 'all', 'label': 'All', 'icon': CATEGORY_ICONS['all'], 'count': total,
        }]
        for cat in FoodCategory.choices:
            key = cat[0]
            result.append({
                'key':   key,
                'label': cat[1],
                'icon':  CATEGORY_ICONS.get(key, '🍴'),
                'count': FoodPlace.objects.filter(is_active=True, category=key).count(),
            })
        return Response(result)

    @action(detail=False, methods=['get'], url_path='cuisines')
    def cuisines(self, request):
        return Response([{'key': c[0], 'label': c[1]} for c in CuisineType.choices])

    @action(detail=False, methods=['get'], url_path='random')
    def random_food(self, request):
        count    = _int_param(request.query_params, 'count', 20, minimum=1, maximum=100)
        category = (request.query_params.get('category') or 'all').lower()

        qs = self.get_queryset()
        if category != 'all':
            qs = qs.filter(category=category)

        pks     = list(qs.values_list('pk', flat=True))
        sample  = random.sample(pks, min(count, len(pks)))
        results = list(FoodPlace.objects.filter(pk__in=sample))
        random.shuffle(results)
        return Response({
            'total':   len(results),
            'sparse':  len(pks) < 20,
            'results': FoodPlaceListSerializer(results, many=True, context={'request': request}).data,
        })

    # ── Explicit, throttled OSM import ───────────────────────────
    @action(detail=False, methods=['post'], url_path='import-area')
    def import_area(self, request):
        """
        POST /api/food/import-area/  { lat, lon, radius }

        Overpass is slow and rate limited, so it must not run inside a browse
        request. This is the deliberate, throttled entry point, and the work
        happens on a worker when Celery is available.
        """
        lat    = _float_param(request.data, 'lat')
        lon    = _float_param(request.data, 'lon')
        radius = _int_param(request.data, 'radius', 8, minimum=1, maximum=25)

        if lat is None or lon is None:
            return Response({'error': 'lat and lon are required'}, status=status.HTTP_400_BAD_REQUEST)

        key = f"food:import:{lat:.2f},{lon:.2f}:{radius}"
        if _is_locked(key):
            return Response({
                'status': 'pending',
                'detail': 'An import for this area is already running. Try again shortly.',
            }, status=status.HTTP_202_ACCEPTED)

        found = fetch_food_near(lat, lon, radius_km=radius)
        saved = _save_food(found)
        # The lock is released on both paths. Leaving it set blocked the area for
        # the full TTL even when the import had already finished.
        _unlock(key)
        return Response({'status': 'done', 'fetched': len(found), 'saved': saved})

    @action(detail=False, methods=['get', 'post'], url_path='import-city')
    def search_import(self, request):
        """
        /api/food/import-city/?q=Jaipur — geocode, then import that area.

        POST as well as GET because this writes rows, and the frontend sends the
        city name in the body of a POST. The name is accepted from either place.
        """
        query = (
            request.data.get('q') if request.method == 'POST' else None
        ) or request.query_params.get('q') or ''
        query = str(query).strip()
        if not query:
            return Response({'error': 'q is required'}, status=status.HTTP_400_BAD_REQUEST)

        key = f"food:import:city:{query.lower()}"
        if _is_locked(key):
            return Response({
                'status': 'pending',
                'detail': 'An import for this city is already running. Try again shortly.',
            }, status=status.HTTP_202_ACCEPTED)

        found = search_food_by_location(query)
        saved = _save_food(found, default_city=query)
        _unlock(key)
        return Response({'status': 'done', 'query': query, 'fetched': len(found), 'saved': saved})