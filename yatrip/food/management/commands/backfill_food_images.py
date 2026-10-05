"""
Backfill photographs for food places, cafes first.

    python manage.py backfill_food_images                      # cafes only
    python manage.py backfill_food_images --all                # every category
    python manage.py backfill_food_images --limit 200
    python manage.py backfill_food_images --place "Cafe XYZ, Pune"

Cafes are the default because that is where the cards look worst: they almost
never carry an OSM ``image`` tag, so nearly every one of them fell back to plain
artwork.

Sequential and rate limited on purpose. Wikimedia is a shared free service and a
burst of searches gets the address throttled.
"""

from django.core.management.base import BaseCommand

from food.models import FoodPlace
from food.services import images as food_images


class Command(BaseCommand):
    help = "Backfill image_url for food places from Wikimedia Commons / Wikipedia"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Backfill every category, not just cafes",
        )
        parser.add_argument("--place", type=str, help="Backfill a single place by name")
        parser.add_argument("--limit", type=int, default=0)
        parser.add_argument("--delay", type=float, default=0.4)
        parser.add_argument(
            "--include-filled",
            action="store_true",
            help="Also re-look-up places that already have an image",
        )

    def handle(self, *args, **options):
        qs = FoodPlace.objects.filter(is_active=True)

        if options.get("place"):
            qs = qs.filter(name__icontains=options["place"])
        elif not options.get("all"):
            qs = qs.filter(category="cafe")

        stats = food_images.backfill(
            qs,
            only_missing=not options.get("include_filled"),
            limit=options["limit"] or None,
            delay=options["delay"],
        )

        self.stdout.write(
            self.style.SUCCESS(
                "\nfilled={filled} no_match={no_match} failed={failed}".format(**stats)
            )
        )
        if stats["no_match"]:
            # self.stderr.write already writes; wrapping it in self.stdout.write
            # printed the return value (None) as a stray line.
            self.stderr.write(
                "Places with no photograph on Wikimedia are left empty on "
                "purpose; the frontend renders generated artwork for those."
            )