"""
Management command to pre-populate attractions from OSM.
Usage:
  python manage.py fetch_attractions                  # fetch all random cities
  python manage.py fetch_attractions --city "Jaipur"  # fetch specific city
  python manage.py fetch_attractions --lat 28.6 --lon 77.2 --radius 50
"""

from django.core.management.base import BaseCommand
from attractions.services.osm_service import (
    fetch_attractions_near,
    fetch_random_attractions,
    RANDOM_CITIES,
)
from attractions.models import Attraction
import time


class Command(BaseCommand):
    help = 'Fetch attractions from OpenStreetMap and populate database'

    def add_arguments(self, parser):
        parser.add_argument('--city', type=str, help='City name to fetch')
        parser.add_argument('--lat', type=float, help='Latitude')
        parser.add_argument('--lon', type=float, help='Longitude')
        parser.add_argument('--radius', type=int, default=30, help='Radius in km')
        parser.add_argument('--all-cities', action='store_true', help='Fetch all preset cities')

    def handle(self, *args, **options):
        saved_total = 0

        if options.get('lat') and options.get('lon'):
            self.stdout.write(f"Fetching near ({options['lat']}, {options['lon']})...")
            data = fetch_attractions_near(
                options['lat'], options['lon'],
                radius_km=options['radius']
            )
            saved_total += self._save(data)

        elif options.get('city'):
            from attractions.services.osm_service import search_attractions_by_location_name
            self.stdout.write(f"Fetching for city: {options['city']}...")
            data = search_attractions_by_location_name(options['city'])
            saved_total += self._save(data, default_city=options['city'])

        elif options.get('all_cities'):
            for city in RANDOM_CITIES:
                self.stdout.write(f"Fetching {city['name']}...")
                data = fetch_attractions_near(city['lat'], city['lon'], radius_km=30)
                saved_total += self._save(data, default_city=city['name'])
                time.sleep(2)  # Respectful rate limiting

        else:
            self.stdout.write("Fetching random cities sample...")
            data = fetch_random_attractions(count=100)
            saved_total += self._save(data)

        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Done! Saved/updated {saved_total} attractions.')
        )
        self.stdout.write(
            self.style.SUCCESS(f'Total in DB: {Attraction.objects.count()}')
        )

    def _save(self, osm_list: list, default_city: str = '') -> int:
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
                status = "Created" if created else "Updated"
                self.stdout.write(f"  {status}: {item['name']} ({item['city'] or default_city})")
                saved += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  Skip {item.get('name')}: {e}"))
        return saved
