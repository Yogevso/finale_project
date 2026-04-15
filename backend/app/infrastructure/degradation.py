"""Degradation policy annotations and runtime metrics for exception handlers."""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps
from threading import Lock
from typing import Any, Callable

logger = logging.getLogger(__name__)


class DegradationPolicy(str, enum.Enum):
    FAIL_FAST = "fail_fast"
    RETRYABLE = "retryable"
    COMPENSATING = "compensating"
    LOSSY = "lossy"


@dataclass(frozen=True, slots=True)
class ComponentDegradationMetrics:
    total_events: int
    by_policy: dict[str, int] = field(default_factory=dict)
    last_recorded_at: str | None = None
    last_error_type: str | None = None
    last_error_message: str | None = None


@dataclass(frozen=True, slots=True)
class DegradationMetricsSnapshot:
    total_events: int
    by_policy: dict[str, int] = field(default_factory=dict)
    by_key: dict[str, int] = field(default_factory=dict)
    components: dict[str, ComponentDegradationMetrics] = field(default_factory=dict)
    last_recorded_at: str | None = None


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class _DegradationRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._clear_unlocked()

    def _clear_unlocked(self) -> None:
        self._total_events = 0
        self._by_policy: dict[str, int] = {}
        self._by_key: dict[str, int] = {}
        self._components: dict[str, dict[str, Any]] = {}
        self._last_recorded_at: str | None = None

    def reset(self) -> None:
        with self._lock:
            self._clear_unlocked()

    def record(
        self,
        *,
        policy: DegradationPolicy,
        component: str,
        error: BaseException | None = None,
    ) -> int:
        timestamp = _utc_iso_now()
        key = f"{policy.value}:{component}"
        error_message = None
        if error is not None:
            raw_error_message = str(error).strip()
            if raw_error_message:
                error_message = raw_error_message[:200]

        with self._lock:
            self._total_events += 1
            self._last_recorded_at = timestamp
            self._by_key[key] = self._by_key.get(key, 0) + 1
            self._by_policy[policy.value] = self._by_policy.get(policy.value, 0) + 1
            component_metrics = self._components.setdefault(
                component,
                {
                    "total_events": 0,
                    "by_policy": {},
                    "last_recorded_at": None,
                    "last_error_type": None,
                    "last_error_message": None,
                },
            )
            component_metrics["total_events"] += 1
            component_metrics["by_policy"][policy.value] = (
                component_metrics["by_policy"].get(policy.value, 0) + 1
            )
            component_metrics["last_recorded_at"] = timestamp
            component_metrics["last_error_type"] = type(error).__name__ if error else None
            component_metrics["last_error_message"] = error_message
            return self._by_key[key]

    def snapshot(self) -> DegradationMetricsSnapshot:
        with self._lock:
            return DegradationMetricsSnapshot(
                total_events=self._total_events,
                by_policy=dict(self._by_policy),
                by_key=dict(self._by_key),
                components={
                    component: ComponentDegradationMetrics(
                        total_events=metrics["total_events"],
                        by_policy=dict(metrics["by_policy"]),
                        last_recorded_at=metrics["last_recorded_at"],
                        last_error_type=metrics["last_error_type"],
                        last_error_message=metrics["last_error_message"],
                    )
                    for component, metrics in self._components.items()
                },
                last_recorded_at=self._last_recorded_at,
            )


_degradation_registry = _DegradationRegistry()


def record_degradation(
    policy: DegradationPolicy,
    component: str,
    error: BaseException | None = None,
) -> None:
    """Record a degradation event for alerting and health surfaces."""
    count = _degradation_registry.record(policy=policy, component=component, error=error)
    logger.warning(
        "Degradation [%s] in %s (count=%d): %s",
        policy.value,
        component,
        count,
        error or "unknown",
    )


def get_degradation_counts() -> dict[str, int]:
    """Return flat counts for compatibility with older health callers."""
    return dict(_degradation_registry.snapshot().by_key)


def get_degradation_metrics() -> DegradationMetricsSnapshot:
    """Return a structured snapshot of degradation counters and recent failures."""
    return _degradation_registry.snapshot()


def reset_degradation_metrics() -> None:
    """Clear degradation counters for tests and controlled runtime resets."""
    _degradation_registry.reset()


def lossy(component: str) -> Callable:
    """Decorator marking a function's exception handler as intentionally lossy."""

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except (
                Exception
            ) as exc:  # policy: DEGRADED - telemetry probes must not block degraded-mode fallback
                record_degradation(DegradationPolicy.LOSSY, component, exc)
                return None

        @wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await fn(*args, **kwargs)
            except (
                Exception
            ) as exc:  # policy: DEGRADED - telemetry probes must not block degraded-mode fallback
                record_degradation(DegradationPolicy.LOSSY, component, exc)
                return None

        import asyncio

        if asyncio.iscoroutinefunction(fn):
            return async_wrapper
        return wrapper

    return decorator
