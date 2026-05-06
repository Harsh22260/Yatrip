"""
OpenStreetMap / Overpass API service
Fetches real attraction data from OSM for free
"""

import requests
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# OSM tag → our category mapping
CATEGORY_OSM_TAGS = {
    'monument': [
        'historic=monument',
        'historic=memorial',
        'historic=castle',
        'historic=fort',
        'historic=ruins',
        'historic=archaeological_site',
        'historic=city_gate',
        'historic=palace',
    ],
    'temple': [
        'amenity=place_of_worship',
        'religion=hindu',
        'religion=buddhist',
        'religion=jain',
        'religion=sikh',
        'historic=temple',
    ],
    'park': [
        'leisure=park',
        'leisure=garden',
        'leisure=nature_reserve',
        'leisure=playground',
        'leisure=recreation_ground',
    ],
    'museum': [
        'tourism=museum',
        'tourism=gallery',
        'tourism=artwork',
    ],
    'nature': [
        'natural=peak',
        'natural=waterfall',
        'natural=beach',
        'natural=cliff',
        'natural=cave_entrance',
        'natural=hot_spring',
        'waterway=waterfall',
        'tourism=viewpoint',
    ],
    'other': [
        'tourism=attraction',
        'tourism=theme_park',
        'tourism=zoo',
        'tourism=aquarium',
        'amenity=arts_centre',
        'tourism=yes',
    ],
}

# All tourism/attraction tags in one query
ALL_TOURISM_TAGS = """
  node["tourism"~"attraction|museum|gallery|viewpoint|theme_park|zoo|aquarium"](around:{radius},{lat},{lon});
  node["historic"~"monument|memorial|castle|fort|ruins|archaeological_site|palace|temple"](around:{radius},{lat},{lon});
  node["leisure"~"park|garden|nature_reserve"](around:{radius},{lat},{lon});
  node["amenity"="place_of_worship"]["religion"~"hindu|buddhist|jain|sikh"](around:{radius},{lat},{lon});
  node["natural"~"peak|waterfall|beach|cliff|cave_entrance"](around:{radius},{lat},{lon});
  node["amenity"="arts_centre"](around:{radius},{lat},{lon});
  way["tourism"~"attraction|museum|gallery|viewpoint|theme_park|zoo"](around:{radius},{lat},{lon});
  way["historic"~"monument|memorial|castle|fort|ruins|palace"](around:{radius},{lat},{lon});
  way["leisure"~"park|garden|nature_reserve"](around:{radius},{lat},{lon});
"""

# Random cities to fetch when no user location
RANDOM_CITIES = [
    {"name": "Delhi", "lat": 28.6139, "lon": 77.2090},
    {"name": "Mumbai", "lat": 19.0760, "lon": 72.8777},
    {"name": "Jaipur", "lat": 26.9124, "lon": 75.7873},
    {"name": "Agra", "lat": 27.1767, "lon": 78.0081},
    {"name": "Varanasi", "lat": 25.3176, "lon": 82.9739},
    {"name": "Goa", "lat": 15.2993, "lon": 74.1240},
    {"name": "Kerala", "lat": 10.8505, "lon": 76.2711},
    {"name": "Kolkata", "lat": 22.5726, "lon": 88.3639},
    {"name": "Chennai", "lat": 13.0827, "lon": 80.2707},
    {"name": "Hyderabad", "lat": 17.3850, "lon": 78.4867},
    {"name": "Udaipur", "lat": 24.5854, "lon": 73.7125},
    {"name": "Mysore", "lat": 12.2958, "lon": 76.6394},
    {"name": "Amritsar", "lat": 31.6340, "lon": 74.8723},
    {"name": "Rishikesh", "lat": 30.0869, "lon": 78.2676},
    {"name": "Hampi", "lat": 15.3350, "lon": 76.4600},
]


def _determine_category(tags: dict) -> str:
    """Determine attraction category from OSM tags"""
    tourism = tags.get('tourism', '')
    historic = tags.get('historic', '')
    leisure = tags.get('leisure', '')
    natural = tags.get('natural', '')
    amenity = tags.get('amenity', '')
    religion = tags.get('religion', '')

    if historic in ['monument', 'memorial', 'castle', 'fort', 'ruins', 'archaeological_site', 'palace', 'city_gate']:
        return 'monument'
    if amenity == 'place_of_worship' or religion in ['hindu', 'buddhist', 'jain', 'sikh'] or historic == 'temple':
        return 'temple'
    if tourism == 'museum' or tourism == 'gallery':
        return 'museum'
    if leisure in ['park', 'garden', 'nature_reserve']:
        return 'park'
    if natural in ['peak', 'waterfall', 'beach', 'cliff', 'cave_entrance'] or tourism == 'viewpoint':
        return 'nature'
    return 'other'


def _extract_name(tags: dict, element_type: str, element_id: int) -> Optional[str]:
    """Extract best available name from OSM tags"""
    return (
        tags.get('name') or
        tags.get('name:en') or
        tags.get('official_name') or
        tags.get('alt_name') or
        None
    )


def _parse_element(element: dict) -> Optional[dict]:
    """Parse a single OSM element into attraction dict"""
    tags = element.get('tags', {})
    name = _extract_name(tags, element.get('type'), element.get('id'))

    if not name:
        return None

    # Get coordinates
    if element['type'] == 'node':
        lat = element.get('lat')
        lon = element.get('lon')
    else:
        # way/relation - use center
        center = element.get('center', {})
        lat = center.get('lat')
        lon = center.get('lon')

    if not lat or not lon:
        return None

    # Build opening hours
    opening_hours = {}
    if tags.get('opening_hours'):
        opening_hours = {'raw': tags.get('opening_hours')}

    # Entry fee
    is_free = True
    entry_fee = None
    fee_tag = tags.get('fee', '').lower()
    charge_tag = tags.get('charge', '')
    if fee_tag == 'yes' or charge_tag:
        is_free = False
        # Try to parse fee
        try:
            fee_str = charge_tag.replace('INR', '').replace('₹', '').strip().split(';')[0].strip()
            entry_fee = float(fee_str) if fee_str else None
        except (ValueError, AttributeError):
            entry_fee = None

    return {
        'osm_id': f"{element['type']}/{element['id']}",
        'osm_type': element['type'],
        'name': name.strip(),
        'category': _determine_category(tags),
        'latitude': lat,
        'longitude': lon,
        'address': ', '.join(filter(None, [
            tags.get('addr:housenumber', ''),
            tags.get('addr:street', ''),
            tags.get('addr:suburb', ''),
        ])),
        'city': tags.get('addr:city', tags.get('is_in:city', '')),
        'state': tags.get('addr:state', tags.get('is_in:state', '')),
        'country': tags.get('addr:country', 'IN'),
        'description': tags.get('description', tags.get('wikipedia', '')),
        'website': tags.get('website', tags.get('url', '')),
        'phone': tags.get('phone', tags.get('contact:phone', '')),
        'image_url': tags.get('image', tags.get('wikimedia_commons', '')),
        'opening_hours': opening_hours,
        'is_free': is_free,
        'entry_fee': entry_fee,
        'rating': 0.0,
        'review_count': 0,
    }


def fetch_attractions_near(lat: float, lon: float, radius_km: int = 50) -> list:
    """
    Fetch attractions from Overpass API near given coordinates.
    radius_km: search radius in kilometers
    """
    radius_m = radius_km * 1000

    query = f"""
[out:json][timeout:60];
(
  node["tourism"~"attraction|museum|gallery|viewpoint|theme_park|zoo|aquarium"](around:{radius_m},{lat},{lon});
  node["historic"~"monument|memorial|castle|fort|ruins|archaeological_site|palace"](around:{radius_m},{lat},{lon});
  node["leisure"~"park|garden|nature_reserve"](around:{radius_m},{lat},{lon});
  node["amenity"="place_of_worship"]["religion"~"hindu|buddhist|jain|sikh"](around:{radius_m},{lat},{lon});
  node["natural"~"peak|waterfall|beach|cliff|cave_entrance"](around:{radius_m},{lat},{lon});
  node["tourism"="viewpoint"](around:{radius_m},{lat},{lon});
  node["amenity"="arts_centre"](around:{radius_m},{lat},{lon});
  way["tourism"~"attraction|museum|gallery|theme_park|zoo"](around:{radius_m},{lat},{lon});
  way["historic"~"monument|memorial|castle|fort|ruins|palace"](around:{radius_m},{lat},{lon});
  way["leisure"~"park|garden|nature_reserve"](around:{radius_m},{lat},{lon});
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

        attractions = []
        seen_names = set()

        for element in data.get('elements', []):
            parsed = _parse_element(element)
            if parsed and parsed['name'] not in seen_names:
                seen_names.add(parsed['name'])
                attractions.append(parsed)

        logger.info(f"Fetched {len(attractions)} attractions near ({lat}, {lon})")
        return attractions

    except requests.exceptions.Timeout:
        logger.error("Overpass API timeout")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Overpass API error: {e}")
        return []
    except Exception as e:
        logger.error(f"Error parsing OSM data: {e}")
        return []


def fetch_random_attractions(count: int = 60) -> list:
    """
    Fetch attractions from random Indian cities when user has no location.
    Returns mix of categories and sizes.
    """
    import random
    cities = random.sample(RANDOM_CITIES, min(4, len(RANDOM_CITIES)))
    all_attractions = []

    for city in cities:
        attractions = fetch_attractions_near(city['lat'], city['lon'], radius_km=30)
        # Assign city name if missing
        for a in attractions:
            if not a.get('city'):
                a['city'] = city['name']
        all_attractions.extend(attractions)
        time.sleep(1)  # Be polite to Overpass API

    # Shuffle and return diverse set
    random.shuffle(all_attractions)
    return all_attractions[:count]


def search_attractions_by_location_name(location_name: str) -> list:
    """Search OSM Nominatim for a location, then fetch attractions near it"""
    try:
        # First geocode the location
        nominatim_url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': location_name,
            'format': 'json',
            'limit': 1,
            'countrycodes': 'in',  # Prioritize India
        }
        headers = {'User-Agent': 'Yatrip/1.0 (travel app)'}

        geo_response = requests.get(nominatim_url, params=params, headers=headers, timeout=10)
        geo_response.raise_for_status()
        geo_data = geo_response.json()

        if not geo_data:
            # Try without country restriction
            params.pop('countrycodes')
            geo_response = requests.get(nominatim_url, params=params, headers=headers, timeout=10)
            geo_data = geo_response.json()

        if geo_data:
            lat = float(geo_data[0]['lat'])
            lon = float(geo_data[0]['lon'])
            return fetch_attractions_near(lat, lon, radius_km=50)

        return []
    except Exception as e:
        logger.error(f"Location search error: {e}")
        return []