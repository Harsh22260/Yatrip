"""
Import food places from OpenStreetMap.

    python manage.py fetch_food                          # a few settlements
    python manage.py fetch_food --city "Kushinagar"       # any place, any size
    python manage.py fetch_food --lat 28.6 --lon 77.2 --radius 10
    python manage.py fetch_food --all-cities             # every settlement in core.Settlement
    python manage.py fetch_food --all-cities --limit 200

``--city`` is the one that matters for small locations: it geocodes the name, so
a village or a small town works exactly like a metropolis instead of being
missing because it was not on a hard-coded city list.
"""

import time

from django.core.management.base import BaseCommand, CommandError

from food.models import FoodPlace
from food.services.osm_food_service import (
    fetch_food_near,
    geocode_place,
    radius_for_place,
    search_food_by_location,
)


class Command(BaseCommand):
    help = "Fetch food places from OpenStreetMap"

    def add_arguments(self, parser):
        parser.add_argument("--city", type=str)
        parser.add_argument("--lat", type=float)
        parser.add_argument("--lon", type=float)
        # None, not 8: leaving it unset lets radius_for_place() pick a radius from
        # how big the geocoded place is, which is what makes a village work.
        parser.add_argument(
            "--radius",
            type=int,
            default=None,
            help="Search radius in km (default: derived from the place type)",
        )
        parser.add_argument("--all-cities", action="store_true")
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="With --all-cities, stop after this many settlements (0 = no limit)",
        )
        parser.add_argument(
            "--pause", type=float, default=2.0, help="Seconds between Overpass calls"
        )

    def handle(self, *args, **options):
        pause = max(0.5, options["pause"])

        if options.get("lat") is not None and options.get("lon") is not None:
            radius = options["radius"] or 8
            data = fetch_food_near(options["lat"], options["lon"], radius)
            saved = self._save(data)

        elif options.get("city"):
            place = geocode_place(options["city"])
            if not place:
                raise CommandError(f"Could not geocode {options['city']!r}.")

            # A village needs a wider net than a metropolis to return anything:
            # every cafe in it is within a few kilometres, but there are few.
            radius = options["radius"] or radius_for_place(place.get("addresstype", ""))
            self.stdout.write(
                f"Resolved {options['city']} -> {place['lat']:.4f},{place['lon']:.4f} "
                f"({place.get('addresstype') or 'place'}), radius {radius}km"
            )
            data = search_food_by_location(options["city"], radius_km=radius)
            saved = self._save(data, place["city"])

        elif options.get("all_cities"):
            saved = self._sync_settlements(pause, options["limit"])

        else:
            from food.services.osm_food_service import fetch_random_food

            data = fetch_random_food(count=120)
            saved = self._save(data)

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. Saved/updated {saved} food places. "
                f"Total: {FoodPlace.objects.count()}"
            )
        )

    def _sync_settlements(self, pause, limit):
        """
        Walk the shared settlement table.

        This is what gives small locations coverage: the settlement table holds
        towns and villages with coordinates and population, so the sweep is no
        longer limited to a dozen metropolitan centres.
        """
        try:
            from core.models import Settlement
        except Exception as exc:  # noqa: BLE001
            raise CommandError(
                "core.Settlement is unavailable; run the settlement ingest first "
                f"or use --city/--lat/--lon instead ({exc})"
            ) from exc

        qs = Settlement.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
        if limit:
            qs = qs.order_by("-population")[:limit]
        else:
            qs = qs.order_by("-population")

        rows = list(qs.values("name", "latitude", "longitude", "population"))
        if not rows:
            raise CommandError(
                "core.Settlement is empty. Run `python manage.py ingest_settlements` "
                "first, or use --city/--lat/--lon for a one-off."
            )

        saved = 0
        for i, row in enumerate(rows, 1):
            self.stdout.write(
                f"[{i}/{len(rows)}] {row['name']} "
                f"(pop {row.get('population') or '?'})"
            )
            radius = 12 if (row.get("population") or 0) < 100_000 else 8
            try:
                data = fetch_food_near(row["latitude"], row["longitude"], radius_km=radius)
            except Exception as exc:  # noqa: BLE001
                self.stderr.write(f"  failed: {exc}")
                continue

            for place in data:
                if not place.get("city"):
                    place["city"] = row["name"]
            saved += self._save(data, row["name"], quiet=True)
            time.sleep(pause)

        return saved

    def _save(self, osm_list, default_city="", quiet=False):
        saved = 0
        for item in osm_list:
            if not item.get("osm_id"):
                continue
            try:
                defaults = {k: v for k, v in item.items() if k != "osm_id"}
                # Overpass has no ratings. Writing its placeholder 0.0 here wiped
                # any real rating on every re-sync, so those two keys are dropped
                # unless the payload actually carries a non-zero value.
                if not defaults.get("rating"):
                    defaults.pop("rating", None)
                if not defaults.get("review_count"):
                    defaults.pop("review_count", None)

                _, created = FoodPlace.objects.update_or_create(
                    osm_id=item["osm_id"], defaults=defaults
                )
                if not quiet:
                    city = item.get("city") or default_city
                    mark = "created" if created else "updated"
                    self.stdout.write(f"  {mark}: {item['name']} ({city})")
                saved += 1
            except Exception as e:  # noqa: BLE001
                self.stderr.write(f"  skip {item.get('name')}: {e}")
        return saved