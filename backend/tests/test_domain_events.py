"""Tests for domain-event dispatch and write-flow event emission."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.events import (
    CommentCreated,
    DocumentPublished,
    InProcessDomainEventDispatcher,
)
from app.models import (
    Comment,
    Document,
    DocumentStatus,
    ReviewRequest,
    ReviewStatus,
    User,
    UserRole,
    Version,
    VersionBumpType,
)
from app.schemas import CommentCreate
from app.services.comment_service import CommentService
from app.services.version_service import VersionService


@dataclass
class RecordingDispatcher:
    """Test helper to capture emitted domain events."""

    events: list[object] = field(default_factory=list)

    def dispatch(self, event: object) -> None:
        self.events.append(event)


def test_in_process_dispatcher_continues_after_handler_error():
    dispatcher = InProcessDomainEventDispatcher()
    handled: list[DocumentPublished] = []

    def failing_handler(_event: DocumentPublished) -> None:
        raise RuntimeError("boom")

    def successful_handler(event: DocumentPublished) -> None:
        handled.append(event)

    dispatcher.register(DocumentPublished, failing_handler)
    dispatcher.register(DocumentPublished, successful_handler)

    event = DocumentPublished(
        document_id=10,
        version_id=22,
        document_title="API Spec",
        document_number="DOC-API-001",
        document_url="http://localhost/documents/10",
        document_author_id=2,
        published_by_user_id=1,
    )
    dispatcher.dispatch(event)

    assert handled == [event]


def test_version_service_emits_document_published_event(db):
    author = User(
        email="author@example.com",
        username="author",
        full_name="Doc Author",
        hashed_password="hashed",
        role=UserRole.EDITOR,
        is_active=True,
    )
    publisher = User(
        email="manager@example.com",
        username="managerpub",
        full_name="Manager Publisher",
        hashed_password="hashed",
        role=UserRole.MANAGER,
        is_active=True,
    )
    db.add_all([author, publisher])
    db.commit()
    db.refresh(author)
    db.refresh(publisher)

    document = Document(
        title="Publishable Document",
        document_number="DOC-PUB-001",
        description="for events",
        status=DocumentStatus.APPROVED,
        created_by=author.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    version = Version(
        document_id=document.id,
        version_number=1,
        semantic_version="1.0.0",
        bump_type=VersionBumpType.PATCH,
        content="ready",
        changes_summary="init",
        is_published=False,
        created_by=author.id,
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    review = ReviewRequest(
        document_id=document.id,
        version_id=version.id,
        submitted_by=author.id,
        reviewed_by=publisher.id,
        status=ReviewStatus.APPROVED,
    )
    db.add(review)
    db.commit()

    dispatcher = RecordingDispatcher()
    service = VersionService(db, event_dispatcher=dispatcher)

    result = service.publish_version(document.id, version.id, publisher)
    db.refresh(document)

    assert result["is_published"] is True
    assert document.status == DocumentStatus.ACTIVE
    assert len(dispatcher.events) == 1
    event = dispatcher.events[0]
    assert isinstance(event, DocumentPublished)
    assert event.document_id == document.id
    assert event.document_author_id == author.id
    assert event.published_by_user_id == publisher.id


def test_comment_service_emits_comment_created_event(db):
    author = User(
        email="author-comment@example.com",
        username="authorcomment",
        full_name="Document Author",
        hashed_password="hashed",
        role=UserRole.EDITOR,
        is_active=True,
    )
    commenter = User(
        email="commenter@example.com",
        username="commenter",
        full_name="Comment Creator",
        hashed_password="hashed",
        role=UserRole.EDITOR,
        is_active=True,
    )
    db.add_all([author, commenter])
    db.commit()
    db.refresh(author)
    db.refresh(commenter)

    document = Document(
        title="Commented Document",
        document_number="DOC-COM-001",
        description="for events",
        status=DocumentStatus.DRAFT,
        created_by=author.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    parent = Comment(
        document_id=document.id,
        user_id=author.id,
        content="Parent thread",
    )
    db.add(parent)
    db.commit()
    db.refresh(parent)

    dispatcher = RecordingDispatcher()
    service = CommentService(db, event_dispatcher=dispatcher)

    created = service.create_comment(
        document.id,
        CommentCreate(
            content="Reply body",
            parent_id=parent.id,
            is_private=True,
            anchor_text="scope",
        ),
        commenter,
    )

    assert created.id is not None
    assert len(dispatcher.events) == 1
    event = dispatcher.events[0]
    assert isinstance(event, CommentCreated)
    assert event.document_id == document.id
    assert event.parent_comment_author_id == author.id
    assert event.commenter_user_id == commenter.id
    assert event.is_private is True
    assert event.has_anchor is True
