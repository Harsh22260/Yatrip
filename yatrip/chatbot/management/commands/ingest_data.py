"""Ingest Yatrip listings into the Pinecone knowledge base.

Thin wrapper around :mod:`chatbot.rag`, kept for backwards compatibility with
the original ``ingest_data`` command. New code should use ``sync_rag``.
"""

from django.core.management.base import BaseCommand, CommandError

from chatbot import rag


class Command(BaseCommand):
    help = "Ingest hotels, attractions, food, rentals and transport into Pinecone."

    def add_arguments(self, parser):
        parser.add_argument(
            "--model",
            action="append",
            choices=rag.CHOICES,
            help="Which model to ingest. Repeatable. Defaults to all.",
        )
        parser.add_argument(
            "--recreate",
            action="store_true",
            help="Drop and rebuild the Pinecone index first.",
        )

    def handle(self, *args, **options):
        try:
            counts = rag.sync(
                options["model"] or ["all"], recreate=options["recreate"]
            )
        except rag.RagConfigurationError as exc:
            raise CommandError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise CommandError(f"Ingestion failed: {exc}") from exc

        for name, count in counts.items():
            self.stdout.write(f"  {name:12} {count} document(s)")

        total = sum(counts.values())
        if not total:
            self.stdout.write(self.style.WARNING("Nothing was ingested."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Ingested {total} document(s)."))
