"""Feedback flow tests for direct feedback plus manual support escalation."""

from app.models import (
    DocumentStatus,
    DocumentVisibility,
    Feedback,
    Notification,
    NotificationType,
    SupportTicket,
    SupportTicketMessage,
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


def test_portal_feedback_submission_stays_in_feedback_queue(
    client,
    db,
    customer_headers,
    test_tenant,
):
    manager = create_user(
        db,
        email="feedback-manager@testcompany.com",
        username="feedback_manager",
        full_name="Feedback Manager",
        plain_password="manager123",
        role=UserRole.MANAGER,
        tenant_id=test_tenant.id,
        is_active=True,
    )
    document = create_document(
        db,
        title="Feedback Handbook",
        document_number="DOC-FB-001",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.PUBLIC,
        created_by=manager.id,
        tenant_id=test_tenant.id,
    )

    response = client.post(
        "/api/v1/portal/feedback",
        headers=customer_headers,
        json={
            "document_id": document.id,
            "feedback_type": "question",
            "content": "I need more detail in the troubleshooting steps.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ticket_id"] is None

    feedback = db.query(Feedback).filter(Feedback.id == payload["id"]).first()
    assert feedback is not None
    assert db.query(SupportTicket).filter(SupportTicket.feedback_id == feedback.id).first() is None

    notification = (
        db.query(Notification)
        .filter(Notification.user_id == manager.id)
        .order_by(Notification.id.desc())
        .first()
    )
    assert notification is not None
    assert notification.type == NotificationType.FEEDBACK_RECEIVED
    assert notification.link == f"/admin/feedback?feedback={feedback.id}"


def test_portal_feedback_submission_accepts_short_customer_feedback(
    client,
    db,
    customer_headers,
    test_tenant,
):
    manager = create_user(
        db,
        email="feedback-short@testcompany.com",
        username="feedback_short",
        full_name="Feedback Short",
        plain_password="manager123",
        role=UserRole.MANAGER,
        tenant_id=test_tenant.id,
        is_active=True,
    )
    document = create_document(
        db,
        title="Short Feedback Guide",
        document_number="DOC-FB-004",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.PUBLIC,
        created_by=manager.id,
        tenant_id=test_tenant.id,
    )

    response = client.post(
        "/api/v1/portal/feedback",
        headers=customer_headers,
        json={
            "document_id": document.id,
            "feedback_type": "question",
            "content": "u sure?",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["content"] == "u sure?"
    assert payload["ticket_id"] is None


def test_feedback_submission_notifies_document_contributors(
    client,
    db,
    customer_headers,
    test_tenant,
):
    editor = create_user(
        db,
        email="feedback-editor@testcompany.com",
        username="feedback_editor",
        full_name="Feedback Editor",
        plain_password="editor123",
        role=UserRole.EDITOR,
        tenant_id=test_tenant.id,
        is_active=True,
    )
    document = create_document(
        db,
        title="Contributor Manual",
        document_number="DOC-FB-003",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.PUBLIC,
        created_by=editor.id,
        tenant_id=test_tenant.id,
    )

    response = client.post(
        "/api/v1/portal/feedback",
        headers=customer_headers,
        json={
            "document_id": document.id,
            "feedback_type": "suggestion",
            "content": "Please add an example for the export process.",
        },
    )

    assert response.status_code == 200
    feedback_id = response.json()["id"]

    notification = (
        db.query(Notification)
        .filter(Notification.user_id == editor.id)
        .order_by(Notification.id.desc())
        .first()
    )
    assert notification is not None
    assert notification.type == NotificationType.FEEDBACK_RECEIVED
    assert notification.link == f"/admin/feedback?feedback={feedback_id}"


def test_feedback_response_stays_on_feedback_and_customer_can_view_it(
    client,
    db,
    customer_headers,
    test_customer,
    test_tenant,
):
    manager = create_user(
        db,
        email="feedback-manager-2@testcompany.com",
        username="feedback_manager_2",
        full_name="Feedback Manager Two",
        plain_password="manager123",
        role=UserRole.MANAGER,
        tenant_id=test_tenant.id,
        is_active=True,
    )
    manager_headers = _login_headers(client, manager.username, "manager123")
    document = create_document(
        db,
        title="Operations Runbook",
        document_number="DOC-FB-002",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.PUBLIC,
        created_by=manager.id,
        tenant_id=test_tenant.id,
    )

    submit_response = client.post(
        "/api/v1/portal/feedback",
        headers=customer_headers,
        json={
            "document_id": document.id,
            "feedback_type": "issue",
            "content": "The escalation section is missing the latest process.",
        },
    )
    assert submit_response.status_code == 200
    feedback_payload = submit_response.json()

    respond_response = client.post(
        f"/api/v1/feedback/{feedback_payload['id']}/respond",
        headers=manager_headers,
        json={"response": "Thanks. We updated the ticket thread with the next steps."},
    )
    assert respond_response.status_code == 200
    responded_payload = respond_response.json()
    assert responded_payload["status"] == "responded"
    assert responded_payload["ticket_id"] is None
    assert (
        responded_payload["response"] == "Thanks. We updated the ticket thread with the next steps."
    )

    assert (
        db.query(SupportTicket).filter(SupportTicket.feedback_id == feedback_payload["id"]).first()
        is None
    )

    portal_feedback_response = client.get(
        f"/api/v1/portal/feedback/{feedback_payload['id']}",
        headers=customer_headers,
    )
    assert portal_feedback_response.status_code == 200
    portal_feedback_payload = portal_feedback_response.json()
    assert portal_feedback_payload["ticket_id"] is None
    assert (
        portal_feedback_payload["response"]
        == "Thanks. We updated the ticket thread with the next steps."
    )

    customer_notification = (
        db.query(Notification)
        .filter(Notification.user_id == test_customer.id)
        .order_by(Notification.id.desc())
        .first()
    )
    assert customer_notification is not None
    assert customer_notification.type == NotificationType.FEEDBACK_RESPONDED
    assert customer_notification.link == f"/portal/feedback?feedback={feedback_payload['id']}"


def test_feedback_can_be_manually_escalated_to_support(
    client,
    db,
    customer_headers,
    test_tenant,
):
    manager = create_user(
        db,
        email="feedback-manager-3@testcompany.com",
        username="feedback_manager_3",
        full_name="Feedback Manager Three",
        plain_password="manager123",
        role=UserRole.MANAGER,
        tenant_id=test_tenant.id,
        is_active=True,
    )
    manager_headers = _login_headers(client, manager.username, "manager123")
    document = create_document(
        db,
        title="Escalation Manual",
        document_number="DOC-FB-005",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.PUBLIC,
        created_by=manager.id,
        tenant_id=test_tenant.id,
    )

    submit_response = client.post(
        "/api/v1/portal/feedback",
        headers=customer_headers,
        json={
            "document_id": document.id,
            "feedback_type": "issue",
            "content": "This needs direct support follow-up.",
        },
    )
    assert submit_response.status_code == 200
    feedback_id = submit_response.json()["id"]

    escalate_response = client.post(
        f"/api/v1/support/tickets/from-feedback/{feedback_id}",
        headers=manager_headers,
    )
    assert escalate_response.status_code == 201
    ticket_payload = escalate_response.json()
    assert ticket_payload["feedback_id"] == feedback_id
    assert ticket_payload["category"] == "issue"

    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_payload["id"]).first()
    assert ticket is not None
    messages = (
        db.query(SupportTicketMessage)
        .filter(SupportTicketMessage.ticket_id == ticket.id)
        .order_by(SupportTicketMessage.created_at.asc())
        .all()
    )
    assert [message.content for message in messages] == ["This needs direct support follow-up."]
