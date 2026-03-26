"""Tests for persisted domain-event outbox dispatch and worker processing."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.config import settings
from app.domain.events import (
    CommentChatBridgeRequested,
    CommentCreated,
    CompanyAssignmentsUpdated,
    DocumentPublished,
    InProcessDomainEventDispatcher,
)
from app.models import DomainEventOutbox, Notification, NotificationType, User, UserRole
from app.security import get_password_hash
from app.services.outbox import (
    OUTBOX_STATUS_DEAD_LETTER,
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


def test_outbox_dispatcher_comment_chat_bridge_event_key_is_idempotent(db):
    dispatcher = build_outbox_event_dispatcher(db)
    event = CommentChatBridgeRequested(
        document_id=200,
        comment_id=55,
        document_author_id=8,
        commenter_user_id=3,
        commenter_display_name="Tester",
    )

    dispatcher.dispatch(event)
    dispatcher.dispatch(event)
    db.commit()

    assert db.query(DomainEventOutbox).count() == 1
    row = db.query(DomainEventOutbox).first()
    assert row.event_type == "CommentChatBridgeRequested"
    assert row.event_key == "comment_chat_bridge_requested:55"


def test_assignment_outbox_event_uses_configured_max_attempts(db, monkeypatch):
    monkeypatch.setattr(settings, "ASSIGNMENT_JOB_MAX_ATTEMPTS", 5)
    dispatcher = build_outbox_event_dispatcher(db)
    dispatcher.dispatch(
        CompanyAssignmentsUpdated(
            document_id=700,
            document_row_version=9,
            assigned_company_ids=(12, 13),
            actor_user_id=5,
        )
    )
    db.commit()

    row = db.query(DomainEventOutbox).one()
    assert row.event_type == "CompanyAssignmentsUpdated"
    assert row.max_attempts == 5
    assert row.event_key == "company_assignments_updated:700:9"


def test_assignment_outbox_retry_uses_assignment_policy_over_retry_delay_override(
    db,
    monkeypatch,
):
    monkeypatch.setattr(settings, "ASSIGNMENT_JOB_RETRY_BASE_DELAY_SECONDS", 12)
    monkeypatch.setattr(settings, "ASSIGNMENT_JOB_RETRY_MAX_DELAY_SECONDS", 12)
    monkeypatch.setattr(settings, "ASSIGNMENT_JOB_RETRY_BACKOFF_MULTIPLIER", 2.0)
    monkeypatch.setattr(settings, "ASSIGNMENT_JOB_RETRY_JITTER_RATIO", 0.0)

    failing_dispatcher = InProcessDomainEventDispatcher(
        suppress_handler_exceptions=False
    )

    def _always_fail_assignment_event(_event: CompanyAssignmentsUpdated) -> None:
        raise RuntimeError("forced assignment event failure")

    failing_dispatcher.register(CompanyAssignmentsUpdated, _always_fail_assignment_event)

    outbox_dispatcher = build_outbox_event_dispatcher(db)
    outbox_dispatcher.dispatch(
        CompanyAssignmentsUpdated(
            document_id=711,
            document_row_version=1,
            assigned_company_ids=(5, 8),
            actor_user_id=None,
        )
    )
    db.commit()

    before_retry_window = datetime.utcnow()
    process_pending_outbox_events_once(
        db=db,
        batch_size=1,
        retry_delay_seconds=0,
        handler_dispatcher=failing_dispatcher,
    )

    row = db.query(DomainEventOutbox).one()
    assert row.status == OUTBOX_STATUS_PENDING
    assert row.next_attempt_at is not None
    assert row.next_attempt_at >= before_retry_window + timedelta(seconds=8)


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


def test_assignment_event_dead_letter_emits_admin_notification(db, monkeypatch):
    monkeypatch.setattr(settings, "ASSIGNMENT_JOB_MAX_ATTEMPTS", 5)
    monkeypatch.setattr(settings, "ASSIGNMENT_JOB_RETRY_BASE_DELAY_SECONDS", 0)
    monkeypatch.setattr(settings, "ASSIGNMENT_JOB_RETRY_MAX_DELAY_SECONDS", 0)
    monkeypatch.setattr(settings, "ASSIGNMENT_JOB_RETRY_BACKOFF_MULTIPLIER", 2.0)
    monkeypatch.setattr(settings, "ASSIGNMENT_JOB_RETRY_JITTER_RATIO", 0.0)

    admin_user = User(
        email="outbox-admin@example.com",
        username="outbox_admin",
        full_name="Outbox Admin",
        hashed_password=get_password_hash("outbox-admin-pass-123"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin_user)
    db.commit()

    failing_dispatcher = InProcessDomainEventDispatcher(
        suppress_handler_exceptions=False
    )

    def _always_fail_assignment_event(_event: CompanyAssignmentsUpdated) -> None:
        raise RuntimeError("forced assignment event failure")

    failing_dispatcher.register(CompanyAssignmentsUpdated, _always_fail_assignment_event)

    outbox_dispatcher = build_outbox_event_dispatcher(db)
    outbox_dispatcher.dispatch(
        CompanyAssignmentsUpdated(
            document_id=888,
            document_row_version=3,
            assigned_company_ids=(101, 102),
            actor_user_id=None,
        )
    )
    db.commit()

    row = db.query(DomainEventOutbox).one()
    assert row.max_attempts == 5

    for _ in range(5):
        processed = process_pending_outbox_events_once(
            db=db,
            batch_size=1,
            retry_delay_seconds=0,
            handler_dispatcher=failing_dispatcher,
        )
        assert processed == 0

    db.refresh(row)
    assert row.status == OUTBOX_STATUS_DEAD_LETTER
    assert row.attempts == 5
    assert row.last_error is not None
    assert "DLQ:attempt_limit_reached" in row.last_error

    notifications = (
        db.query(Notification)
        .filter(
            Notification.user_id == admin_user.id,
            Notification.type == NotificationType.SYSTEM,
        )
        .all()
    )
    assert len(notifications) == 1
    assert "dead letter queue" in notifications[0].title.lower()
