"""Regression coverage for customer-feedback queue filtering."""

from app.models import (
    DocumentStatus,
    DocumentVisibility,
    Feedback,
    FeedbackStatus,
    FeedbackType,
    UserRole,
)
from tests.factories import create_document, create_user


def _login_headers(client, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_management_feedback_queue_excludes_engagement_ratings(
    client,
    db,
    test_tenant,
    test_customer,
):
    manager = create_user(
        db,
        email="queue-manager@testcompany.com",
        username="queue_manager",
        full_name="Queue Manager",
        plain_password="manager123",
        role=UserRole.MANAGER,
        tenant_id=test_tenant.id,
        is_active=True,
    )
    manager_headers = _login_headers(client, manager.username, "manager123")
    document = create_document(
        db,
        title="Queue Filter Guide",
        document_number="DOC-QF-001",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.PUBLIC,
        created_by=manager.id,
        tenant_id=test_tenant.id,
    )

    customer_feedback = Feedback(
        user_id=test_customer.id,
        document_id=document.id,
        feedback_type=FeedbackType.QUESTION,
        status=FeedbackStatus.PENDING,
        content="Please clarify the rollback section.",
    )
    engagement_feedback = Feedback(
        user_id=test_customer.id,
        document_id=document.id,
        feedback_type=FeedbackType.OTHER,
        status=FeedbackStatus.PENDING,
        content="Helpful document",
        comment="Helpful document",
        is_helpful=True,
    )
    db.add_all([customer_feedback, engagement_feedback])
    db.commit()

    list_response = client.get("/api/v1/feedback", headers=manager_headers)
    assert list_response.status_code == 200
    payload = list_response.json()
    assert [item["id"] for item in payload["items"]] == [customer_feedback.id]

    stats_response = client.get("/api/v1/feedback/stats/summary", headers=manager_headers)
    assert stats_response.status_code == 200
    assert stats_response.json()["total"] == 1
    assert stats_response.json()["pending"] == 1


def test_portal_feedback_history_excludes_engagement_ratings(
    client,
    db,
    customer_headers,
    test_customer,
    test_tenant,
):
    manager = create_user(
        db,
        email="portal-feedback-manager@testcompany.com",
        username="portal_feedback_manager",
        full_name="Portal Feedback Manager",
        plain_password="manager123",
        role=UserRole.MANAGER,
        tenant_id=test_tenant.id,
        is_active=True,
    )
    document = create_document(
        db,
        title="Portal Feedback Guide",
        document_number="DOC-QF-002",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.PUBLIC,
        created_by=manager.id,
        tenant_id=test_tenant.id,
    )

    customer_feedback = Feedback(
        user_id=test_customer.id,
        document_id=document.id,
        feedback_type=FeedbackType.SUGGESTION,
        status=FeedbackStatus.PENDING,
        content="Add a practical example to the import section.",
    )
    engagement_feedback = Feedback(
        user_id=test_customer.id,
        document_id=document.id,
        feedback_type=FeedbackType.OTHER,
        status=FeedbackStatus.PENDING,
        content="Feedback submitted",
        comment="Helpful document",
        is_helpful=False,
    )
    db.add_all([customer_feedback, engagement_feedback])
    db.commit()

    list_response = client.get("/api/v1/portal/feedback", headers=customer_headers)
    assert list_response.status_code == 200
    payload = list_response.json()
    assert [item["id"] for item in payload["items"]] == [customer_feedback.id]

    detail_response = client.get(
        f"/api/v1/portal/feedback/{engagement_feedback.id}",
        headers=customer_headers,
    )
    assert detail_response.status_code == 404
