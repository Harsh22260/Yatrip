"""
Legacy RAG sync entry point.

The real implementation now lives in :mod:`chatbot.rag` (shared with the
``sync_rag`` management command and the MCP ``search_knowledge_base`` tool).
This script is kept because it is referenced by the scheduled-task docs, but it
just delegates so there is only one ingestion code path.

Previously this file embedded with a non-existent model
(``models/embedding-001``), upserted in a single unbatched call, and never
supplied document ids - so every run appended a fresh near-duplicate copy of
all 405 records to the index.

Usage::

    python scripts/auto_rag_sync.py --once
    python scripts/auto_rag_sync.py --interval 1800
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time

import django

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "yatrip.settings")
django.setup()

from chatbot import rag  # noqa: E402

DEFAULT_INTERVAL_SECONDS = 1800
logger = logging.getLogger("yatrip.auto_rag_sync")


def run_sync() -> bool:
    """Ingest every catalogue record. Returns True on success."""
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting RAG sync...")
    try:
        report = rag.sync(("all",))
    except rag.RagConfigurationError as exc:
        print(f"RAG sync skipped: {exc}", file=sys.stderr)
        return False
    except Exception as exc:  # noqa: BLE001
        logger.exception("RAG sync failed")
        print(f"RAG sync failed: {exc}", file=sys.stderr)
        return False

    print(
        "RAG sync complete: "
        + ", ".join(f"{source}={count}" for source, count in report.items())
    )
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync Yatrip catalogue data into Pinecone.")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single sync and exit (use this from cron / Task Scheduler).",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL_SECONDS,
        help=f"Seconds between runs when looping (default: {DEFAULT_INTERVAL_SECONDS}).",
    )
    args = parser.parse_args(argv)

    if args.once or args.interval <= 0:
        return 0 if run_sync() else 1

    failures = 0
    while True:
        if not run_sync():
            failures += 1
        print(f"Waiting {args.interval} seconds for next sync...")
        time.sleep(args.interval)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
