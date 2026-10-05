"""Embed Yatrip's catalogue into the Pinecone knowledge base."""

from django.core.management.base import BaseCommand, CommandError

from chatbot import rag


class Command(BaseCommand):
    help = (
        "Sync hotels, food, attractions, rentals and transport into the "
        "Pinecone knowledge base used by the chatbot."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--model",
            action="append",
            choices=rag.CHOICES,
            help=(
                "Which model to index. Repeatable. Defaults to every model "
                "(equivalent to --model all)."
            ),
        )
        parser.add_argument(
            "--recreate",
            action="store_true",
            help=(
                "Drop and rebuild the Pinecone index. Required when the index "
                "dimension no longer matches the configured embedding model."
            ),
        )
        parser.add_argument(
            "--status",
            action="store_true",
            help="Only report how many vectors the index currently holds.",
        )

    def handle(self, *args, **options):
        if options["status"]:
            total = rag.count_indexed_vectors()
            self.stdout.write(f"Index holds {total} vector(s).")
            return

        try:
            counts = rag.sync(
                options["model"] or ["all"], recreate=options["recreate"]
            )
        except rag.RagConfigurationError as exc:
            raise CommandError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise CommandError(f"Knowledge base sync failed: {exc}") from exc

        if not any(counts.values()):
            self.stdout.write(
                self.style.WARNING("Nothing was indexed. Checked models: " + ", ".join(counts))
            )
            return

        for name, count in counts.items():
            style = self.style.SUCCESS if count else self.style.WARNING
            self.stdout.write(f"  {name:12} {count} document(s)")

        self.stdout.write(
            self.style.SUCCESS(
                f"Indexed {sum(counts.values())} document(s); "
                f"index now holds {rag.count_indexed_vectors()} vector(s)."
            )
        )
