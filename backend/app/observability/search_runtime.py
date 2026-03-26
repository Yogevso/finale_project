"""Runtime metrics for the search backend selection and fallback path."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class SearchRuntimeSnapshot:
    configured_mode: str
    effective_mode: str
    dialect: str
    total_search_requests: int
    executions_by_mode: dict[str, int] = field(default_factory=dict)
    degraded_fallbacks: int = 0
    last_degraded_at: str | None = None
    last_requested_mode: str | None = None
    last_fallback_mode: str | None = None
    last_error_type: str | None = None
    last_error_message: str | None = None


class _SearchRuntimeRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._clear_unlocked()

    def _clear_unlocked(self) -> None:
        self._total_search_requests = 0
        self._executions_by_mode: dict[str, int] = {}
        self._degraded_fallbacks = 0
        self._last_degraded_at: str | None = None
        self._last_requested_mode: str | None = None
        self._last_fallback_mode: str | None = None
        self._last_error_type: str | None = None
        self._last_error_message: str | None = None

    def reset(self) -> None:
        with self._lock:
            self._clear_unlocked()

    def record_execution(self, *, effective_mode: str) -> None:
        with self._lock:
            self._total_search_requests += 1
            self._executions_by_mode[effective_mode] = (
                self._executions_by_mode.get(effective_mode, 0) + 1
            )

    def record_degraded_fallback(
        self,
        *,
        requested_mode: str,
        fallback_mode: str,
        error: BaseException | None = None,
    ) -> None:
        error_message = None
        if error is not None:
            raw_error_message = str(error).strip()
            if raw_error_message:
                error_message = raw_error_message[:200]
        with self._lock:
            self._degraded_fallbacks += 1
            self._last_degraded_at = _utc_iso_now()
            self._last_requested_mode = requested_mode
            self._last_fallback_mode = fallback_mode
            self._last_error_type = type(error).__name__ if error else None
            self._last_error_message = error_message

    def snapshot(
        self,
        *,
        configured_mode: str,
        effective_mode: str,
        dialect: str,
    ) -> SearchRuntimeSnapshot:
        with self._lock:
            return SearchRuntimeSnapshot(
                configured_mode=configured_mode,
                effective_mode=effective_mode,
                dialect=dialect,
                total_search_requests=self._total_search_requests,
                executions_by_mode=dict(self._executions_by_mode),
                degraded_fallbacks=self._degraded_fallbacks,
                last_degraded_at=self._last_degraded_at,
                last_requested_mode=self._last_requested_mode,
                last_fallback_mode=self._last_fallback_mode,
                last_error_type=self._last_error_type,
                last_error_message=self._last_error_message,
            )


_registry = _SearchRuntimeRegistry()


def record_search_execution(*, effective_mode: str) -> None:
    _registry.record_execution(effective_mode=effective_mode)


def record_search_degraded_fallback(
    *,
    requested_mode: str,
    fallback_mode: str,
    error: BaseException | None = None,
) -> None:
    _registry.record_degraded_fallback(
        requested_mode=requested_mode,
        fallback_mode=fallback_mode,
        error=error,
    )


def get_search_runtime_metrics(
    *,
    configured_mode: str,
    effective_mode: str,
    dialect: str,
) -> SearchRuntimeSnapshot:
    return _registry.snapshot(
        configured_mode=configured_mode,
        effective_mode=effective_mode,
        dialect=dialect,
    )


def reset_search_runtime_metrics() -> None:
    _registry.reset()
