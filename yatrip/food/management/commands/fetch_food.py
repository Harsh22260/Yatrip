"""
python manage.py fetch_food                    # random cities
python manage.py fetch_food --city "Delhi"
python manage.py fetch_food --lat 28.6 --lon 77.2 --radius 10
python manage.py fetch_food --all-cities
"""
from django.core.management.base import BaseCommand
from food.services.osm_food_service import fetch_food_near, fetch_random_food, FOOD_CITIES, search_food_by_location
from food.models import FoodPlace
import time


class Command(BaseCommand):
    help = 'Fetch food places from OpenStreetMap'

    def add_arguments(self, parser):
        parser.add_argument('--city',       type=str)
        parser.add_argument('--lat',        type=float)
        parser.add_argument('--lon',        type=float)
        parser.add_argument('--radius',     type=int, default=8)
        parser.add_argument('--all-cities', action='store_true')

    def handle(self, *args, **options):
        saved = 0
        if options.get('lat') and options.get('lon'):
            data = fetch_food_near(options['lat'], options['lon'], options['radius'])
            saved += self._save(data)
        elif options.get('city'):
            data = search_food_by_location(options['city'])
            saved += self._save(data, options['city'])
        elif options.get('all_cities'):
            for city in FOOD_CITIES:
                self.stdout.write(f"Fetching {city['name']}...")
                data = fetch_food_near(city['lat'], city['lon'], radius_km=8)
                saved += self._save(data, city['name'])
                time.sleep(2)
        else:
            data = fetch_random_food(count=120)
            saved += self._save(data)

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Done! Saved/updated {saved} food places. Total: {FoodPlace.objects.count()}'
        ))

    def _save(self, osm_list, default_city=''):
        saved = 0
        for item in osm_list:
            if not item.get('osm_id'):
                continue
            try:
                _, created = FoodPlace.objects.update_or_create(
                    osm_id=item['osm_id'],
                    defaults={k: v for k, v in item.items() if k != 'osm_id'}
                )
                self.stdout.write(f"  {'✓' if created else '↻'} {item['name']} ({item.get('city') or default_city})")
                saved += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  Skip {item.get('name')}: {e}"))
        return saved