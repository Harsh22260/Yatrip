"""
Management command to pre-populate attractions from OSM.
Usage:
  python manage.py fetch_attractions                  # fetch all random cities
  python manage.py fetch_attractions --city "Jaipur"  # fetch specific city
  python manage.py fetch_attractions --lat 28.6 --lon 77.2 --radius 50
"""

import sys

from django.core.management.base import BaseCommand
from attractions.services.cities import CITY_TIERS
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
        parser.add_argument('--all-cities', action='store_true',
                            help='Deprecated alias for --region all')
        parser.add_argument('--region', type=str, default='',
                            help='north | south | west | east | central | all')
        parser.add_argument('--skip-images', action='store_true',
                            help='Do not look up photographs after fetching')
        parser.add_argument('--city-limit', type=int, default=0,
                            help='Only fetch this many cities from the region')

    def handle(self, *args, **options):
        # The console on Windows defaults to a codepage that cannot render the
        # status glyphs in these messages, and the resulting UnicodeEncodeError
        # aborts a long import at the very end. Force UTF-8 so a full-country run
        # cannot die while printing its own summary.
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

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

        elif options.get('region') or options.get('all_cities'):
            saved_total += self._sync_cities(options)

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

    def _sync_cities(self, options) -> int:
        """
        Walk a region's cities, then attach photographs in one pass.

        Images are deferred to the end deliberately. They come from Wikimedia,
        a different service with different rate limits, and interleaving the
        two means a throttled image lookup stalls the geographic import.
        """
        region = (options.get('region') or 'all').lower()
        regions = (
            CITY_TIERS if region == 'all'
            else {region: CITY_TIERS.get(region, [])}
        )
        if not regions.get(region) and region != 'all':
            self.stderr.write(
                self.style.ERROR(
                    f"Unknown region {region!r}. Choose from: "
                    + ", ".join(sorted(CITY_TIERS))
                )
            )
            return 0

        saved_total = 0
        limit = options.get('city_limit') or 0
        for name, cities in regions.items():
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n== {name} =="))
            done = 0
            for city_name, lat, lon in cities:
                if limit and done >= limit:
                    self.stdout.write(f"(stopping after {done} cities)")
                    break
                done += 1
                try:
                    data = fetch_attractions_near(lat, lon, radius_km=options['radius'])
                except Exception as exc:
                    # One city failing must not abandon the other hundred.
                    self.stderr.write(
                        self.style.WARNING(f"  {city_name}: {exc}")
                    )
                    continue
                n = self._save(data, default_city=city_name, quiet=True)
                saved_total += n
                self.stdout.write(f"  {city_name}: {n}")
                # Overpass is a shared free service.
                time.sleep(2)

        if not options.get('skip_images'):
            self.stdout.write(self.style.MIGRATE_HEADING('\n== images =='))
            from attractions.services import images as image_service
            stats = image_service.backfill(
                Attraction.objects.filter(is_active=True, image_url='')
            )
            self.stdout.write(
                f"  filled={stats['filled']} no_match={stats['no_match']}"
            )
        return saved_total

    def _save(self, osm_list: list, default_city: str = '', quiet: bool = False) -> int:
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
                        # Left alone when already set, so a re-sync does not
                        # overwrite a photograph that came from Wikimedia with a
                        # blank or worse OSM value.
                        **({} if Attraction.objects.filter(
                            osm_id=osm_id
                        ).exclude(image_url='').exists() else {
                            'image_url': item.get('image_url', '')[:200]
                        }),
                        'opening_hours': item.get('opening_hours', {}),
                        'is_free': item.get('is_free', True),
                        'entry_fee': item.get('entry_fee'),
                        'osm_type': item.get('osm_type', ''),
                        'is_active': True,
                    }
                )
                status = "Created" if created else "Updated"
                if not quiet:
                    self.stdout.write(
                        f"  {status}: {item['name']} ({item['city'] or default_city})"
                    )
                saved += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  Skip {item.get('name')}: {e}"))
        return saved
