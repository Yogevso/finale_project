"""Degradation policy annotations and metrics for exception handlers.

Each broad `except` in the codebase should be classified:
- FAIL_FAST: re-raise immediately; let the caller handle it
- RETRYABLE: transient failure; schedule retry with backoff
- COMPENSATING: rollback partial work, then fail
- LOSSY: intentionally swallow; feature is optional / best-effort
"""

from __future__ import annotations

import enum
import logging
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Simple counter dict for monitoring; replace with real metrics (Prometheus, etc.)
_degradation_counts: dict[str, int] = {}


class DegradationPolicy(str, enum.Enum):
    FAIL_FAST = "fail_fast"
    RETRYABLE = "retryable"
    COMPENSATING = "compensating"
    LOSSY = "lossy"


def record_degradation(
    policy: DegradationPolicy,
    component: str,
    error: BaseException | None = None,
) -> None:
    """Record a degradation event for alerting/monitoring."""
    key = f"{policy.value}:{component}"
    _degradation_counts[key] = _degradation_counts.get(key, 0) + 1
    logger.warning(
        "Degradation [%s] in %s (count=%d): %s",
        policy.value,
        component,
        _degradation_counts[key],
        error or "unknown",
    )


def get_degradation_counts() -> dict[str, int]:
    """Return current degradation counts (for health/admin endpoints)."""
    return dict(_degradation_counts)


def lossy(component: str) -> Callable:
    """Decorator marking a function's exception handler as intentionally lossy."""

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except Exception as exc:  # policy: DEGRADED — telemetry probes must not block degraded-mode fallback
                record_degradation(DegradationPolicy.LOSSY, component, exc)
                return None

        @wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except Exception as exc:  # policy: DEGRADED — telemetry probes must not block degraded-mode fallback
                record_degradation(DegradationPolicy.LOSSY, component, exc)
                return None

        import asyncio

        if asyncio.iscoroutinefunction(fn):
            return async_wrapper
        return wrapper

    return decorator
