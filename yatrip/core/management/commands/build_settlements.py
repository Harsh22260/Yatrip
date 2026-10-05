"""
Build the India settlement index that drives catalogue ingestion.

Run once to populate, then re-run to extend coverage:

    python manage.py build_settlements                      # cities + towns
    python manage.py build_settlements --include-villages   # adds villages (huge)
    python manage.py build_settlements --replace
    python manage.py build_settlements --limit 2000
"""

from __future__ import annotations

import logging
import time

from django.core.management.base import BaseCommand

from core import settlements as S

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Populate the India settlement index from OpenStreetMap via Overpass."

    def add_arguments(self, parser):
        parser.add_argument("--include-villages", action="store_true",
                            help="Also index villages. There are ~650k in India, so this is slow.")
        parser.add_argument("--max-cells", type=int, default=0,
                            help="Stop after this many grid cells. 0 = the whole country.")
        parser.add_argument("--limit", type=int, default=0,
                            help="Stop after storing this many settlements. 0 = no limit.")
        parser.add_argument("--replace", action="store_true",
                            help="Delete existing settlements first.")
        parser.add_argument("--delay", type=float, default=1.2,
                            help="Seconds to wait between cells (default: 1.2).")

    def handle(self, *args, **options):
        places = S.FEATURE_TIERS[1] if options["include_villages"] else S.FEATURE_TIERS[0]
        label = "+".join(places)
        self.stdout.write(f"Indexing India settlements [{label}] from Overpass grid...")

        rows = []
        for index, row in enumerate(S.iter_settlements(
            places, max_cells=options["max_cells"] or None
        ), start=1):
            rows.append(row)
            if index % 200 == 0:
                self.stdout.write(f"  read {index}...")
            if options["limit"] and len(rows) >= options["limit"]:
                break
            if index % 100 == 0:
                time.sleep(options["delay"])

        if not rows:
            self.stderr.write(self.style.ERROR("No settlements returned. Overpass is likely busy; retry later."))
            return

        written = S.store_settlements(rows, replace=options["replace"])

        from core.models import Settlement
        total = Settlement.objects.count()
        self.stdout.write(self.style.SUCCESS(f"Stored {written} settlements"))
        self.stdout.write(f"Total settlements in index: {total}")
        top = S.top_settlements(12)
        self.stdout.write("Largest few: " + ", ".join(s.name for s in top))
