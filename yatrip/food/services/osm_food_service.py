"""
OpenStreetMap / Overpass API — Food Places Scraper
Fetches restaurants, street food, cafes, dhabas etc.
"""
import requests
import logging
import time
import random

logger = logging.getLogger(__name__)
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# ── OSM tag → our category ────────────────────────────────────────────────────
CATEGORY_MAP = {
    'restaurant': 'restaurant',
    'fast_food':  'fast_food',
    'cafe':       'cafe',
    'food_court': 'restaurant',
    'bar':        'other',
    'pub':        'other',
    'ice_cream':  'sweet_shop',
    'bakery':     'bakery',
    'confectionery': 'sweet_shop',
    'juice_bar':  'juice_bar',
    'street_vendor': 'street_food',
    'food_kiosk': 'street_food',
    'dhaba':      'dhaba',
    'sweet_shop': 'sweet_shop',
    'snack_bar':  'street_food',
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
    'burger':        'fast_food',
    'sandwich':      'fast_food',
    'street_food':   'street',
    'regional':      'multi',
    'multi':         'multi',
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

    # Check shop tag first
    if shop in ['bakery', 'confectionery', 'ice_cream']:
        return CATEGORY_MAP.get(shop, 'other')

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
    if any(w in name for w in ['burger', 'sandwich', 'wrap']): return 'fast_food'

    return 'other'


def _parse_price_level(tags: dict) -> int:
    price_range = tags.get('price_range', tags.get('level', ''))
    if '₹₹₹₹' in price_range or price_range == '4': return 4
    if '₹₹₹'  in price_range or price_range == '3': return 3
    if '₹₹'   in price_range or price_range == '2': return 2
    return 1


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
                      'ice_cream','juice_bar','street_vendor','food_kiosk','snack_bar'}
    food_shops     = {'bakery','confectionery','ice_cream','sweet'}
    if amenity not in food_amenities and shop not in food_shops:
        # Allow if name has food keywords
        food_keywords = ['dhaba','restaurant','cafe','food','biryani','chaat',
                         'sweet','mithai','juice','lassi','halwai','snack']
        if not any(kw in name.lower() for kw in food_keywords):
            return None

    # Coordinates
    if element['type'] == 'node':
        lat, lon = element.get('lat'), element.get('lon')
    else:
        center = element.get('center', {})
        lat, lon = center.get('lat'), center.get('lon')

    if not lat or not lon:
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
        'website':  tags.get('website', tags.get('url', '')),
        'phone':    tags.get('phone', tags.get('contact:phone', '')),
        'image_url': tags.get('image', ''),
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
  node["amenity"~"restaurant|fast_food|cafe|bar|food_court|ice_cream|juice_bar|snack_bar"](around:{radius_m},{lat},{lon});
  node["amenity"="street_vendor"](around:{radius_m},{lat},{lon});
  node["shop"~"bakery|confectionery|ice_cream|sweet"](around:{radius_m},{lat},{lon});
  node["cuisine"](around:{radius_m},{lat},{lon});
  way["amenity"~"restaurant|fast_food|cafe|food_court"](around:{radius_m},{lat},{lon});
  way["shop"~"bakery|confectionery"](around:{radius_m},{lat},{lon});
);
out center tags;
"""
    try:
        response = requests.post(
            OVERPASS_URL,
            data={'data': query},
            timeout=60,
            headers={'User-Agent': 'Yatrip/1.0 (travel app)'}
        )
        response.raise_for_status()
        data = response.json()

        results, seen = [], set()
        for element in data.get('elements', []):
            parsed = _parse_element(element)
            if parsed and parsed['name'] not in seen:
                seen.add(parsed['name'])
                results.append(parsed)

        logger.info(f"Fetched {len(results)} food places near ({lat},{lon})")
        return results

    except requests.exceptions.Timeout:
        logger.error("Overpass timeout for food fetch")
        return []
    except Exception as e:
        logger.error(f"Food fetch error: {e}")
        return []


def fetch_random_food(count: int = 80) -> list:
    """Fetch food from random Indian cities when user has no location."""
    cities = random.sample(FOOD_CITIES, min(4, len(FOOD_CITIES)))
    all_places = []
    for city in cities:
        places = fetch_food_near(city['lat'], city['lon'], radius_km=8)
        for p in places:
            if not p.get('city'):
                p['city'] = city['name']
        all_places.extend(places)
        time.sleep(1)
    random.shuffle(all_places)
    return all_places[:count]


def search_food_by_location(location_name: str) -> list:
    """Geocode location name, then fetch food near it."""
    try:
        params = {
            'q': location_name, 'format': 'json',
            'limit': 1, 'countrycodes': 'in',
        }
        headers = {'User-Agent': 'Yatrip/1.0'}
        geo = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params=params, headers=headers, timeout=10
        )
        geo.raise_for_status()
        data = geo.json()
        if not data:
            params.pop('countrycodes')
            data = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params=params, headers=headers, timeout=10
            ).json()
        if data:
            return fetch_food_near(float(data[0]['lat']), float(data[0]['lon']), radius_km=10)
        return []
    except Exception as e:
        logger.error(f"Food location search error: {e}")
        return []