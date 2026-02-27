"""Tests for persisted domain-event outbox dispatch and worker processing."""

from __future__ import annotations

from app.domain.events import (
    CommentCreated,
    DocumentPublished,
    InProcessDomainEventDispatcher,
)
from app.models import DomainEventOutbox
from app.services.outbox import (
    OUTBOX_STATUS_DISPATCHED,
    OUTBOX_STATUS_FAILED,
    OUTBOX_STATUS_PENDING,
    build_outbox_event_dispatcher,
    list_dead_letter_outbox_entries,
    process_pending_outbox_events_once,
    requeue_dead_letter_outbox_entry,
)


def test_outbox_dispatcher_persists_pending_event(db):
    dispatcher = build_outbox_event_dispatcher(db)

    dispatcher.dispatch(
        DocumentPublished(
            document_id=101,
            version_id=7,
            document_title="Published Spec",
            document_number="DOC-OUT-001",
            document_url="http://localhost/viewer/documents/101",
            document_author_id=2,
            published_by_user_id=1,
        )
    )
    db.commit()

    row = db.query(DomainEventOutbox).one()
    assert row.event_type == "DocumentPublished"
    assert row.status == OUTBOX_STATUS_PENDING
    assert row.event_key == "document_published:7"


def test_outbox_dispatcher_event_key_is_idempotent(db):
    dispatcher = build_outbox_event_dispatcher(db)
    event = CommentCreated(
        document_id=200,
        document_title="Comment Doc",
        document_url="http://localhost/documents/200?tab=comments&comment=55",
        document_author_id=8,
        comment_id=55,
        comment_content="hello",
        commenter_user_id=3,
        commenter_display_name="Tester",
        parent_comment_author_id=None,
        is_private=False,
        has_anchor=False,
    )

    dispatcher.dispatch(event)
    dispatcher.dispatch(event)
    db.commit()

    assert db.query(DomainEventOutbox).count() == 1
    row = db.query(DomainEventOutbox).first()
    assert row.event_key == "comment_created:55"


def test_outbox_worker_dispatches_and_marks_processed(db):
    recorded: list[DocumentPublished] = []
    handler_dispatcher = InProcessDomainEventDispatcher(
        suppress_handler_exceptions=False
    )
    handler_dispatcher.register(DocumentPublished, lambda event: recorded.append(event))

    outbox_dispatcher = build_outbox_event_dispatcher(db)
    outbox_dispatcher.dispatch(
        DocumentPublished(
            document_id=303,
            version_id=9,
            document_title="Worker Doc",
            document_number="DOC-OUT-303",
            document_url="http://localhost/viewer/documents/303",
            document_author_id=10,
            published_by_user_id=11,
        )
    )
    db.commit()

    processed = process_pending_outbox_events_once(
        db=db,
        batch_size=10,
        retry_delay_seconds=0,
        handler_dispatcher=handler_dispatcher,
    )

    assert processed == 1
    row = db.query(DomainEventOutbox).one()
    assert row.status == OUTBOX_STATUS_DISPATCHED
    assert row.processed_at is not None
    assert len(recorded) == 1
    assert recorded[0].document_id == 303


def test_outbox_worker_retries_then_marks_failed(db):
    failing_dispatcher = InProcessDomainEventDispatcher(
        suppress_handler_exceptions=False
    )

    def _always_fail(_event: CommentCreated) -> None:
        raise RuntimeError("forced handler failure")

    failing_dispatcher.register(CommentCreated, _always_fail)

    outbox_dispatcher = build_outbox_event_dispatcher(db)
    outbox_dispatcher.dispatch(
        CommentCreated(
            document_id=404,
            document_title="Retry Doc",
            document_url="http://localhost/documents/404?tab=comments&comment=99",
            document_author_id=1,
            comment_id=99,
            comment_content="retry me",
            commenter_user_id=2,
            commenter_display_name="Retry User",
            parent_comment_author_id=None,
            is_private=False,
            has_anchor=False,
        )
    )
    row = db.query(DomainEventOutbox).one()
    row.max_attempts = 2
    db.commit()

    first = process_pending_outbox_events_once(
        db=db,
        batch_size=1,
        retry_delay_seconds=0,
        handler_dispatcher=failing_dispatcher,
    )
    db.refresh(row)
    assert first == 0
    assert row.status == OUTBOX_STATUS_PENDING
    assert row.attempts == 1

    second = process_pending_outbox_events_once(
        db=db,
        batch_size=1,
        retry_delay_seconds=0,
        handler_dispatcher=failing_dispatcher,
    )
    db.refresh(row)
    assert second == 0
    assert row.status == OUTBOX_STATUS_FAILED
    assert row.attempts == 2
    assert row.processed_at is not None


def test_outbox_dead_letter_entries_are_listed_and_requeueable(db):
    outbox_dispatcher = build_outbox_event_dispatcher(db)
    outbox_dispatcher.dispatch(
        DocumentPublished(
            document_id=909,
            version_id=44,
            document_title="DLQ Document",
            document_number="DOC-DLQ-909",
            document_url="http://localhost/viewer/documents/909",
            document_author_id=1,
            published_by_user_id=2,
        )
    )
    row = db.query(DomainEventOutbox).one()
    row.status = OUTBOX_STATUS_FAILED
    row.last_error = "[DLQ:attempt_limit_reached(5/5)] forced failure"
    db.commit()

    failed_rows = list_dead_letter_outbox_entries(db=db, limit=10)
    assert len(failed_rows) == 1
    assert failed_rows[0].id == row.id

    requeued = requeue_dead_letter_outbox_entry(row.id, db=db, reset_attempts=True)
    assert requeued is True
    db.refresh(row)
    assert row.status == OUTBOX_STATUS_PENDING
    assert row.last_error is None
    assert row.attempts == 0
