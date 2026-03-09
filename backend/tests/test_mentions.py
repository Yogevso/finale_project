"""Unit tests for mention extraction and notification fan-out."""

from app.models import Notification, NotificationType
from app.services.notification_service import NotificationService
from tests.factories import create_document, create_user


def test_extract_mentions_strips_html_and_deduplicates_usernames():
    mentions = NotificationService.extract_mentions(
        '<p>Hello <strong>@target_user</strong></p><p>@target_user and @second.user</p>'
    )

    assert mentions == ["target_user", "second.user"]


def test_notify_mentions_creates_notification_for_mentioned_user(db):
    author = create_user(
        db,
        email="mention-author@example.com",
        username="mention_author",
        full_name="Mention Author",
    )
    mentioned_user = create_user(
        db,
        email="mention-target@example.com",
        username="target_user",
        full_name="Mention Target",
    )
    document = create_document(
        db,
        created_by=author.id,
        title="Mention Ready Document",
        document_number="DOC-MENTION-001",
    )

    service = NotificationService(db)

    notified_ids = service.notify_mentions(
        content="<p>Please review this update @target_user</p>",
        actor_user=author,
        document=document,
        notification_type=NotificationType.COMMENT_ADDED,
        title_builder=lambda _user: "Mentioned in comment",
        message_builder=lambda _user: "Please review this update.",
        link=f"/documents/{document.id}?tab=comments",
    )
    db.commit()

    assert notified_ids == {mentioned_user.id}

    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == mentioned_user.id)
        .order_by(Notification.id.asc())
        .all()
    )

    assert len(notifications) == 1
    assert notifications[0].type == NotificationType.COMMENT_ADDED
    assert notifications[0].title == "Mentioned in comment"
    assert notifications[0].message == "Please review this update."
