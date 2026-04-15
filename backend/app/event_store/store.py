"""Minimal append-only event store primitives for pilot use-cases."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    """One immutable event persisted in an event stream."""

    stream_id: str
    stream_version: int
    event_type: str
    payload: dict[str, Any]
    occurred_at: str
    metadata: dict[str, str] = field(default_factory=dict)


class OptimisticConcurrencyError(RuntimeError):
    """Raised when an append uses a stale expected stream version."""


class InMemoryEventStore:
    """Thread-safe in-memory event store with optimistic concurrency checks."""

    def __init__(self) -> None:
        self._streams: dict[str, list[EventEnvelope]] = {}
        self._lock = Lock()

    def append(
        self,
        *,
        stream_id: str,
        event_type: str,
        payload: dict[str, Any],
        expected_version: int | None = None,
        metadata: dict[str, str] | None = None,
        occurred_at: str | None = None,
    ) -> EventEnvelope:
        with self._lock:
            stream = self._streams.setdefault(stream_id, [])
            current_version = len(stream)
            if expected_version is not None and int(expected_version) != current_version:
                raise OptimisticConcurrencyError(
                    f"Expected version {expected_version} for {stream_id}, "
                    f"found {current_version}"
                )

            envelope = EventEnvelope(
                stream_id=stream_id,
                stream_version=current_version + 1,
                event_type=event_type,
                payload=dict(payload),
                occurred_at=occurred_at or _utc_iso_now(),
                metadata={str(k): str(v) for k, v in dict(metadata or {}).items()},
            )
            stream.append(envelope)
            return envelope

    def read_stream(self, stream_id: str) -> list[EventEnvelope]:
        with self._lock:
            return list(self._streams.get(stream_id, []))

    def stream_version(self, stream_id: str) -> int:
        with self._lock:
            return len(self._streams.get(stream_id, []))

    def clear(self) -> None:
        with self._lock:
            self._streams.clear()


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()
