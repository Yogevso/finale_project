"""Support ticket service tests — X1-107 to X1-111."""

import pytest

from app.config import settings
from app.errors import DomainError
from app.models import (
    Document,
    DocumentStatus,
    DocumentVisibility,
    Feedback,
    FeedbackType,
    Notification,
    NotificationType,
    SupportTicket,
    SupportTicketAssignment,
    SupportTicketMessage,
    SupportTicketPriority,
    SupportTicketStatus,
    UserRole,
)
from app.services.support_service import SupportTicketService
from tests.factories import create_document, create_tenant, create_user


class _FakeStorageBackend:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.upload_calls = 0

    def upload(self, file_data, filename: str, content_type: str) -> str:
        self.upload_calls += 1
        key = f"support-{self.upload_calls}-{filename}"
        self.files[key] = file_data.read()
        return key

    def download(self, storage_key: str) -> bytes:
        if storage_key not in self.files:
            raise FileNotFoundError(storage_key)
        return self.files[storage_key]

    def delete(self, storage_key: str) -> bool:
        self.files.pop(storage_key, None)
        return True


@pytest.fixture
def tenant(db):
    return create_tenant(db, name="Support Tenant", slug="support-tenant")


@pytest.fixture
def customer(db, tenant):
    return create_user(
        db, username="support_cust", full_name="Support Customer",
        role=UserRole.CUSTOMER, tenant_id=tenant.id,
    )


@pytest.fixture
def customer_b(db):
    other_tenant = create_tenant(db, name="Other Tenant", slug="other-tenant-supp")
    return create_user(
        db, username="other_cust", full_name="Other Customer",
        role=UserRole.CUSTOMER, tenant_id=other_tenant.id,
    )


@pytest.fixture
def agent(db, tenant):
    return create_user(
        db, username="agent1", full_name="Agent One",
        role=UserRole.MANAGER, tenant_id=tenant.id,
    )


@pytest.fixture
def agent_b(db, tenant):
    return create_user(
        db, username="agent2", full_name="Agent Two",
        role=UserRole.MANAGER, tenant_id=tenant.id,
    )


@pytest.fixture
def feedback(db, customer, tenant):
    doc = create_document(
        db, title="FB Doc", created_by=customer.id,
        status=DocumentStatus.ACTIVE, visibility=DocumentVisibility.PUBLIC,
    )
    fb = Feedback(
        user_id=customer.id,
        document_id=doc.id,
        feedback_type=FeedbackType.OTHER,
        content="I need help with this document",
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


@pytest.fixture
def svc(db):
    return SupportTicketService(db)


# =====================================================================
# X1-107: create_ticket_from_feedback
# =====================================================================

class TestCreateTicketFromFeedback:
    """X1-107: Verify ticket created with correct customer, subject extracted."""

    def test_ticket_created_from_feedback(self, svc, customer, feedback):
        ticket = svc.create_ticket_from_feedback(customer, feedback.id)
        assert ticket.customer_id == customer.id
        assert ticket.feedback_id == feedback.id
        assert feedback.content[:100] in ticket.subject
        assert ticket.status == SupportTicketStatus.OPEN

    def test_initial_message_matches_feedback(self, db, svc, customer, feedback):
        ticket = svc.create_ticket_from_feedback(customer, feedback.id)
        msgs = (
            db.query(SupportTicketMessage)
            .filter_by(ticket_id=ticket.id)
            .all()
        )
        assert len(msgs) == 1
        assert msgs[0].content == feedback.content
        assert msgs[0].sender_id == customer.id

    def test_deduplication_returns_existing(self, svc, customer, feedback):
        ticket1 = svc.create_ticket_from_feedback(customer, feedback.id)
        ticket2 = svc.create_ticket_from_feedback(customer, feedback.id)
        assert ticket1.id == ticket2.id

    def test_feedback_not_found_raises_404(self, svc, customer):
        with pytest.raises(DomainError) as exc:
            svc.create_ticket_from_feedback(customer, 99999)
        assert exc.value.status_code == 404


# =====================================================================
# X1-108: Internal notes visibility
# =====================================================================

class TestInternalNotes:
    """X1-108: Verify customer cannot see notes, agents can."""

    def _create_ticket_with_note(self, svc, customer, agent):
        ticket = svc.create_ticket(customer, "Test subject", "Hello")
        svc.send_message(ticket.id, agent, "Internal note", is_internal_note=True)
        svc.send_message(ticket.id, agent, "Public reply", is_internal_note=False)
        return ticket

    def test_customer_does_not_see_internal_notes(self, svc, customer, agent):
        ticket = self._create_ticket_with_note(svc, customer, agent)
        messages = svc.get_messages(ticket.id, customer)
        assert all(not m.is_internal_note for m in messages)
        # Should see initial message + public reply, not the internal note
        assert len(messages) == 2

    def test_agent_sees_internal_notes(self, svc, customer, agent):
        ticket = self._create_ticket_with_note(svc, customer, agent)
        messages = svc.get_messages(ticket.id, agent)
        internal = [m for m in messages if m.is_internal_note]
        assert len(internal) == 1
        assert internal[0].content == "Internal note"

    def test_customer_cannot_create_internal_note(self, svc, customer):
        ticket = svc.create_ticket(customer, "Test", "Content")
        with pytest.raises(DomainError) as exc:
            svc.send_message(ticket.id, customer, "Sneaky note", is_internal_note=True)
        assert exc.value.status_code == 403


# =====================================================================
# X1-109: Status transitions
# =====================================================================

class TestStatusTransitions:
    """X1-109: Verify valid transitions, reject invalid."""

    def test_open_to_in_progress_on_assign(self, svc, customer, agent):
        ticket = svc.create_ticket(customer, "Subject", "Content")
        assert ticket.status == SupportTicketStatus.OPEN
        svc.assign_agent(ticket.id, agent, agent.id, is_primary=True)
        svc.db.refresh(ticket)
        assert ticket.status == SupportTicketStatus.IN_PROGRESS

    def test_resolve_sets_resolved_at(self, svc, customer, agent):
        ticket = svc.create_ticket(customer, "Subject", "Content")
        svc.assign_agent(ticket.id, agent, agent.id, is_primary=True)
        updated = svc.update_ticket(ticket.id, agent, status=SupportTicketStatus.RESOLVED)
        assert updated.status == SupportTicketStatus.RESOLVED
        assert updated.resolved_at is not None

    def test_customer_close_resolved_ticket(self, svc, customer):
        ticket = svc.create_ticket(customer, "Subject", "Content")
        svc.update_ticket.__func__  # ensure method exists
        # Manually set resolved for this test
        ticket.status = SupportTicketStatus.RESOLVED
        svc.db.commit()
        closed = svc.close_ticket_as_customer(ticket.id, customer)
        assert closed.status == SupportTicketStatus.CLOSED

    def test_customer_cannot_close_in_progress(self, svc, customer, agent):
        ticket = svc.create_ticket(customer, "Subject", "Content")
        ticket.status = SupportTicketStatus.IN_PROGRESS
        svc.db.commit()
        with pytest.raises(DomainError) as exc:
            svc.close_ticket_as_customer(ticket.id, customer)
        assert exc.value.status_code == 400

    def test_customer_message_reopens_resolved(self, svc, customer, agent):
        ticket = svc.create_ticket(customer, "Subject", "Content")
        svc.assign_agent(ticket.id, agent, agent.id, is_primary=True)
        svc.update_ticket(ticket.id, agent, status=SupportTicketStatus.RESOLVED)
        svc.send_message(ticket.id, customer, "Still broken")
        svc.db.refresh(ticket)
        assert ticket.status == SupportTicketStatus.OPEN


# =====================================================================
# X1-110: Multi-agent ticket
# =====================================================================

class TestMultiAgentTicket:
    """X1-110: Two agents respond, verify both messages appear."""

    def test_two_agents_respond(self, svc, customer, agent, agent_b):
        ticket = svc.create_ticket(customer, "Subject", "Help")
        svc.assign_agent(ticket.id, agent, agent.id)
        svc.assign_agent(ticket.id, agent_b, agent_b.id)

        svc.send_message(ticket.id, agent, "Agent 1 reply")
        svc.send_message(ticket.id, agent_b, "Agent 2 reply")

        messages = svc.get_messages(ticket.id, agent)
        contents = [m.content for m in messages]
        assert "Agent 1 reply" in contents
        assert "Agent 2 reply" in contents

    def test_both_agents_visible_in_assignments(self, db, svc, customer, agent, agent_b):
        ticket = svc.create_ticket(customer, "Subject", "Help")
        svc.assign_agent(ticket.id, agent, agent.id)
        svc.assign_agent(ticket.id, agent_b, agent_b.id)

        assignments = (
            db.query(SupportTicketAssignment)
            .filter_by(ticket_id=ticket.id)
            .all()
        )
        agent_ids = {a.agent_id for a in assignments}
        assert agent_ids == {agent.id, agent_b.id}

    def test_handoff_transfers_primary(self, db, svc, customer, agent, agent_b):
        ticket = svc.create_ticket(customer, "Subject", "Help")
        svc.assign_agent(ticket.id, agent, agent.id, is_primary=True)

        svc.handoff_ticket(ticket.id, agent, agent_b.id, note="Take over please")

        a1 = db.query(SupportTicketAssignment).filter_by(
            ticket_id=ticket.id, agent_id=agent.id
        ).first()
        a2 = db.query(SupportTicketAssignment).filter_by(
            ticket_id=ticket.id, agent_id=agent_b.id
        ).first()
        assert a1.is_primary is False
        assert a2.is_primary is True


# =====================================================================
# X1-111: Customer isolation
# =====================================================================

class TestCustomerIsolation:
    """X1-111: Customer cannot access other customer's ticket."""

    def test_customer_cannot_see_other_customer_ticket(self, svc, customer, customer_b):
        ticket = svc.create_ticket(customer, "Private ticket", "Help me")
        with pytest.raises(DomainError) as exc:
            svc.get_ticket(ticket.id, customer_b)
        assert exc.value.status_code == 403

    def test_customer_cannot_message_other_ticket(self, svc, customer, customer_b):
        ticket = svc.create_ticket(customer, "Private ticket", "Help me")
        with pytest.raises(DomainError) as exc:
            svc.send_message(ticket.id, customer_b, "Intruder message")
        assert exc.value.status_code == 403

    def test_customer_only_sees_own_tickets(self, svc, customer, customer_b):
        svc.create_ticket(customer, "Customer A ticket", "A content")
        svc.create_ticket(customer_b, "Customer B ticket", "B content")

        tickets_a, total_a = svc.list_tickets(customer)
        tickets_b, total_b = svc.list_tickets(customer_b)

        assert total_a == 1
        assert total_b == 1
        assert tickets_a[0].customer_id == customer.id
        assert tickets_b[0].customer_id == customer_b.id

    def test_agent_can_see_all_tickets(self, db, svc, customer, customer_b):
        svc.create_ticket(customer, "Ticket A", "A")
        svc.create_ticket(customer_b, "Ticket B", "B")

        sys_admin = create_user(
            db, username="sys_agent", full_name="Sys Agent",
            role=UserRole.SYSTEM_ADMIN,
        )
        tickets, total = svc.list_tickets(sys_admin)
        assert total == 2


class TestSupportNotifications:
    def test_agent_reply_creates_customer_notification_and_email(
        self,
        svc,
        customer,
        agent,
        monkeypatch,
    ):
        ticket = svc.create_ticket(customer, "Need help", "Original issue")
        queued_emails: list[dict[str, str]] = []

        monkeypatch.setattr(settings, "EMAIL_ENABLED", True)
        monkeypatch.setattr(svc, "_queue_email", lambda **kwargs: queued_emails.append(kwargs))

        svc.send_message(ticket.id, agent, "We are looking into it.")

        notification = (
            svc.db.query(Notification)
            .filter(Notification.user_id == customer.id)
            .order_by(Notification.id.desc())
            .first()
        )
        assert notification is not None
        assert notification.title == f"New reply on ticket #{ticket.id}"
        assert notification.link == f"/portal/support?ticket={ticket.id}"
        assert any(
            item["to_email"] == customer.email
            and item["subject"] == f"Support replied to ticket #{ticket.id}: {ticket.subject}"
            for item in queued_emails
        )

    def test_create_ticket_emails_support_agents(
        self,
        svc,
        customer,
        agent,
        monkeypatch,
    ):
        queued_emails: list[dict[str, str]] = []

        monkeypatch.setattr(settings, "EMAIL_ENABLED", True)
        monkeypatch.setattr(svc, "_queue_email", lambda **kwargs: queued_emails.append(kwargs))

        ticket = svc.create_ticket(customer, "Creation email", "Please help")

        assert any(
            item["to_email"] == agent.email
            and item["subject"] == f"New support ticket #{ticket.id}: {ticket.subject}"
            for item in queued_emails
        )

    def test_create_ticket_creates_agent_notification(
        self,
        svc,
        customer,
        agent,
    ):
        ticket = svc.create_ticket(customer, "Creation notification", "Please help")

        notification = (
            svc.db.query(Notification)
            .filter(Notification.user_id == agent.id)
            .order_by(Notification.id.desc())
            .first()
        )
        assert notification is not None
        assert notification.type == NotificationType.TICKET_NEW_CUSTOMER_MSG
        assert notification.title == f"New support ticket #{ticket.id}"
        assert notification.link == f"/support?ticket={ticket.id}"

    def test_resolving_ticket_emails_customer(
        self,
        svc,
        customer,
        agent,
        monkeypatch,
    ):
        ticket = svc.create_ticket(customer, "Resolution email", "Please help")
        svc.assign_agent(ticket.id, agent, agent.id, is_primary=True)
        queued_emails: list[dict[str, str]] = []

        monkeypatch.setattr(settings, "EMAIL_ENABLED", True)
        monkeypatch.setattr(svc, "_queue_email", lambda **kwargs: queued_emails.append(kwargs))

        svc.update_ticket(ticket.id, agent, status=SupportTicketStatus.RESOLVED)

        assert any(
            item["to_email"] == customer.email
            and item["subject"] == f"Ticket #{ticket.id} marked resolved"
            for item in queued_emails
        )


class TestSupportMessageAttachments:
    def test_message_attachment_is_persisted_and_exposed_in_event_payload(
        self,
        svc,
        customer,
        monkeypatch,
    ):
        fake_storage = _FakeStorageBackend()
        monkeypatch.setattr("app.services.support_service.get_storage_backend", lambda: fake_storage)

        ticket = svc.create_ticket(customer, "Attachment support", "Initial issue")
        message = svc.send_message(
            ticket.id,
            customer,
            "",
            file_bytes=b"hello support",
            file_name="evidence.txt",
            file_mime_type="text/plain",
        )

        assert message.content == ""
        assert message.file_name == "evidence.txt"
        assert message.file_size == len(b"hello support")
        assert message.file_mime_type == "text/plain"
        assert message.file_storage_key in fake_storage.files

        event_data = svc.build_message_event_data(message, customer)
        assert event_data["file_name"] == "evidence.txt"
        assert event_data["file_size"] == len(b"hello support")
        assert event_data["file_mime_type"] == "text/plain"
        assert event_data["file_url"] == (
            f"{settings.API_PREFIX}/support/tickets/{ticket.id}/messages/{message.id}/attachment"
        )

    def test_attachment_download_requires_ticket_access(
        self,
        svc,
        customer,
        customer_b,
        monkeypatch,
    ):
        fake_storage = _FakeStorageBackend()
        monkeypatch.setattr("app.services.support_service.get_storage_backend", lambda: fake_storage)

        ticket = svc.create_ticket(customer, "Attachment download", "Initial issue")
        message = svc.send_message(
            ticket.id,
            customer,
            "See file",
            file_bytes=b"hello support",
            file_name="evidence.txt",
            file_mime_type="text/plain",
        )

        loaded_message, content = svc.get_message_attachment(ticket.id, message.id, customer)
        assert loaded_message.id == message.id
        assert content == b"hello support"

        with pytest.raises(DomainError) as exc:
            svc.get_message_attachment(ticket.id, message.id, customer_b)
        assert exc.value.status_code == 403
