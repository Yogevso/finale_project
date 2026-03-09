"""Integration tests for approval SLA reminder and escalation processing."""

from datetime import datetime, timedelta

from app.models import Notification, NotificationType, ReviewRequest, UserRole
from tests.factories import create_user


def test_review_sla_reminder_generates_notification(
    client,
    db,
    auth_headers,
    manager_headers,
    test_document,
):
    reviewer = create_user(
        db,
        email="reviewer-sla@example.com",
        username="reviewer_sla",
        full_name="Reviewer SLA",
        role=UserRole.EDITOR,
    )

    submit_response = client.post(
        f"/api/v1/reviews/documents/{test_document.id}/submit",
        headers=auth_headers,
        json={"message": "Please review within SLA"},
    )
    assert submit_response.status_code in [200, 201]
    review_id = submit_response.json()["id"]

    review = db.query(ReviewRequest).filter(ReviewRequest.id == review_id).first()
    assert review is not None
    review.submitted_at = datetime.utcnow() - timedelta(hours=49)
    db.commit()

    response = client.post("/api/v1/reviews/sla/process", headers=manager_headers)
    assert response.status_code == 200
    payload = response.json()

    assert payload["reminders_sent"] == 1
    assert payload["escalations_sent"] == 0
    assert payload["items"][0]["review_id"] == review_id
    assert payload["items"][0]["reminder_recipient_ids"] == [reviewer.id]

    reminder_notifications = (
        db.query(Notification)
        .filter(
            Notification.user_id == reviewer.id,
            Notification.type == NotificationType.REVIEW_REMINDER,
        )
        .all()
    )
    assert len(reminder_notifications) == 1

    db.refresh(review)
    assert review.reviewer_reminded_at is not None
    assert review.manager_escalated_at is None


def test_review_sla_escalation_only_runs_once(
    client,
    db,
    auth_headers,
    manager_headers,
    test_document,
):
    secondary_manager = create_user(
        db,
        email="manager-sla@example.com",
        username="manager_sla",
        full_name="Manager SLA",
        role=UserRole.MANAGER,
    )

    submit_response = client.post(
        f"/api/v1/reviews/documents/{test_document.id}/submit",
        headers=auth_headers,
        json={"message": "Escalation path"},
    )
    assert submit_response.status_code in [200, 201]
    review_id = submit_response.json()["id"]

    review = db.query(ReviewRequest).filter(ReviewRequest.id == review_id).first()
    assert review is not None
    review.submitted_at = datetime.utcnow() - timedelta(hours=97)
    db.commit()

    first_run = client.post("/api/v1/reviews/sla/process", headers=manager_headers)
    assert first_run.status_code == 200
    first_payload = first_run.json()

    assert first_payload["reminders_sent"] == 1
    assert first_payload["escalations_sent"] == 1
    assert first_payload["items"][0]["escalation_recipient_ids"] == [secondary_manager.id]

    escalation_notifications = (
        db.query(Notification)
        .filter(
            Notification.user_id == secondary_manager.id,
            Notification.type == NotificationType.REVIEW_ESCALATED,
        )
        .all()
    )
    assert len(escalation_notifications) == 1

    second_run = client.post("/api/v1/reviews/sla/process", headers=manager_headers)
    assert second_run.status_code == 200
    second_payload = second_run.json()
    assert second_payload["reminders_sent"] == 0
    assert second_payload["escalations_sent"] == 0
    assert second_payload["items"] == []

    db.refresh(review)
    assert review.reviewer_reminded_at is not None
    assert review.manager_escalated_at is not None
