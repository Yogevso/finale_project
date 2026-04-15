"""Use-case telemetry contracts and in-memory sink implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from time import perf_counter
from typing import Literal, Protocol

UseCaseKind = Literal["command", "query", "workflow", "collab", "other"]
UseCaseOutcome = Literal["success", "failure"]


@dataclass(frozen=True, slots=True)
class UseCaseTelemetryEvent:
    """One normalized use-case telemetry datapoint."""

    use_case_id: str
    use_case_kind: UseCaseKind
    outcome: UseCaseOutcome
    duration_ms: float
    started_at: str
    dimensions: dict[str, str] = field(default_factory=dict)


class UseCaseTelemetrySink(Protocol):
    """Telemetry sink contract."""

    def record(self, event: UseCaseTelemetryEvent) -> None: ...


class InMemoryUseCaseTelemetrySink(UseCaseTelemetrySink):
    """Thread-safe in-memory sink used by runtime and tests."""

    def __init__(self) -> None:
        self._events: list[UseCaseTelemetryEvent] = []
        self._lock = Lock()

    def record(self, event: UseCaseTelemetryEvent) -> None:
        with self._lock:
            self._events.append(event)

    def snapshot(self) -> list[UseCaseTelemetryEvent]:
        with self._lock:
            return list(self._events)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


_GLOBAL_TELEMETRY_SINK = InMemoryUseCaseTelemetrySink()


def get_use_case_telemetry_sink() -> InMemoryUseCaseTelemetrySink:
    """Return process-wide telemetry sink."""
    return _GLOBAL_TELEMETRY_SINK


def reset_use_case_telemetry_sink() -> None:
    """Clear process-wide telemetry sink state."""
    _GLOBAL_TELEMETRY_SINK.clear()


def _normalize_identifier(raw: str) -> str:
    trimmed = (raw or "").strip()
    if not trimmed:
        return "unknown"

    pieces: list[str] = []
    current = []
    for char in trimmed:
        if char.isalnum():
            current.append(char.lower())
        else:
            if current:
                pieces.append("".join(current))
                current = []
    if current:
        pieces.append("".join(current))
    return "_".join(pieces) if pieces else "unknown"


def build_use_case_id(*, kind: UseCaseKind, name: str) -> str:
    """Build canonical telemetry identifier across services."""
    return f"{kind}.{_normalize_identifier(name)}"


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_use_case_telemetry(
    *,
    sink: UseCaseTelemetrySink | None,
    use_case_kind: UseCaseKind,
    use_case_name: str,
    outcome: UseCaseOutcome,
    duration_ms: float,
    started_at: str,
    dimensions: dict[str, str] | None = None,
) -> UseCaseTelemetryEvent:
    """Record a single telemetry event in sink and return it."""
    event = UseCaseTelemetryEvent(
        use_case_id=build_use_case_id(kind=use_case_kind, name=use_case_name),
        use_case_kind=use_case_kind,
        outcome=outcome,
        duration_ms=round(max(0.0, float(duration_ms)), 3),
        started_at=started_at,
        dimensions=dict(dimensions or {}),
    )
    (sink or get_use_case_telemetry_sink()).record(event)
    return event


@dataclass(frozen=True, slots=True)
class UseCaseTimer:
    """Simple timer helper for use-case telemetry instrumentation."""

    started_at: str
    start_perf_counter: float

    @classmethod
    def start(cls) -> UseCaseTimer:
        return cls(started_at=_utc_iso_now(), start_perf_counter=perf_counter())

    def duration_ms(self) -> float:
        return (perf_counter() - self.start_perf_counter) * 1000
