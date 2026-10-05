"""
OpenStreetMap / Overpass API — Food Places Scraper
Fetches restaurants, street food, cafes, dhabas etc.
"""
import requests
import logging
import time
import random

logger = logging.getLogger(__name__)
#: Overpass mirrors, tried in order. The main endpoint returns 504 fairly often
#: under load, and a single failed request meant a whole town's import came back
#: empty. These are all the same data on separate infrastructure.
OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)

#: How long to wait on one mirror before moving to the next.
OVERPASS_TIMEOUT = 45

# ── OSM tag → our category ────────────────────────────────────────────────────
CATEGORY_MAP = {
    'restaurant': 'restaurant',
    'fast_food':  'fast_food',
    'cafe':       'cafe',
    'food_court': 'restaurant',
    'bar':        'other',
    'pub':        'other',
    'ice_cream':  'juice_bar',
    'bakery':     'bakery',
    'confectionery': 'sweet_shop',
    'juice_bar':  'juice_bar',
    'sweet':      'sweet_shop',
    'coffee':     'cafe',
    'tea':        'cafe',
    'pizza':      'restaurant',
    'chocolate':  'sweet_shop',
    'butcher':    'other',
    'street_vendor': 'street_food',
    'food_kiosk': 'street_food',
    'dhaba':      'dhaba',
    'sweet_shop': 'sweet_shop',
    'snack_bar':  'street_food',
    'bbq':        'dhaba',
    'biergarten': 'other',
    'motel':      'restaurant',
    'deli':       'restaurant',
    'diner':      'restaurant',
}

# ── Cuisine tag → our cuisine ─────────────────────────────────────────────────
CUISINE_MAP = {
    'indian':        'multi',
    'north_indian':  'north_indian',
    'south_indian':  'south_indian',
    'chinese':       'chinese',
    'mughlai':       'mughlai',
    'punjabi':       'punjabi',
    'rajasthani':    'rajasthani',
    'bengali':       'bengali',
    'gujarati':      'gujarati',
    'continental':   'continental',
    'italian':       'italian',
    'pizza':         'italian',
    # There is no "fast_food" *cuisine*. Writing it into a choices field produced
    # rows the cuisine filter could never match, because the UI only offers the
    # values in CuisineType.
    'burger':        'multi',
    'sandwich':      'multi',
    'street_food':   'street',
    'regional':      'multi',
    'multi':         'multi',
    # Also not a cuisine. It is a category, and the tag shows up on plenty of
    # outlets, so it is normalised rather than falling through to 'other'.
    'fast_food':     'multi',
}

# ── Random Indian cities for fallback ────────────────────────────────────────
FOOD_CITIES = [
    {"name": "Delhi",     "lat": 28.6139, "lon": 77.2090},
    {"name": "Mumbai",    "lat": 19.0760, "lon": 72.8777},
    {"name": "Kolkata",   "lat": 22.5726, "lon": 88.3639},
    {"name": "Chennai",   "lat": 13.0827, "lon": 80.2707},
    {"name": "Jaipur",    "lat": 26.9124, "lon": 75.7873},
    {"name": "Hyderabad", "lat": 17.3850, "lon": 78.4867},
    {"name": "Pune",      "lat": 18.5204, "lon": 73.8567},
    {"name": "Amritsar",  "lat": 31.6340, "lon": 74.8723},
    {"name": "Varanasi",  "lat": 25.3176, "lon": 82.9739},
    {"name": "Ahmedabad", "lat": 23.0225, "lon": 72.5714},
    {"name": "Lucknow",   "lat": 26.8467, "lon": 80.9462},
    {"name": "Indore",    "lat": 22.7196, "lon": 75.8577},
]


def _determine_category(tags: dict) -> str:
    amenity  = tags.get('amenity', '')
    shop     = tags.get('shop', '')
    cuisine  = tags.get('cuisine', '').lower()
    name     = tags.get('name', '').lower()

    # Check shop tag first. Any shop value the map knows about is categorised by it,
    # not only a hand-picked few, so `shop=coffee` becomes a cafe.
    if shop in CATEGORY_MAP:
        return CATEGORY_MAP[shop]

    # Check amenity
    cat = CATEGORY_MAP.get(amenity, '')
    if cat:
        return cat

    # Heuristic from name/cuisine
    if any(w in name for w in ['dhaba', 'dhabha']):
        return 'dhaba'
    if any(w in name for w in ['juice', 'lassi', 'sharbat']):
        return 'juice_bar'
    if any(w in name for w in ['sweet', 'mithai', 'halwai', 'ladoo', 'barfi']):
        return 'sweet_shop'
    if any(w in name for w in ['chaat', 'pani puri', 'bhel', 'vada', 'pav']):
        return 'street_food'
    if any(w in name for w in ['cafe', 'coffee', 'tea stall', 'chai']):
        return 'cafe'
    if amenity == 'fast_food':
        return 'fast_food'

    return 'restaurant'


def _determine_cuisine(tags: dict) -> str:
    cuisine_tag = tags.get('cuisine', '').lower().split(';')[0].strip()
    name        = tags.get('name', '').lower()

    mapped = CUISINE_MAP.get(cuisine_tag, '')
    if mapped:
        return mapped

    # Heuristic from name
    if any(w in name for w in ['punjabi', 'dhaba']):   return 'punjabi'
    if any(w in name for w in ['south', 'udupi', 'idli', 'dosa']): return 'south_indian'
    if any(w in name for w in ['chinese', 'noodle', 'chowmein']): return 'chinese'
    if any(w in name for w in ['mughal', 'awadhi', 'biryani']): return 'mughlai'
    if any(w in name for w in ['rajasthani', 'dal baati']): return 'rajasthani'
    if any(w in name for w in ['bengali', 'mishti']): return 'bengali'
    if any(w in name for w in ['gujarati', 'thali']): return 'gujarati'
    if any(w in name for w in ['italian', 'pizza', 'pasta']): return 'italian'
    if any(w in name for w in ['burger', 'sandwich', 'wrap']): return 'multi'

    return 'other'


def _parse_price_level(tags: dict) -> int:
    price_range = tags.get('price_range', tags.get('level', ''))
    if '₹₹₹₹' in price_range or price_range == '4': return 4
    if '₹₹₹'  in price_range or price_range == '3': return 3
    if '₹₹'   in price_range or price_range == '2': return 2
    return 1


#: Every tag key OSM uses to carry a photograph. Cafes in particular tend to
#: use `image:url` or `contact:image` rather than plain `image`, and reading only
#: `image` was why so many cafe cards came back blank.
IMAGE_TAGS = (
    'image',
    'image:url',
    'image:link',
    'image:photo',
    'contact:image',
    'contact:photo',
    'wikimedia',
    'wikidata',
    'logo',
    # Numbered variants. A cafe that bothers to add a photo usually adds several
    # and the first slot is not always the storefront, so the whole family is
    # read rather than just `image`.
    'image:1', 'image:2', 'image:3', 'image:4',
)

CREDIT_TAGS = ('image:credit', 'attribution', 'license', 'contact:attribution')


def _parse_image(tags: dict) -> str:
    """First usable photograph URL from the OSM tags, if any."""
    for key in IMAGE_TAGS:
        value = (tags.get(key) or '').strip()
        if not value:
            continue
        # A bare filename is not a URL; skip it rather than storing something the
        # browser will try to fetch relative to the API host.
        if not value.lower().startswith(('http://', 'https://')):
            continue
        return value
    return ''


def _parse_image_credit(tags: dict) -> str:
    for key in CREDIT_TAGS:
        value = (tags.get(key) or '').strip()
        if value:
            return value[:300]
    return ''


def _parse_element(element: dict):
    tags = element.get('tags', {})
    name = (tags.get('name') or tags.get('name:en') or
            tags.get('official_name') or tags.get('alt_name'))
    if not name:
        return None

    amenity = tags.get('amenity', '')
    shop    = tags.get('shop', '')

    # Only food-related
    food_amenities = {'restaurant','fast_food','cafe','bar','pub','food_court',
                      'ice_cream','juice_bar','street_vendor','food_kiosk','snack_bar',
                      'bbq','biergarten','motel','confectionery','deli','diner'}
    food_shops     = {'bakery','confectionery','ice_cream','sweet','coffee','tea',
                     'pizza','juice_bar','chocolate','deli'}
    if amenity not in food_amenities and shop not in food_shops:
        # Allow if name has food keywords
        food_keywords = ['dhaba','restaurant','cafe','food','biryani','chaat',
                         'sweet','mithai','juice','lassi','halwai','snack']
        if not any(kw in name.lower() for kw in food_keywords):
            return None

    # Coordinates. A way/relation carries them in `center`, a node at the top
    # level. Compared against None rather than for truthiness: 0.0 is a legal
    # coordinate and `if not lat` silently threw those places away.
    if element['type'] == 'node':
        lat, lon = element.get('lat'), element.get('lon')
    else:
        center = element.get('center', {})
        lat, lon = center.get('lat'), center.get('lon')

    if lat is None or lon is None:
        return None

    # Parse features
    diet_veg = tags.get('diet:vegetarian', '')
    diet_vegan = tags.get('diet:vegan', '')
    is_veg = None
    if diet_veg == 'only' or diet_vegan == 'only':
        is_veg = True
    elif diet_veg == 'no':
        is_veg = False

    opening_hours = {}
    if tags.get('opening_hours'):
        opening_hours = {'raw': tags['opening_hours']}

    return {
        'osm_id':   f"{element['type']}/{element['id']}",
        'osm_type': element['type'],
        'name':     name.strip(),
        'category': _determine_category(tags),
        'cuisine':  _determine_cuisine(tags),
        'latitude': lat,
        'longitude': lon,
        'address':  ', '.join(filter(None,[
            tags.get('addr:housenumber',''),
            tags.get('addr:street',''),
            tags.get('addr:suburb',''),
        ])),
        'city':     tags.get('addr:city', tags.get('is_in:city', '')),
        'state':    tags.get('addr:state', tags.get('is_in:state', '')),
        'country':  tags.get('addr:country', 'IN'),
        'description': tags.get('description', ''),
        'website':  tags.get('website', tags.get('url', tags.get('contact:website', ''))),
        'phone':    tags.get('phone', tags.get('contact:phone', '')),
        'image_url': _parse_image(tags),
        'image_credit': _parse_image_credit(tags),
        'opening_hours': opening_hours,
        'price_level': _parse_price_level(tags),
        'is_veg':   is_veg,
        'takeaway': tags.get('takeaway', '') in ('yes', 'only'),
        'outdoor_seating': tags.get('outdoor_seating', '') == 'yes',
        'home_delivery': tags.get('delivery', '') == 'yes',
        'rating':   0.0,
        'review_count': 0,
    }


def fetch_food_near(lat: float, lon: float, radius_km: int = 10) -> list:
    """Fetch food places from Overpass API near given coordinates."""
    radius_m = radius_km * 1000

    query = f"""
[out:json][timeout:60];
(
  node["amenity"~"^(restaurant|fast_food|cafe|bar|pub|food_court|ice_cream|juice_bar|snack_bar|bbq|biergarten|motel|confectionery|diner|deli)$"](around:{radius_m},{lat},{lon});
  node["amenity"="street_vendor"](around:{radius_m},{lat},{lon});
  node["shop"~"^(bakery|confectionery|ice_cream|sweet|coffee|tea|pizza|juice_bar|chocolate|deli)$"](around:{radius_m},{lat},{lon});
  way["amenity"~"^(restaurant|fast_food|cafe|food_court|diner|deli)$"](around:{radius_m},{lat},{lon});
  way["shop"~"^(bakery|confectionery|coffee|tea|pizza)$"](around:{radius_m},{lat},{lon});
);
out center tags;
"""
    # The query above deliberately has no bare `node["cuisine"]` clause. That
    # matches *any* node carrying a cuisine tag inside the radius, including ones
    # that are not places at all, and it was the single biggest cause of the
    # Overpass timeouts this endpoint hit. The amenity/shop filters already cover
    # everything that can be categorised.
    try:
        data = _overpass_json(query)
        if data is None:
            return []

        # Dedupe on identity, not on the name. Keying on `name` collapsed every
        # branch of a chain in a city into one row, so a search for "Domino's
        # Pizza" in Delhi returned a single outlet.
        results, seen = [], set()
        for element in data.get('elements', []):
            parsed = _parse_element(element)
            if parsed and parsed['osm_id'] not in seen:
                seen.add(parsed['osm_id'])
                results.append(parsed)

        logger.info("Fetched %d food places near (%s,%s)", len(results), lat, lon)
        return results

    except Exception as e:
        logger.error(f"Food fetch error: {e}")
        return []


def _overpass_json(query: str) -> dict | None:
    """
    Run an Overpass query, trying each mirror in turn.

    The public endpoint returns 504 regularly under load, and giving up on the
    first failure meant a whole town's import came back empty with no clue why.
    Returns the decoded payload, or ``None`` when every mirror failed.
    """
    for url in OVERPASS_URLS:
        try:
            response = requests.post(
                url,
                data={'data': query},
                timeout=OVERPASS_TIMEOUT,
                headers={'User-Agent': 'Yatrip/1.0 (travel app)'},
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.warning("Overpass timeout at %s, trying next mirror", url)
        except requests.RequestException as exc:
            logger.warning("Overpass request failed at %s: %s", url, exc)
        except ValueError as exc:
            # A 504 often arrives with an HTML error page rather than JSON.
            logger.warning("Overpass returned non-JSON at %s: %s", url, exc)

    logger.error("All Overpass mirrors failed")
    return None


# ── Fallback coverage when the caller has no location ─────────────────────────
# Deliberately not the 12 metros any more. A browse with no location used to pull
# only from Delhi/Mumbai/Jaipur and friends, so a traveller in a small town saw an
# empty page no matter what they asked for. Coverage now comes from the shared
# `core.Settlement` table, which is the whole point of having it.
def fetch_random_food(count: int = 80) -> list:
    """Fetch food from a spread of settlements when the user has no location."""
    cities = _pick_settlement_centres(min(4, 12))
    all_places = []
    for city in cities:
        places = fetch_food_near(city['lat'], city['lon'], radius_km=city.get('radius_km', 8))
        for p in places:
            if not p.get('city'):
                p['city'] = city['name']
        all_places.extend(places)
        time.sleep(1)
    random.shuffle(all_places)
    return all_places[:count]


def _pick_settlement_centres(limit: int) -> list[dict]:
    """
    Seed points spread across settlements, largest first then randomised.

    Small settlements are what were missing, so the pool is weighted towards them
    rather than being another list of metropolitan centres. Falls back to the
    built-in list when the settlement table has not been ingested yet, so a fresh
    checkout still returns something.
    """
    try:
        from core.models import Settlement
    except Exception:
        return list(FOOD_CITIES)[:limit]

    try:
        # Half the budget from the biggest places (they have the most cafes),
        # half from small ones, so breadth does not come entirely at the cost of
        # depth.
        half = max(1, limit // 2)
        # `pk` has to be in .values() for the exclude() below. It was missing, so
        # s['pk'] raised a KeyError, the whole lookup fell back to the built-in
        # city list, and the small-settlement weighting never actually applied.
        fields = ('pk', 'name', 'latitude', 'longitude', 'population')
        big = list(
            Settlement.objects.filter(population__isnull=False)
            .exclude(latitude__isnull=True)
            .exclude(longitude__isnull=True)
            .order_by('-population')[:half]
            .values(*fields)
        )
        rest = list(
            Settlement.objects.exclude(pk__in=[s['pk'] for s in big])
            .exclude(latitude__isnull=True)
            .exclude(longitude__isnull=True)
            .order_by('?')[: limit - len(big)]
            .values(*fields)
        )
        chosen = big + rest
    except Exception as exc:
        logger.warning("settlement lookup failed, using built-in cities: %s", exc)
        return list(FOOD_CITIES)[:limit]

    if not chosen:
        return list(FOOD_CITIES)[:limit]

    return [
        {
            'name': row['name'],
            'lat':  row['latitude'],
            'lon':  row['longitude'],
            # A small town's cafes are all within a couple of kilometres, so a
            # wide radius costs little and is the only way to get any coverage.
            'radius_km': 12 if (row.get('population') or 0) < 100_000 else 8,
        }
        for row in chosen
    ]


# ── Geocoding ─────────────────────────────────────────────────────────────────
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

#: Nominatim usage policy: at most one request per second, and a real contact in
#: the User-Agent. Bulk requests without this get the endpoint blocked.
_GEOCODE_HEADERS = {"User-Agent": "Yatrip/1.0 (travel app)"}


def geocode_place(location_name: str) -> dict | None:
    """
    Resolve a place name to coordinates.

    Restricted to India first and only widened if that finds nothing, because an
    unbounded search happily resolves an Indian town name to a street of the same
    name somewhere else entirely.
    """
    if not (location_name or "").strip():
        return None

    base = {'q': location_name, 'format': 'json', 'limit': 1}
    attempts = [dict(base, countrycodes='in'), base]

    for params in attempts:
        try:
            r = requests.get(NOMINATIM_URL, params=params, headers=_GEOCODE_HEADERS, timeout=10)
            r.raise_for_status()
            data = r.json() or []
        except Exception as e:
            logger.warning("geocode failed for %r: %s", location_name, e)
            continue

        if not data:
            continue

        hit = data[0]
        try:
            lat = float(hit['lat'])
            lon = float(hit['lon'])
        except (KeyError, TypeError, ValueError):
            continue

        # `addresstype` / `class` distinguish a town from a city, which decides
        # how far out to search for food.
        addresstype = (hit.get('addresstype') or hit.get('class') or '').lower()
        name = (
            hit.get('addresstype') and location_name
            or hit.get('name')
            or location_name
        )
        return {
            'lat':          lat,
            'lon':          lon,
            'display_name': hit.get('display_name', location_name),
            'city':          hit.get('name') or location_name,
            'state':         (hit.get('address', {}) or {}).get('state', ''),
            'addresstype':   addresstype,
        }
    return None


def radius_for_place(addresstype: str = '') -> int:
    """
    Search radius appropriate to how big a place is.

    A village or hamlet has every cafe within a few kilometres, and asking for
    only 10 km around a tiny settlement was fine -- the real problem was the fixed
    8 km used for the seeded fallback. Small places get a wider net so a single
    cafe is still findable.
    """
    if addresstype in {'village', 'hamlet', 'isolated_dwelling', 'farm'}:
        return 20
    if addresstype in {'town', 'suburb', 'quarter', 'neighbourhood'}:
        return 15
    return 10


def search_food_by_location(location_name: str, radius_km: int | None = None) -> list:
    """
    Geocode a location name of any size, then fetch food near it.

    This is the path that makes small locations work: the name is geocoded rather
    than matched against a hard-coded city list, so a village or a small town
    resolves like a metropolis does.
    """
    place = geocode_place(location_name)
    if not place:
        return []

    radius = radius_km or radius_for_place(place.get('addresstype', ''))
    results = fetch_food_near(place['lat'], place['lon'], radius_km=radius)

    # OSM rarely carries addr:city on a cafe, and in a small town there is no
    # `city` tag at all. Stamping the resolved place name on is what lets the
    # list endpoint's city filter find these rows afterwards.
    for row in results:
        if not row.get('city'):
            row['city'] = place['city']
        if not row.get('state') and place.get('state'):
            row['state'] = place['state']
    return results