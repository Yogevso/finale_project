"""Repository for persisted domain-event outbox records."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_

from app.models import DomainEventOutbox
from app.repositories.base import BaseRepository


class OutboxRepository(BaseRepository):
    """Persistence/query helpers for domain-event outbox entries."""

    def get_by_id(self, outbox_id: int) -> DomainEventOutbox | None:
        return (
            self.db.query(DomainEventOutbox)
            .filter(DomainEventOutbox.id == outbox_id)
            .first()
        )

    def get_by_event_key(self, event_key: str) -> DomainEventOutbox | None:
        return (
            self.db.query(DomainEventOutbox)
            .filter(DomainEventOutbox.event_key == event_key)
            .first()
        )

    def enqueue(
        self,
        *,
        event_type: str,
        payload_json: str,
        event_key: str | None,
        max_attempts: int = 5,
    ) -> DomainEventOutbox:
        if event_key:
            existing = self.get_by_event_key(event_key)
            if existing:
                return existing

        row = DomainEventOutbox(
            event_type=event_type,
            event_key=event_key,
            payload_json=payload_json,
            status="pending",
            attempts=0,
            max_attempts=max_attempts,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def list_runnable_pending_ids(self, *, limit: int, now: datetime) -> list[int]:
        rows = (
            self.db.query(DomainEventOutbox.id)
            .filter(
                DomainEventOutbox.status == "pending",
                or_(
                    DomainEventOutbox.next_attempt_at.is_(None),
                    DomainEventOutbox.next_attempt_at <= now,
                ),
            )
            .order_by(DomainEventOutbox.created_at.asc(), DomainEventOutbox.id.asc())
            .limit(limit)
            .all()
        )
        return [row[0] for row in rows]

    def claim_pending(self, *, outbox_id: int, now: datetime) -> bool:
        updated = (
            self.db.query(DomainEventOutbox)
            .filter(
                DomainEventOutbox.id == outbox_id,
                DomainEventOutbox.status == "pending",
                or_(
                    DomainEventOutbox.next_attempt_at.is_(None),
                    DomainEventOutbox.next_attempt_at <= now,
                ),
            )
            .update(
                {
                    DomainEventOutbox.status: "processing",
                    DomainEventOutbox.claimed_at: now,
                    DomainEventOutbox.last_error: None,
                    DomainEventOutbox.next_attempt_at: None,
                    DomainEventOutbox.attempts: DomainEventOutbox.attempts + 1,
                },
                synchronize_session=False,
            )
        )
        return updated == 1
