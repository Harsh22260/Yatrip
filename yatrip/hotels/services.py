"""
Booking inventory services.

The public booking API used to call ``Booking.objects.create`` directly, which
had three problems:

1. availability was never checked, so the same room could be sold twice;
2. even with a check, two concurrent requests both read "1 unit free" and both
   booked it (a classic read-modify-write race);
3. ``RatePlan.discount_percent`` was ignored, so discounted plans charged full
   price.

All of that now lives here, where every mutation of the availability calendar
goes through the same code. Inventory is held at *hold* time and released again
on cancel/expire, so a hold is a real reservation rather than a promise.
"""

from __future__ import annotations

import logging
import secrets
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable

from django.db import transaction
from django.utils import timezone

from .models import Availability, Booking, Hotel, RatePlan, RoomType, RoomUnit

logger = logging.getLogger(__name__)

HOLD_MINUTES = 10


class BookingError(Exception):
    """Business-rule violation. ``code`` is safe to show to the client."""

    def __init__(self, message: str, *, code: str = "invalid", status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


class NoAvailability(BookingError):
    def __init__(self, message: str = "Not enough rooms available for those dates.") -> None:
        super().__init__(message, code="no_availability", status=409)


def _nights(check_in: date, check_out: date) -> list[date]:
    return [check_in + timedelta(days=i) for i in range((check_out - check_in).days)]


def compute_total(room_type: RoomType, nights: int, rate_plan: RatePlan | None) -> Decimal:
    """
    Price for ``nights``, applying the rate plan's multiplier *and* discount.

    ``discount_percent`` used to be silently dropped, so every discounted plan
    charged the undiscounted amount.
    """
    total = Decimal(room_type.base_price) * nights
    if rate_plan is None:
        return total.quantize(Decimal("0.01"))

    total = total * Decimal(rate_plan.price_multiplier)
    if rate_plan.discount_percent:
        total = total * (Decimal(100) - Decimal(str(rate_plan.discount_percent))) / Decimal(100)
    return total.quantize(Decimal("0.01"))


def _validate_rate_plan(room_type: RoomType, rate_plan: RatePlan | None) -> None:
    if rate_plan is not None and rate_plan.room_type_id != room_type.id:
        raise BookingError(
            "That rate plan does not belong to the selected room type.",
            code="rate_plan_mismatch",
        )


def _validate_room_unit(room_type: RoomType, room_unit: RoomUnit | None) -> None:
    """
    Stop a guest attaching a room from a different hotel.

    The old endpoint did a bare ``RoomUnit.objects.get(id=...)``, so any unit in
    the database could be attached to any booking.
    """
    if room_unit is None:
        return
    if room_unit.room_type_id != room_type.id:
        raise BookingError(
            "That room does not belong to the selected room type.",
            code="room_unit_mismatch",
        )
    if not room_unit.is_available:
        raise BookingError("That room is not available.", code="room_unavailable")


@transaction.atomic
def hold_rooms(
    *,
    user,
    room_type: RoomType,
    check_in: date,
    check_out: date,
    rate_plan: RatePlan | None = None,
    room_unit: RoomUnit | None = None,
    units: int = 1,
    meta: dict | None = None,
) -> Booking:
    """
    Reserve inventory and create a HELD booking, atomically.

    The availability rows for the requested nights are locked with
    ``select_for_update`` before being read, so two concurrent requests for the
    last room cannot both succeed.
    """
    if check_in >= check_out:
        raise BookingError("check_out must be after check_in", code="bad_dates")
    if check_in < timezone.localdate():
        raise BookingError("check_in cannot be in the past", code="bad_dates")
    if units < 1:
        raise BookingError("units must be at least 1", code="bad_units")

    nights = _nights(check_in, check_out)
    if not nights:
        raise BookingError("Stay must be at least one night", code="bad_dates")

    _validate_rate_plan(room_type, rate_plan)
    _validate_room_unit(room_type, room_unit)

    if rate_plan is not None and nights and nights[0] and rate_plan.min_stay > len(nights):
        raise BookingError(
            f"This rate plan requires a minimum stay of {rate_plan.min_stay} nights.",
            code="min_stay",
        )

    # Lock the rows we are about to change. Rows are created on demand so that a
    # room type added without a generated calendar still books correctly.
    rows = {
        row.date: row
        for row in (
            Availability.objects.select_for_update()
            .filter(room_type=room_type, room_unit__isnull=True, date__in=nights)
        )
    }

    missing = [night for night in nights if night not in rows]
    for night in missing:
        rows[night] = Availability.objects.create(
            room_type=room_type,
            room_unit=None,
            date=night,
            available_units=room_type.total_units,
            price=room_type.base_price,
        )

    short = [night.isoformat() for night in nights if rows[night].available_units < units]
    if short:
        raise NoAvailability(
            "Not enough rooms available on: " + ", ".join(short)
        )

    for night in nights:
        rows[night].available_units -= units
        rows[night].save(update_fields=["available_units", "updated_at"])

    booking = Booking.objects.create(
        user=user,
        hotel=room_type.hotel,
        room_type=room_type,
        room_unit=room_unit,
        rate_plan=rate_plan,
        check_in=check_in,
        check_out=check_out,
        total_price=compute_total(room_type, len(nights), rate_plan),
        status="HELD",
        hold_token=secrets.token_urlsafe(24),
        hold_expires_at=timezone.now() + timedelta(minutes=HOLD_MINUTES),
        meta={**(meta or {}), "units": units},
    )
    logger.info(
        "Held %d unit(s) of %s for %s (%s -> %s)",
        units,
        room_type,
        user,
        check_in,
        check_out,
    )
    return booking


@transaction.atomic
def release_rooms(booking: Booking, *, reason: str) -> None:
    """
    Return a booking's units to the calendar.

    Safe to call more than once: it only acts when the booking still occupies
    inventory, and it flips the status first so a concurrent cancel cannot
    double-credit.
    """
    if not booking.holds_inventory() or not booking.room_type_id:
        return

    units = int((booking.meta or {}).get("units", 1) or 1)
    nights = _nights(booking.check_in, booking.check_out)
    if not nights:
        return

    rows = {
        row.date: row
        for row in (
            Availability.objects.select_for_update()
            .filter(room_type_id=booking.room_type_id, room_unit__isnull=True, date__in=nights)
        )
    }
    for night in nights:
        row = rows.get(night)
        if row is None:
            continue
        # Never exceed the physical room count, even if availability was
        # hand-edited to a lower number.
        row.available_units = min(row.available_units + units, booking.room_type.total_units)
        row.save(update_fields=["available_units", "updated_at"])

    booking.status = "CANCELLED"
    booking.hold_token = None
    booking.hold_expires_at = None
    booking.meta = {**(booking.meta or {}), "released_at": str(timezone.now()), "release_reason": reason}
    booking.save(update_fields=["status", "hold_token", "hold_expires_at", "meta"])
    logger.info("Released %d unit(s) from booking %s (%s)", units, booking.id, reason)


@transaction.atomic
def confirm_booking(booking: Booking, hold_token: str) -> None:
    """Turn a HELD booking into a CONFIRMED one, holding the same units."""
    if booking.status != "HELD":
        raise BookingError("Booking is not awaiting confirmation.", code="bad_state", status=400)
    if not booking.hold_token or booking.hold_token != hold_token:
        raise BookingError("Invalid hold token.", code="bad_token", status=403)
    if booking.hold_expires_at and timezone.now() > booking.hold_expires_at:
        release_rooms(booking, reason="hold_expired")
        raise BookingError("This hold has expired.", code="expired", status=410)

    booking.status = "CONFIRMED"
    booking.hold_token = None
    booking.hold_expires_at = None
    booking.meta = {**(booking.meta or {}), "confirmed_at": str(timezone.now())}
    booking.save(update_fields=["status", "hold_token", "hold_expires_at", "meta"])


@transaction.atomic
def expire_stale_holds() -> int:
    """
    Release holds whose window has passed.

    Scans both HELD and PENDING: the booking API writes HELD, so a task that
    only looked at PENDING never expired anything it created, and stale holds
    kept inventory locked out indefinitely.
    """
    stale = list(
        Booking.objects.select_for_update(skip_locked=True)
        .filter(status__in=("HELD", "PENDING"), hold_expires_at__isnull=False, hold_expires_at__lt=timezone.now())
        .select_related("room_type")
    )
    for booking in stale:
        release_rooms(booking, reason="hold_expired")
    if stale:
        logger.info("Expired %d stale hold(s)", len(stale))
    return len(stale)
