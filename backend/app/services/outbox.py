"""Outbox persistence and worker processing for domain events."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.domain.events import (
    CommentCreated,
    DocumentPublished,
    DomainEvent,
    InProcessDomainEventDispatcher,
)
from app.jobs import (
    AsyncJobBatchReport,
    AsyncJobDisposition,
    RetryDecision,
    RetryPolicy,
    evaluate_retry,
    run_polling_worker,
)
from app.models import DomainEventOutbox
from app.repositories import OutboxRepository

logger = logging.getLogger(__name__)

OUTBOX_STATUS_PENDING = "pending"
OUTBOX_STATUS_PROCESSING = "processing"
OUTBOX_STATUS_DISPATCHED = "dispatched"
OUTBOX_STATUS_FAILED = "failed"
OUTBOX_WORKER_NAME = "outbox"


class DomainEventSerializer:
    """Serialize/deserialize domain events for outbox storage."""

    _event_types: dict[str, type[DomainEvent]] = {
        "DocumentPublished": DocumentPublished,
        "CommentCreated": CommentCreated,
    }

    @classmethod
    def serialize(cls, event: DomainEvent) -> tuple[str, str]:
        payload = asdict(event)
        payload["occurred_at"] = event.occurred_at.isoformat()
        return type(event).__name__, json.dumps(payload)

    @classmethod
    def deserialize(cls, event_type: str, payload_json: str) -> DomainEvent:
        event_cls = cls._event_types[event_type]
        payload = json.loads(payload_json)
        payload["occurred_at"] = datetime.fromisoformat(payload["occurred_at"])
        return event_cls(**payload)

    @staticmethod
    def event_key_for(event: DomainEvent) -> str | None:
        if isinstance(event, DocumentPublished):
            return f"document_published:{event.version_id}"
        if isinstance(event, CommentCreated):
            return f"comment_created:{event.comment_id}"
        return None


class OutboxDomainEventDispatcher:
    """Event dispatcher that persists domain events to outbox."""

    def __init__(
        self,
        db: Session,
        *,
        serializer: type[DomainEventSerializer] = DomainEventSerializer,
    ) -> None:
        self.db = db
        self._serializer = serializer
        self._repository = OutboxRepository(db)

    def dispatch(self, event: DomainEvent) -> None:
        event_type, payload_json = self._serializer.serialize(event)
        event_key = self._serializer.event_key_for(event)
        self._repository.enqueue(
            event_type=event_type,
            payload_json=payload_json,
            event_key=event_key,
        )


def build_outbox_event_dispatcher(db: Session) -> OutboxDomainEventDispatcher:
    """Factory for services that should persist emitted events to outbox."""

    return OutboxDomainEventDispatcher(db)


def _mark_dispatched(row: DomainEventOutbox, *, now: datetime) -> None:
    row.status = OUTBOX_STATUS_DISPATCHED
    row.processed_at = now
    row.claimed_at = None
    row.next_attempt_at = None
    row.last_error = None


def _mark_retry_or_failed(
    row: DomainEventOutbox,
    *,
    now: datetime,
    error: str,
    retry_policy: RetryPolicy,
) -> RetryDecision:
    decision = evaluate_retry(
        attempts=int(row.attempts or 0),
        max_attempts=int(row.max_attempts or 5),
        error=error,
        policy=retry_policy,
    )
    row.claimed_at = None

    if decision.disposition == AsyncJobDisposition.DEAD_LETTER:
        row.status = OUTBOX_STATUS_FAILED
        row.processed_at = now
        row.next_attempt_at = None
        row.last_error = f"[DLQ:{decision.reason}] {error}"
        return decision

    row.last_error = error
    row.status = OUTBOX_STATUS_PENDING
    row.next_attempt_at = now + timedelta(seconds=max(0, int(decision.next_delay_seconds or 0)))
    return decision


def process_pending_outbox_events_batch(
    *,
    batch_size: int = 20,
    retry_delay_seconds: int = 30,
    retry_policy: RetryPolicy | None = None,
    db: Session | None = None,
    handler_dispatcher: InProcessDomainEventDispatcher | None = None,
) -> AsyncJobBatchReport:
    """Process one outbox batch and return detailed worker counters."""

    owns_session = db is None
    session = db or SessionLocal()
    report = AsyncJobBatchReport(worker_name=OUTBOX_WORKER_NAME)
    policy = retry_policy or RetryPolicy(
        base_delay_seconds=max(0, int(retry_delay_seconds)),
        max_delay_seconds=max(0, int(retry_delay_seconds)) * 10 or 300,
        backoff_multiplier=2.0,
    )
    try:
        from app.services.domain_event_handlers import build_domain_event_dispatcher

        repository = OutboxRepository(session)
        side_effect_dispatcher = handler_dispatcher or build_domain_event_dispatcher(
            session,
            suppress_handler_exceptions=False,
        )
        now = datetime.utcnow()
        candidate_ids = repository.list_runnable_pending_ids(limit=batch_size, now=now)

        for outbox_id in candidate_ids:
            claimed_now = datetime.utcnow()
            if not repository.claim_pending(outbox_id=outbox_id, now=claimed_now):
                report.skipped += 1
                continue
            session.commit()

            row = repository.get_by_id(outbox_id)
            if not row:
                report.skipped += 1
                continue
            report.attempted += 1

            try:
                event = DomainEventSerializer.deserialize(row.event_type, row.payload_json)
                side_effect_dispatcher.dispatch(event)
                _mark_dispatched(row, now=datetime.utcnow())
                session.commit()
                report.completed += 1
            except Exception as exc:
                decision = _mark_retry_or_failed(
                    row,
                    now=datetime.utcnow(),
                    error=str(exc),
                    retry_policy=policy,
                )
                session.commit()
                if decision.disposition == AsyncJobDisposition.DEAD_LETTER:
                    report.dead_lettered += 1
                elif decision.disposition == AsyncJobDisposition.RETRY:
                    report.retried += 1
                else:
                    report.skipped += 1

        return report
    finally:
        if owns_session:
            session.close()


def process_pending_outbox_events_once(
    *,
    batch_size: int = 20,
    retry_delay_seconds: int = 30,
    retry_policy: RetryPolicy | None = None,
    db: Session | None = None,
    handler_dispatcher: InProcessDomainEventDispatcher | None = None,
) -> int:
    """Compatibility wrapper returning dispatched (completed) count only."""
    report = process_pending_outbox_events_batch(
        batch_size=batch_size,
        retry_delay_seconds=retry_delay_seconds,
        retry_policy=retry_policy,
        db=db,
        handler_dispatcher=handler_dispatcher,
    )
    return report.completed


def list_dead_letter_outbox_entries(
    *,
    limit: int = 100,
    db: Session | None = None,
) -> list[DomainEventOutbox]:
    """List outbox rows currently parked in DLQ/failed state."""
    owns_session = db is None
    session = db or SessionLocal()
    try:
        return (
            session.query(DomainEventOutbox)
            .filter(DomainEventOutbox.status == OUTBOX_STATUS_FAILED)
            .order_by(DomainEventOutbox.processed_at.desc(), DomainEventOutbox.id.desc())
            .limit(max(1, int(limit)))
            .all()
        )
    finally:
        if owns_session:
            session.close()


def requeue_dead_letter_outbox_entry(
    outbox_id: int,
    *,
    reset_attempts: bool = False,
    db: Session | None = None,
) -> bool:
    """Requeue one DLQ outbox record for operator-driven recovery."""
    owns_session = db is None
    session = db or SessionLocal()
    try:
        row = (
            session.query(DomainEventOutbox)
            .filter(
                DomainEventOutbox.id == outbox_id,
                DomainEventOutbox.status == OUTBOX_STATUS_FAILED,
            )
            .first()
        )
        if not row:
            return False

        row.status = OUTBOX_STATUS_PENDING
        row.claimed_at = None
        row.next_attempt_at = None
        row.processed_at = None
        row.last_error = None
        if reset_attempts:
            row.attempts = 0
        session.commit()
        return True
    finally:
        if owns_session:
            session.close()


def run_outbox_worker(
    *,
    poll_interval_seconds: float = 2.0,
    batch_size: int = 20,
    retry_delay_seconds: int = 30,
    once: bool = False,
) -> None:
    """Run durable outbox worker loop."""
    policy = RetryPolicy(
        base_delay_seconds=max(0, int(retry_delay_seconds)),
        max_delay_seconds=max(0, int(retry_delay_seconds)) * 10 or 300,
        backoff_multiplier=2.0,
    )
    run_polling_worker(
        worker_name=OUTBOX_WORKER_NAME,
        logger=logger,
        poll_interval_seconds=poll_interval_seconds,
        batch_size=batch_size,
        once=once,
        process_batch=lambda size: process_pending_outbox_events_batch(
            batch_size=size,
            retry_policy=policy,
        ),
    )
