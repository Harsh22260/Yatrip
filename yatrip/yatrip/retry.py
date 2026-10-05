"""
Shared retry and rate-limit helpers.

Both the chatbot (Gemini free tier allows only ~5 generateContent calls per
minute) and the knowledge-base ingester (100 embed calls per minute) hit
upstream quota limits, so the backoff logic lives here once.
"""

from __future__ import annotations

import asyncio
import logging
import re
import threading
import time
from typing import Any, Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

RATE_LIMIT_HINTS = (
    "429",
    "quota",
    "rate limit",
    "rate_limit",
    "resourceexhausted",
    "resource_exhausted",
    "toomanyrequests",
)

# Gemini's free tier also imposes *daily* per-model request caps. Retrying those
# is pointless: the quota only resets the next day, and the API still suggests a
# short "retry in Ns" delay which is actively misleading.
DAILY_QUOTA_MARKERS = (
    "perday",
    "per_day",
    "requestsperday",
    "generaterequestsperday",
    "daily limit",
)

_RETRY_AFTER_PATTERN = re.compile(r"retry in\s+([\d.]+)\s*s", re.IGNORECASE)
_RETRY_DELAY_PATTERN = re.compile(r"retry_delay[^{]*seconds:\s*(\d+)", re.IGNORECASE)

MAX_BACKOFF_SECONDS = 120.0


def is_rate_limited(exc: Exception) -> bool:
    """Best-effort detection of an upstream quota/rate-limit rejection."""
    message = str(exc).lower()
    return any(hint in message for hint in RATE_LIMIT_HINTS)


def is_daily_quota_exhausted(exc: Exception) -> bool:
    """
    True when the failure is a per-day cap rather than a short-lived rate limit.

    Retrying one of these just burns wall-clock time: the window resets in
    hours, not seconds.
    """
    message = str(exc).lower()
    if not any(marker in message for marker in DAILY_QUOTA_MARKERS):
        return False
    # A per-day failure can also surface as a plain 429; require the per-day
    # marker so ordinary per-minute throttling keeps its retry behaviour.
    return True


def retry_delay(exc: Exception, attempt: int) -> float:
    """
    How long to wait before retrying ``exc``.

    Prefers the delay the upstream API explicitly asked for, since that is
    usually the accurate quota reset time. Falls back to exponential backoff.
    """
    for pattern in (_RETRY_AFTER_PATTERN, _RETRY_DELAY_PATTERN):
        match = pattern.search(str(exc))
        if match:
            try:
                return min(float(match.group(1)) + 2.0, MAX_BACKOFF_SECONDS)
            except ValueError:
                break
    return min(2.0**attempt, MAX_BACKOFF_SECONDS)


def call_with_backoff(
    operation: Callable[[], T],
    *,
    label: str = "operation",
    max_retries: int = 6,
    on_retry: Callable[[Exception, float], None] | None = None,
) -> T:
    """Blocking variant of :func:`acall_with_backoff`."""
    return _retry_loop_sync(operation, label=label, max_retries=max_retries, on_retry=on_retry)


class DailyQuotaExhausted(RuntimeError):
    """
    Raised instead of sleeping when a per-day upstream cap is hit.

    Carries the original error as ``__cause__`` so callers can log it without
    the retry loop hanging for minutes.
    """


def _should_give_up(exc: Exception) -> bool:
    if is_daily_quota_exhausted(exc):
        return True
    # A generic timeout/connection reset is not worth sleeping on either.
    message = str(exc).lower()
    return "deadline exceeded" in message or "timeout" in message


def _retry_loop_sync(operation, *, label, max_retries, on_retry):
    for attempt in range(max_retries + 1):
        try:
            return operation()
        except Exception as exc:  # noqa: BLE001
            if _should_give_up(exc):
                reason = (
                    "a daily quota cap"
                    if is_daily_quota_exhausted(exc)
                    else "a timeout"
                )
                logger.error("%s hit %s; not retrying: %s", label, reason, exc)
                raise DailyQuotaExhausted(
                    f"{label} unavailable: {reason}"
                ) from exc
            if attempt >= max_retries:
                logger.error("%s failed after %d attempt(s): %s", label, max_retries + 1, exc)
                raise
            delay = retry_delay(exc, attempt)
            logger.warning(
                "%s hit %s, retrying in %.0fs (attempt %d/%d)",
                label,
                "a rate limit" if is_rate_limited(exc) else "a transient error",
                delay,
                attempt + 1,
                max_retries,
            )
            if on_retry is not None:
                on_retry(exc, delay)
            time.sleep(delay)
    raise AssertionError("unreachable")


async def acall_with_backoff(
    operation: Callable[[], Awaitable[T]],
    *,
    label: str = "operation",
    max_retries: int = 6,
) -> T:
    """Await ``operation``, retrying short-lived rate limits and transient errors."""
    for attempt in range(max_retries + 1):
        try:
            return await operation()
        except Exception as exc:  # noqa: BLE001
            if _should_give_up(exc):
                reason = (
                    "a daily quota cap"
                    if is_daily_quota_exhausted(exc)
                    else "a timeout"
                )
                logger.error("%s hit %s; not retrying: %s", label, reason, exc)
                raise DailyQuotaExhausted(
                    f"{label} unavailable: {reason}"
                ) from exc
            if attempt >= max_retries:
                logger.error("%s failed after %d attempt(s): %s", label, max_retries + 1, exc)
                raise
            delay = retry_delay(exc, attempt)
            logger.warning(
                "%s hit %s, retrying in %.0fs (attempt %d/%d)",
                label,
                "a rate limit" if is_rate_limited(exc) else "a transient error",
                delay,
                attempt + 1,
                max_retries,
            )
            await asyncio.sleep(delay)
    raise AssertionError("unreachable")


class Throttle:
    """
    Process-wide minimum interval between calls.

    The slot is reserved inside a lock, so concurrent callers queue up instead
    of all deciding at once that they can fire immediately. Uses a plain
    timestamp rather than an ``asyncio`` primitive so it is safe to share
    between event loops (the chatbot runs a fresh loop per request).
    """

    def __init__(self, min_interval: float) -> None:
        self.min_interval = max(float(min_interval), 0.0)
        self._lock = threading.Lock()
        self._next_slot = 0.0

    def reserve(self) -> float:
        """Claim the next slot and return how long the caller must wait."""
        if self.min_interval <= 0:
            return 0.0
        with self._lock:
            now = time.monotonic()
            slot = max(now, self._next_slot)
            self._next_slot = slot + self.min_interval
            return max(slot - now, 0.0)

    async def wait(self) -> None:
        delay = self.reserve()
        if delay > 0:
            await asyncio.sleep(delay)

    def wait_blocking(self) -> None:
        delay = self.reserve()
        if delay > 0:
            time.sleep(delay)
