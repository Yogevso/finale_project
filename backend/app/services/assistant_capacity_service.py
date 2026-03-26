"""Assistant admission control and saturation metrics."""

from __future__ import annotations

import asyncio
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from time import perf_counter
from typing import Literal

from app.config import settings
from app.infrastructure.degradation import DegradationPolicy, record_degradation

AssistantLaneName = Literal["chat", "embedding"]


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 3)
    index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * percentile))))
    return round(ordered[index], 3)


@dataclass(frozen=True, slots=True)
class AssistantLaneSnapshot:
    name: AssistantLaneName
    status: str
    active: int
    queued: int
    max_concurrent: int
    max_queue: int
    queue_timeout_seconds: float
    total_admitted: int
    total_completed: int
    total_rejected: int
    total_timed_out: int
    p50_duration_ms: float
    p95_duration_ms: float
    p50_queue_wait_ms: float
    p95_queue_wait_ms: float
    last_rejected_at: str | None = None
    last_rejection_reason: str | None = None


@dataclass(frozen=True, slots=True)
class AssistantCapacitySnapshot:
    status: str
    recorded_at: str
    chat: AssistantLaneSnapshot
    embedding: AssistantLaneSnapshot
    total_rejections: int
    total_timeouts: int


@dataclass(slots=True)
class _LaneRuntime:
    active: int = 0
    queued: int = 0
    total_admitted: int = 0
    total_completed: int = 0
    total_rejected: int = 0
    total_timed_out: int = 0
    durations_ms: deque[float] = field(default_factory=lambda: deque(maxlen=256))
    queue_wait_ms: deque[float] = field(default_factory=lambda: deque(maxlen=256))
    last_rejected_at: str | None = None
    last_rejection_reason: str | None = None


class AssistantCapacityExceeded(RuntimeError):
    """Raised when assistant capacity is exhausted."""

    def __init__(
        self,
        *,
        lane: AssistantLaneName,
        reason: str,
        retry_after_seconds: int,
    ) -> None:
        self.lane = lane
        self.reason = reason
        self.retry_after_seconds = retry_after_seconds
        if reason == "queue_full":
            message = f"Assistant {lane} capacity is saturated."
        else:
            message = f"Assistant {lane} queue wait timed out."
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class AssistantCapacityPermit:
    lane: AssistantLaneName
    queue_wait_ms: float
    started_at: float
    service: "AssistantCapacityService"
    released: bool = False

    async def release(self) -> None:
        if self.released:
            return
        object.__setattr__(self, "released", True)
        self.service._release(self.lane, started_at=self.started_at, queue_wait_ms=self.queue_wait_ms)


class AssistantCapacityService:
    """Process-wide admission control for assistant chat and embeddings."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._chat = _LaneRuntime()
        self._embedding = _LaneRuntime()

    def reset(self) -> None:
        with self._lock:
            self._chat = _LaneRuntime()
            self._embedding = _LaneRuntime()

    def _lane_runtime(self, lane: AssistantLaneName) -> _LaneRuntime:
        return self._chat if lane == "chat" else self._embedding

    def _lane_limits(self, lane: AssistantLaneName) -> tuple[int, int, float]:
        if lane == "chat":
            return (
                max(1, int(settings.ASSISTANT_CHAT_MAX_CONCURRENT)),
                max(0, int(settings.ASSISTANT_CHAT_MAX_QUEUE)),
                max(0.1, float(settings.ASSISTANT_CHAT_QUEUE_TIMEOUT_SECONDS)),
            )
        return (
            max(1, int(settings.ASSISTANT_EMBEDDING_MAX_CONCURRENT)),
            max(0, int(settings.ASSISTANT_EMBEDDING_MAX_QUEUE)),
            max(0.1, float(settings.ASSISTANT_EMBEDDING_QUEUE_TIMEOUT_SECONDS)),
        )

    async def acquire(self, lane: AssistantLaneName) -> AssistantCapacityPermit:
        max_concurrent, max_queue, queue_timeout_seconds = self._lane_limits(lane)
        runtime = self._lane_runtime(lane)
        queued = False
        queue_started_at = perf_counter()

        while True:
            with self._lock:
                if runtime.active < max_concurrent:
                    runtime.active += 1
                    runtime.total_admitted += 1
                    queue_wait_ms = (perf_counter() - queue_started_at) * 1000.0
                    runtime.queue_wait_ms.append(queue_wait_ms)
                    if queued:
                        runtime.queued = max(0, runtime.queued - 1)
                    return AssistantCapacityPermit(
                        lane=lane,
                        queue_wait_ms=round(queue_wait_ms, 3),
                        started_at=perf_counter(),
                        service=self,
                    )

                if not queued:
                    if runtime.queued >= max_queue:
                        runtime.total_rejected += 1
                        runtime.last_rejected_at = _utc_iso_now()
                        runtime.last_rejection_reason = "queue_full"
                        exc = AssistantCapacityExceeded(
                            lane=lane,
                            reason="queue_full",
                            retry_after_seconds=max(1, int(queue_timeout_seconds)),
                        )
                        record_degradation(
                            DegradationPolicy.FAIL_FAST,
                            f"assistant.{lane}.capacity",
                            exc,
                        )
                        raise exc
                    runtime.queued += 1
                    queued = True

                if perf_counter() - queue_started_at >= queue_timeout_seconds:
                    if queued:
                        runtime.queued = max(0, runtime.queued - 1)
                    runtime.total_rejected += 1
                    runtime.total_timed_out += 1
                    runtime.last_rejected_at = _utc_iso_now()
                    runtime.last_rejection_reason = "queue_timeout"
                    exc = AssistantCapacityExceeded(
                        lane=lane,
                        reason="queue_timeout",
                        retry_after_seconds=max(1, int(queue_timeout_seconds)),
                    )
                    record_degradation(
                        DegradationPolicy.FAIL_FAST,
                        f"assistant.{lane}.capacity",
                        exc,
                    )
                    raise exc

            await asyncio.sleep(0.01)

    def _release(
        self,
        lane: AssistantLaneName,
        *,
        started_at: float,
        queue_wait_ms: float,
    ) -> None:
        runtime = self._lane_runtime(lane)
        duration_ms = (perf_counter() - started_at) * 1000.0
        with self._lock:
            runtime.active = max(0, runtime.active - 1)
            runtime.total_completed += 1
            runtime.durations_ms.append(duration_ms)

    def snapshot(self) -> AssistantCapacitySnapshot:
        with self._lock:
            chat = self._build_lane_snapshot("chat", self._chat)
            embedding = self._build_lane_snapshot("embedding", self._embedding)
            status = "ready"
            if chat.status == "saturated" or embedding.status == "saturated":
                status = "saturated"
            elif chat.status == "busy" or embedding.status == "busy":
                status = "busy"
            return AssistantCapacitySnapshot(
                status=status,
                recorded_at=_utc_iso_now(),
                chat=chat,
                embedding=embedding,
                total_rejections=chat.total_rejected + embedding.total_rejected,
                total_timeouts=chat.total_timed_out + embedding.total_timed_out,
            )

    def _build_lane_snapshot(
        self,
        lane: AssistantLaneName,
        runtime: _LaneRuntime,
    ) -> AssistantLaneSnapshot:
        max_concurrent, max_queue, queue_timeout_seconds = self._lane_limits(lane)
        status = "idle"
        if runtime.active > 0 or runtime.queued > 0:
            status = "busy"
        if runtime.active >= max_concurrent and runtime.queued >= max_queue:
            status = "saturated"
        return AssistantLaneSnapshot(
            name=lane,
            status=status,
            active=runtime.active,
            queued=runtime.queued,
            max_concurrent=max_concurrent,
            max_queue=max_queue,
            queue_timeout_seconds=queue_timeout_seconds,
            total_admitted=runtime.total_admitted,
            total_completed=runtime.total_completed,
            total_rejected=runtime.total_rejected,
            total_timed_out=runtime.total_timed_out,
            p50_duration_ms=_percentile(list(runtime.durations_ms), 0.50),
            p95_duration_ms=_percentile(list(runtime.durations_ms), 0.95),
            p50_queue_wait_ms=_percentile(list(runtime.queue_wait_ms), 0.50),
            p95_queue_wait_ms=_percentile(list(runtime.queue_wait_ms), 0.95),
            last_rejected_at=runtime.last_rejected_at,
            last_rejection_reason=runtime.last_rejection_reason,
        )


_assistant_capacity_service = AssistantCapacityService()


def get_assistant_capacity_service() -> AssistantCapacityService:
    return _assistant_capacity_service


def reset_assistant_capacity_service() -> None:
    _assistant_capacity_service.reset()


async def acquire_assistant_chat_slot() -> AssistantCapacityPermit:
    return await _assistant_capacity_service.acquire("chat")


async def acquire_assistant_embedding_slot() -> AssistantCapacityPermit:
    return await _assistant_capacity_service.acquire("embedding")


@asynccontextmanager
async def assistant_embedding_slot():
    permit = await acquire_assistant_embedding_slot()
    try:
        yield permit
    finally:
        await permit.release()
