"""Import transport hubs from OpenStreetMap.

    python manage.py fetch_transport --city Bengaluru
    python manage.py fetch_transport --city Bengaluru --radius 40
    python manage.py fetch_transport --lat 12.9716 --lon 77.5946 --radius 25
    python manage.py fetch_transport --all-cities          # every indexed settlement
    python manage.py fetch_transport --all-cities --limit 20
"""

from django.core.management.base import BaseCommand, CommandError

from transport.models import TransportNode
from transport.services import osm_transport


class Command(BaseCommand):
    help = "Fetch bus stands, auto stands, metro, railway and airport hubs from OSM."

    def add_arguments(self, parser):
        parser.add_argument("--city", help="City name to geocode and fetch around.")
        parser.add_argument("--lat", type=float, help="Latitude, use with --lon.")
        parser.add_argument("--lon", type=float, help="Longitude, use with --lat.")
        parser.add_argument("--state", default="", help="State name, for display only.")
        parser.add_argument(
            "--radius", type=float, default=30.0, help="Radius in km (default 30)."
        )
        parser.add_argument(
            "--all-cities",
            action="store_true",
            help="Fetch for every settlement in the index, largest first.",
        )
        parser.add_argument(
            "--limit", type=int, default=50, help="With --all-cities, how many settlements."
        )
        parser.add_argument(
            "--reclassify",
            action="store_true",
            help="Re-run operator/name classification over stored rows and exit.",
        )

    def handle(self, *args, **opts):
        if opts["reclassify"]:
            result = osm_transport.reclassify_stored()
            self.stdout.write(self.style.SUCCESS(f"Reclassified: {result['reclassified']}"))
            return

        if opts["all_cities"]:
            self._all_cities(opts)
            return

        if opts["lat"] is not None and opts["lon"] is not None:
            result = osm_transport.fetch_near(
                opts["lat"], opts["lon"], opts["radius"], state=opts["state"]
            )
        elif opts["city"]:
            result = osm_transport.fetch_for_city(opts["city"], opts["radius"])
        else:
            raise CommandError("Pass --city, or --lat with --lon, or --all-cities.")

        self.stdout.write(
            self.style.SUCCESS(
                f"created={result['created']} updated={result['updated']} "
                f"raw={result['raw']} total={TransportNode.objects.count()}"
            )
        )

    def _all_cities(self, opts):
        from core.settlements import top_settlements

        cities = top_settlements(limit=opts["limit"])
        if not cities:
            raise CommandError(
                "Settlement index is empty. Run: python manage.py build_settlements"
            )

        totals = {"created": 0, "updated": 0}
        for index, place in enumerate(cities, start=1):
            name = place.name
            self.stdout.write(f"[{index}/{len(cities)}] {name}")
            try:
                result = osm_transport.fetch_for_city(name, radius_km=opts["radius"])
            except Exception as exc:  # noqa: BLE001 - one bad city must not stop the run
                self.stderr.write(f"  failed: {exc}")
                continue
            totals["created"] += result["created"]
            totals["updated"] += result["updated"]
            self.stdout.write(
                f"  +{result['created']} new, {result['updated']} updated "
                f"(running total {TransportNode.objects.count()})"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"done: created={totals['created']} updated={totals['updated']} "
                f"total={TransportNode.objects.count()}"
            )
        )
