"""
Chat model providers with automatic failover.

Gemini's free tier allows only a small number of ``generateContent`` calls per
day per model (20 for the 3.x flash models as of this writing), which is not
enough to run a travel assistant on its own. ``LLM_PROVIDER_CHAIN`` therefore
lists models in preference order and this module walks the list whenever a
provider runs out of quota or is otherwise unavailable.

Two details matter for correctness:

* Each provider gets its **own** throttle. Rate limits are per provider, so a
  shared throttle would needlessly throttle Groq while Gemini recovers.
* A provider is only skipped for *availability* problems (quota, rate limit,
  timeout, upstream 5xx). A malformed tool schema is a bug in our code, so that
  still propagates instead of being masked by a working fallback.
"""

from __future__ import annotations

import functools
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from django.conf import settings

from yatrip.retry import Throttle, acall_with_backoff, call_with_backoff

logger = logging.getLogger(__name__)

DEFAULT_CHAIN = "gemini:gemini-3.8-flash,groq:openai/gpt-oss-120b"

# Once a provider is known to be out of daily quota, keep skipping it for this
# long. Without this, every request would still wait out the provider's throttle
# interval before discovering it is dead.
DEFAULT_COOLDOWN_SECONDS = 3600.0


class AllProvidersExhausted(RuntimeError):
    """Every configured provider was unavailable. ``reasons`` maps name -> error."""

    def __init__(self, reasons: dict[str, str]) -> None:
        self.reasons = reasons
        detail = "; ".join(f"{name}: {reason}" for name, reason in reasons.items())
        super().__init__(f"No LLM provider available ({detail})")


@dataclass(frozen=True)
class Provider:
    name: str
    model: str
    api_key: str
    #: Minimum seconds between calls for this provider's tier.
    min_interval: float
    kind: str
    extra: dict[str, Any] = field(default_factory=dict)


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


# Per-provider minimum interval, in priority order. The free tiers differ by
# roughly an order of magnitude, so they get separate knobs.
_GEMINI_INTERVAL = _env_float("GEMINI_MIN_INTERVAL_SECONDS", 13.0)
_GROQ_INTERVAL = _env_float("GROQ_MIN_INTERVAL_SECONDS", 2.0)
_OPENROUTER_INTERVAL = _env_float("OPENROUTER_MIN_INTERVAL_SECONDS", 2.0)


def _api_key(name: str) -> str:
    return (getattr(settings, f"{name.upper()}_API_KEY", "") or "").strip()


def get_providers() -> list[Provider]:
    """
    Configured providers, highest priority first.

    Entries whose API key is missing are dropped, so adding a provider to
    ``LLM_PROVIDER_CHAIN`` is safe before its key exists. Providers inside their
    circuit-breaker cooldown are also dropped, so a dead provider costs nothing.
    """
    raw_chain = os.getenv("LLM_PROVIDER_CHAIN") or getattr(
        settings, "LLM_PROVIDER_CHAIN", DEFAULT_CHAIN
    )

    providers: list[Provider] = []
    for entry in str(raw_chain).split(","):
        entry = entry.strip()
        if not entry:
            continue
        kind, _, model = entry.partition(":")
        kind = kind.strip().lower()
        model = model.strip()
        if not kind or not model:
            logger.warning("Ignoring malformed LLM_PROVIDER_CHAIN entry %r", entry)
            continue

        key = _api_key(kind)
        if not key:
            logger.info("Skipping %s provider: %s_API_KEY is not set", kind, kind.upper())
            continue

        remaining = breaker_remaining(kind)
        if remaining > 0:
            logger.info(
                "Skipping %s provider: out of quota, retrying in %.0f min",
                kind,
                remaining / 60.0,
            )
            continue

        interval = {
            "gemini": _GEMINI_INTERVAL,
            "groq": _GROQ_INTERVAL,
            "openrouter": _OPENROUTER_INTERVAL,
        }.get(kind, _env_float("LLM_MIN_INTERVAL_SECONDS", 2.0))

        providers.append(Provider(name=kind, model=model, api_key=key, min_interval=interval, kind=kind))

    return providers


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------
# provider name -> monotonic timestamp when it may be tried again
_broken_until: dict[str, float] = {}
_breaker_lock = threading.Lock()


def _cooldown_seconds() -> float:
    return _env_float("LLM_BREAKER_COOLDOWN", DEFAULT_COOLDOWN_SECONDS)


def breaker_remaining(name: str) -> float:
    """Seconds left before ``name`` may be retried (0 = usable)."""
    with _breaker_lock:
        until = _broken_until.get(name)
        if until is None:
            return 0.0
        remaining = until - time.monotonic()
        if remaining <= 0:
            _broken_until.pop(name, None)
            return 0.0
        return remaining


def trip_breaker(name: str, *, cooldown: float | None = None) -> None:
    """Stop using ``name`` for a while after a daily-quota failure."""
    delay = _cooldown_seconds() if cooldown is None else cooldown
    if delay <= 0:
        return
    with _breaker_lock:
        _broken_until[name] = time.monotonic() + delay
    logger.warning(
        "Provider %s disabled for %.0f min after exhausting its quota", name, delay / 60.0
    )


def reset_breakers() -> None:
    """Clear all circuit breakers (used by tests and management commands)."""
    with _breaker_lock:
        _broken_until.clear()


@functools.lru_cache(maxsize=None)
def _throttle_for(name: str, min_interval: float) -> Throttle:
    return Throttle(min_interval)


def throttle_for(provider: Provider) -> Throttle:
    return _throttle_for(provider.name, provider.min_interval)


def build_client(provider: Provider, *, max_retries: int = 0):
    """
    Construct a LangChain chat client for ``provider``.

    ``max_retries`` stays at 0 on purpose: the underlying SDKs retry with their
    own backoff, and composing that with :func:`acall_with_backoff` made a single
    chat turn sleep for minutes. All retrying happens in this module.
    """
    if provider.kind == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=provider.model,
            google_api_key=provider.api_key,
            temperature=0.7,
            max_retries=max_retries,
        )

    if provider.kind == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=provider.model,
            api_key=provider.api_key,
            temperature=0.7,
            max_retries=max_retries,
        )

    if provider.kind == "openrouter":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=provider.model,
            api_key=provider.api_key,
            base_url=os.getenv(
                "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
            ).rstrip("/"),
            temperature=0.7,
            max_retries=max_retries,
        )

    raise ValueError(f"Unknown LLM provider {provider.kind!r}")


# Failures that mean "this provider cannot serve the request right now".
_SKIP_MARKERS = (
    "429",
    "quota",
    "rate limit",
    "rate_limit",
    "resourceexhausted",
    "resource_exhausted",
    "toomanyrequests",
    "overloaded",
    "503",
    "502",
    "500",
    "deadline exceeded",
    "timeout",
    "timed out",
    "connection",
    "temporarily unavailable",
    "model is not found",
    "not_found",
    "notfound",
    "404",
)


def should_skip_provider(exc: Exception) -> bool:
    """True when the failure is an availability problem rather than our bug."""
    if isinstance(exc, AllProvidersExhausted):
        return False
    from yatrip.retry import DailyQuotaExhausted

    if isinstance(exc, DailyQuotaExhausted):
        return True
    message = str(exc).lower()
    return any(marker in message for marker in _SKIP_MARKERS)


async def ainvoke_chain(
    messages: Sequence[Any],
    *,
    tools: Sequence[Any] | None = None,
    label: str = "model call",
    max_retries: int = 3,
) -> tuple[Any, str]:
    """
    Invoke the first provider that can serve ``messages``.

    Returns ``(response, provider_name)``. Raises :class:`AllProvidersExhausted`
    when every configured provider is unavailable.
    """
    providers = get_providers()
    if not providers:
        raise AllProvidersExhausted({"": "no provider has its API key configured"})

    reasons: dict[str, str] = {}
    last_error: Exception | None = None

    for provider in providers:
        throttle = throttle_for(provider)
        try:
            client = build_client(provider)
            if tools:
                client = client.bind_tools(list(tools))
        except Exception as exc:  # noqa: BLE001
            logger.warning("%s: could not build client: %s", provider.name, exc)
            reasons[provider.name] = str(exc)[:200]
            continue

        async def attempt(_client=client, _throttle=throttle):
            await _throttle.wait()
            return await _client.ainvoke(list(messages))

        try:
            response = await acall_with_backoff(
                attempt,
                label=f"{label} via {provider.name}",
                max_retries=max_retries,
            )
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if not should_skip_provider(exc):
                # A real defect (bad tool schema, programming error). Retrying on
                # another model would hide it, so surface it immediately.
                logger.error("%s failed for a non-availability reason: %s", provider.name, exc)
                raise
            daily = _is_daily(exc)
            reason = "daily quota exhausted" if daily else "unavailable"
            if daily:
                trip_breaker(provider.name)
            logger.warning(
                "Falling back from %s (%s): %s", provider.name, reason, str(exc)[:200]
            )
            reasons[provider.name] = reason
            continue

        logger.info("%s served by %s", label, provider.name)
        return response, provider.name

    if last_error is not None and not reasons:
        raise last_error
    raise AllProvidersExhausted(reasons)


def _is_daily(exc: Exception) -> bool:
    from yatrip.retry import is_daily_quota_exhausted

    try:
        return is_daily_quota_exhausted(exc.__cause__ or exc) or is_daily_quota_exhausted(exc)
    except Exception:  # noqa: BLE001
        return False


def invoke_chain_sync(
    messages: Sequence[Any],
    *,
    tools: Sequence[Any] | None = None,
    label: str = "model call",
    max_retries: int = 3,
) -> tuple[Any, str]:
    """
    Blocking counterpart of :func:`ainvoke_chain`.

    Used by the image-analysis path, which already runs in a worker thread.
    """
    providers = get_providers()
    if not providers:
        raise AllProvidersExhausted({"": "no provider has its API key configured"})

    reasons: dict[str, str] = {}
    last_error: Exception | None = None

    for provider in providers:
        throttle = throttle_for(provider)
        try:
            client = build_client(provider)
            if tools:
                client = client.bind_tools(list(tools))
        except Exception as exc:  # noqa: BLE001
            logger.warning("%s: could not build client: %s", provider.name, exc)
            reasons[provider.name] = str(exc)[:200]
            continue

        def attempt(_client=client, _throttle=throttle):
            _throttle.wait_blocking()
            return _client.invoke(list(messages))

        try:
            response = call_with_backoff(
                attempt,
                label=f"{label} via {provider.name}",
                max_retries=max_retries,
            )
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if not should_skip_provider(exc):
                logger.error("%s failed for a non-availability reason: %s", provider.name, exc)
                raise
            daily = _is_daily(exc)
            reason = "daily quota exhausted" if daily else "unavailable"
            if daily:
                trip_breaker(provider.name)
            logger.warning(
                "Falling back from %s (%s): %s", provider.name, reason, str(exc)[:200]
            )
            reasons[provider.name] = reason
            continue

        logger.info("%s served by %s", label, provider.name)
        return response, provider.name

    if last_error is not None and not reasons:
        raise last_error
    raise AllProvidersExhausted(reasons)
