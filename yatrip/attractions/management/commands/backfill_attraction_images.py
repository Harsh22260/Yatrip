"""
Attach real photographs to attractions from Wikimedia Commons.

Usage:
    python manage.py backfill_attraction_images
    python manage.py backfill_attraction_images --limit 20 --city Agra
    python manage.py backfill_attraction_images --all      # re-check rows that
                                                           # already have images
"""

from django.core.management.base import BaseCommand

from attractions.models import Attraction
from attractions.services import images as image_service


class Command(BaseCommand):
    help = "Fill missing attraction images from Wikimedia Commons"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", type=int, default=0,
            help="Only process this many rows (0 = all)",
        )
        parser.add_argument("--city", type=str, help="Restrict to one city")
        parser.add_argument(
            "--all", action="store_true",
            help="Re-check attractions that already have an image",
        )
        parser.add_argument(
            "--delay", type=float, default=0.4,
            help="Pause between Commons searches, in seconds",
        )

    def handle(self, *args, **options):
        qs = Attraction.objects.filter(is_active=True)
        if options.get("city"):
            qs = qs.filter(city__iexact=options["city"])
        if not options.get("all"):
            qs = qs.filter(image_url="")
        qs = qs.order_by("-rating", "-review_count")
        if options.get("limit"):
            qs = qs[: options["limit"]]

        total = qs.count()
        if not total:
            self.stdout.write(self.style.SUCCESS("Nothing to do."))
            return

        self.stdout.write(f"Looking up photographs for {total} attractions…")
        stats = image_service.backfill(
            qs,
            only_missing=not options.get("all"),
            delay=options["delay"],
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. filled={stats['filled']} "
                f"no_match={stats['no_match']} failed={stats['failed']}"
            )
        )
        if stats["no_match"]:
            # Said plainly, because a result of zero here means these rows will
            # rely on the generated fallback artwork rather than a real photo.
            self.stdout.write(
                self.style.WARNING(
                    f"{stats['no_match']} attractions have no photograph on "
                    f"Commons and will use the generated fallback."
                )
            )