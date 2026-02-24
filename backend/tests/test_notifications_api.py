"""Tests for notifications API contract and behavior."""

from app.models import Notification, NotificationType


def test_notifications_list_returns_snake_case_type_values(client, auth_headers, db, test_user):
    """Notification API should expose canonical snake_case type values."""
    db.add_all(
        [
            Notification(
                user_id=test_user.id,
                type=NotificationType.DOCUMENT_CREATED,
                title="Document created",
                message="A document was created",
            ),
            Notification(
                user_id=test_user.id,
                type=NotificationType.REVIEW_SUBMITTED,
                title="Review submitted",
                message="A review is pending",
            ),
        ]
    )
    db.commit()

    response = client.get("/api/v1/notifications", headers=auth_headers)
    assert response.status_code == 200

    payload = response.json()
    type_values = {item["type"] for item in payload["items"]}
    assert "document_created" in type_values
    assert "review_submitted" in type_values
    assert payload["unread_count"] == 2


def test_notifications_count_endpoint_returns_unread_count(client, auth_headers, db, test_user):
    """Unread count endpoint should only include unread rows."""
    unread = Notification(
        user_id=test_user.id,
        type=NotificationType.SYSTEM,
        title="System alert",
        message="Unread",
        is_read=False,
    )
    read = Notification(
        user_id=test_user.id,
        type=NotificationType.SYSTEM,
        title="System alert",
        message="Read",
        is_read=True,
    )
    db.add_all([unread, read])
    db.commit()

    response = client.get("/api/v1/notifications/count", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["unread_count"] == 1
