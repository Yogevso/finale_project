"""Feedback flow tests for ticket-backed customer conversations."""

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


def test_portal_feedback_submission_creates_linked_ticket(
    client,
    db,
    customer_headers,
    test_customer,
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
    assert payload["ticket_id"] is not None

    feedback = db.query(Feedback).filter(Feedback.id == payload["id"]).first()
    ticket = db.query(SupportTicket).filter(SupportTicket.id == payload["ticket_id"]).first()
    assert feedback is not None
    assert ticket is not None
    assert ticket.feedback_id == feedback.id
    assert ticket.customer_id == test_customer.id
    assert ticket.category == "question"
    assert "Feedback Handbook" in ticket.subject

    messages = (
        db.query(SupportTicketMessage)
        .filter(SupportTicketMessage.ticket_id == ticket.id)
        .order_by(SupportTicketMessage.created_at.asc())
        .all()
    )
    assert [message.content for message in messages] == [feedback.content]

    notification = (
        db.query(Notification)
        .filter(Notification.user_id == manager.id)
        .order_by(Notification.id.desc())
        .first()
    )
    assert notification is not None
    assert notification.type == NotificationType.FEEDBACK_RECEIVED
    assert notification.link == f"/support?ticket={ticket.id}"


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
    ticket_id = response.json()["ticket_id"]

    notification = (
        db.query(Notification)
        .filter(Notification.user_id == editor.id)
        .order_by(Notification.id.desc())
        .first()
    )
    assert notification is not None
    assert notification.type == NotificationType.FEEDBACK_RECEIVED
    assert notification.link == f"/support?ticket={ticket_id}"


def test_feedback_response_writes_into_ticket_thread_and_customer_can_view_it(
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
    assert responded_payload["ticket_id"] == feedback_payload["ticket_id"]
    assert responded_payload["response"] == "Thanks. We updated the ticket thread with the next steps."

    ticket = db.query(SupportTicket).filter(SupportTicket.id == feedback_payload["ticket_id"]).first()
    assert ticket is not None
    messages = (
        db.query(SupportTicketMessage)
        .filter(SupportTicketMessage.ticket_id == ticket.id)
        .order_by(SupportTicketMessage.created_at.asc())
        .all()
    )
    assert [message.content for message in messages] == [
        "The escalation section is missing the latest process.",
        "Thanks. We updated the ticket thread with the next steps.",
    ]

    portal_feedback_response = client.get(
        f"/api/v1/portal/feedback/{feedback_payload['id']}",
        headers=customer_headers,
    )
    assert portal_feedback_response.status_code == 200
    assert portal_feedback_response.json()["ticket_id"] == ticket.id

    ticket_response = client.get(
        f"/api/v1/portal/support/tickets/{ticket.id}",
        headers=customer_headers,
    )
    assert ticket_response.status_code == 200
    ticket_payload = ticket_response.json()
    assert ticket_payload["feedback_id"] == feedback_payload["id"]
    assert [message["content"] for message in ticket_payload["messages"]] == [
        "The escalation section is missing the latest process.",
        "Thanks. We updated the ticket thread with the next steps.",
    ]

    customer_notification = (
        db.query(Notification)
        .filter(Notification.user_id == test_customer.id)
        .order_by(Notification.id.desc())
        .first()
    )
    assert customer_notification is not None
    assert customer_notification.type == NotificationType.FEEDBACK_RESPONDED
    assert customer_notification.link == f"/portal/support?ticket={ticket.id}"
