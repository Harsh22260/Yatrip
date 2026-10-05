"""Celery tasks for booking inventory housekeeping."""

from __future__ import annotations

import logging

from celery import shared_task

from .services import expire_stale_holds

logger = logging.getLogger(__name__)


@shared_task(name="hotels.expire_stale_holds")
def expire_pending_bookings() -> str:
    """
    Release expired holds and put the rooms back on sale.

    The old task only looked at ``PENDING`` while the booking API writes
    ``HELD``, so it never expired anything the API created and those holds kept
    inventory blocked forever. The service handles both.
    """
    count = expire_stale_holds()
    return f"Expired {count} stale hold(s)"
