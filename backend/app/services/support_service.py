"""Support ticket service — customer support chat (Wave X.1)."""

from __future__ import annotations

import io
import json
import logging
import re
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import (
    Feedback,
    Notification,
    NotificationType,
    SupportTicket,
    SupportTicketAssignment,
    SupportTicketMessage,
    SupportTicketPriority,
    SupportTicketStatus,
    User,
    UserRole,
)
from app.services.attachment_service.common import AttachmentServiceCommonMixin
from app.services.email_service import email_service
from app.services.malware_scan_service import (
    MalwareDetectedError,
    MalwareScannerUnavailableError,
    scan_upload_bytes,
)
from app.services.storage_service import get_storage_backend
from app.utils.async_tasks import run_async_task
from app.utils.sanitization import sanitize_html_content

MENTION_RE = re.compile(r"(?<!\w)@(\w[\w.-]{0,99})")
logger = logging.getLogger(__name__)

# H-27: Support ticket state machine — allowed transitions per role category.
_STAFF_TRANSITIONS: dict[SupportTicketStatus, set[SupportTicketStatus]] = {
    SupportTicketStatus.OPEN: {SupportTicketStatus.IN_PROGRESS, SupportTicketStatus.CLOSED},
    SupportTicketStatus.IN_PROGRESS: {SupportTicketStatus.RESOLVED, SupportTicketStatus.OPEN, SupportTicketStatus.CLOSED},
    SupportTicketStatus.RESOLVED: {SupportTicketStatus.CLOSED, SupportTicketStatus.IN_PROGRESS},
    SupportTicketStatus.CLOSED: set(),  # staff cannot reopen closed tickets
}

_CUSTOMER_TRANSITIONS: dict[SupportTicketStatus, set[SupportTicketStatus]] = {
    SupportTicketStatus.OPEN: {SupportTicketStatus.CLOSED},
    SupportTicketStatus.IN_PROGRESS: set(),
    SupportTicketStatus.RESOLVED: {SupportTicketStatus.CLOSED, SupportTicketStatus.OPEN},
    SupportTicketStatus.CLOSED: set(),
}


def _allowed_transitions(user: User) -> dict[SupportTicketStatus, set[SupportTicketStatus]]:
    if user.role in (UserRole.CUSTOMER, UserRole.VIEWER):
        return _CUSTOMER_TRANSITIONS
    return _STAFF_TRANSITIONS


class SupportTicketService:
    _SUPPORTED_ATTACHMENT_EXTENSIONS = {
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".pdf",
        ".txt",
        ".md",
        ".html",
        ".htm",
        ".json",
        ".csv",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
    }

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _sanitize_message_content(content: str, *, allow_empty: bool = False) -> str:
        normalized_content = (content or "").strip()
        if not normalized_content:
            if allow_empty:
                return ""
            raise HTTPException(status_code=400, detail="content is empty after sanitization")
        sanitized_content = (sanitize_html_content(normalized_content) or "").strip()
        if not sanitized_content:
            raise HTTPException(status_code=400, detail="content is empty after sanitization")
        return sanitized_content

    @staticmethod
    def _message_preview(content: str, limit: int = 160) -> str:
        condensed = " ".join(content.split())
        if len(condensed) <= limit:
            return condensed
        return condensed[: limit - 1].rstrip() + "..."

    @staticmethod
    def _agent_ticket_link(ticket_id: int) -> str:
        return f"{settings.BASE_URL}/support?ticket={ticket_id}"

    @staticmethod
    def _customer_ticket_link(ticket_id: int) -> str:
        return f"{settings.BASE_URL}/portal/support?ticket={ticket_id}"

    def _queue_email(
        self,
        *,
        to_email: str | None,
        subject: str,
        html_content: str,
        text_content: str,
    ) -> None:
        if not settings.EMAIL_ENABLED or not to_email:
            return
        run_async_task(
            email_service.send_email(
                to_email=to_email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
            )
        )

    def _list_support_notification_recipients(
        self,
        ticket: SupportTicket,
        *,
        exclude_user_id: int | None = None,
    ) -> list[User]:
        assigned_agents = (
            self.db.query(User)
            .join(
                SupportTicketAssignment,
                SupportTicketAssignment.agent_id == User.id,
            )
            .filter(
                SupportTicketAssignment.ticket_id == ticket.id,
                User.is_active.is_(True),
            )
        )
        if exclude_user_id is not None:
            assigned_agents = assigned_agents.filter(User.id != exclude_user_id)
        recipients = assigned_agents.all()
        if recipients:
            return recipients

        support_roles = [UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER]
        fallback_query = self.db.query(User).filter(
            User.is_active.is_(True),
            User.role.in_(support_roles),
        )
        if exclude_user_id is not None:
            fallback_query = fallback_query.filter(User.id != exclude_user_id)
        if ticket.tenant_id is not None:
            fallback_query = fallback_query.filter(
                or_(
                    User.role == UserRole.SYSTEM_ADMIN,
                    User.tenant_id == ticket.tenant_id,
                )
            )
        return fallback_query.all()

    def _list_support_email_recipients(
        self,
        ticket: SupportTicket,
        *,
        exclude_user_id: int | None = None,
    ) -> list[User]:
        return [
            recipient
            for recipient in self._list_support_notification_recipients(
                ticket,
                exclude_user_id=exclude_user_id,
            )
            if recipient.email
        ]

    def _notify_agents_on_new_ticket(
        self,
        *,
        ticket: SupportTicket,
        customer: User,
    ) -> None:
        for recipient in self._list_support_notification_recipients(
            ticket,
            exclude_user_id=customer.id,
        ):
            self.db.add(
                Notification(
                    user_id=recipient.id,
                    type=NotificationType.TICKET_NEW_CUSTOMER_MSG,
                    title=f"New support ticket #{ticket.id}",
                    message=f"{customer.full_name} opened \"{ticket.subject}\"",
                    link=f"/support?ticket={ticket.id}",
                )
            )

    def _email_support_agents_about_new_ticket(
        self,
        *,
        ticket: SupportTicket,
        customer: User,
        initial_message: str,
    ) -> None:
        preview = escape(self._message_preview(initial_message))
        ticket_subject = escape(ticket.subject)
        ticket_url = self._agent_ticket_link(ticket.id)
        for recipient in self._list_support_email_recipients(ticket, exclude_user_id=customer.id):
            self._queue_email(
                to_email=recipient.email,
                subject=f"New support ticket #{ticket.id}: {ticket.subject}",
                html_content=(
                    "<p>A new support ticket was created.</p>"
                    f"<p><strong>Customer:</strong> {escape(customer.full_name)}</p>"
                    f"<p><strong>Subject:</strong> {ticket_subject}</p>"
                    f"<blockquote>{preview}</blockquote>"
                    f"<p><a href=\"{ticket_url}\">Open ticket</a></p>"
                ),
                text_content=(
                    f"New support ticket #{ticket.id}\n\n"
                    f"Customer: {customer.full_name}\n"
                    f"Subject: {ticket.subject}\n"
                    f"Message: {self._message_preview(initial_message)}\n"
                    f"Open ticket: {ticket_url}\n"
                ),
            )

    def _email_support_agents_on_customer_message(
        self,
        *,
        ticket: SupportTicket,
        customer: User,
        message_content: str,
    ) -> None:
        preview = escape(self._message_preview(message_content))
        ticket_subject = escape(ticket.subject)
        ticket_url = self._agent_ticket_link(ticket.id)
        for recipient in self._list_support_email_recipients(ticket, exclude_user_id=customer.id):
            self._queue_email(
                to_email=recipient.email,
                subject=f"Customer replied on ticket #{ticket.id}: {ticket.subject}",
                html_content=(
                    "<p>A customer replied on a support ticket.</p>"
                    f"<p><strong>Customer:</strong> {escape(customer.full_name)}</p>"
                    f"<p><strong>Subject:</strong> {ticket_subject}</p>"
                    f"<blockquote>{preview}</blockquote>"
                    f"<p><a href=\"{ticket_url}\">Open ticket</a></p>"
                ),
                text_content=(
                    f"Customer replied on ticket #{ticket.id}\n\n"
                    f"Customer: {customer.full_name}\n"
                    f"Subject: {ticket.subject}\n"
                    f"Message: {self._message_preview(message_content)}\n"
                    f"Open ticket: {ticket_url}\n"
                ),
            )

    def _notify_customer_on_agent_reply(
        self,
        *,
        ticket: SupportTicket,
        agent: User,
    ) -> None:
        self.db.add(
            Notification(
                user_id=ticket.customer_id,
                type=NotificationType.SYSTEM,
                title=f"New reply on ticket #{ticket.id}",
                message=f"{agent.full_name} replied to \"{ticket.subject}\".",
                link=f"/portal/support?ticket={ticket.id}",
            )
        )

    def _email_customer_on_agent_reply(
        self,
        *,
        ticket: SupportTicket,
        agent: User,
        message_content: str,
    ) -> None:
        customer = ticket.customer or self.db.query(User).filter(User.id == ticket.customer_id).first()
        if customer is None:
            return

        preview = escape(self._message_preview(message_content))
        ticket_subject = escape(ticket.subject)
        ticket_url = self._customer_ticket_link(ticket.id)
        self._queue_email(
            to_email=customer.email,
            subject=f"Support replied to ticket #{ticket.id}: {ticket.subject}",
            html_content=(
                "<p>Your support ticket has a new reply.</p>"
                f"<p><strong>Agent:</strong> {escape(agent.full_name)}</p>"
                f"<p><strong>Subject:</strong> {ticket_subject}</p>"
                f"<blockquote>{preview}</blockquote>"
                f"<p><a href=\"{ticket_url}\">View ticket</a></p>"
            ),
            text_content=(
                f"Support replied to ticket #{ticket.id}\n\n"
                f"Agent: {agent.full_name}\n"
                f"Subject: {ticket.subject}\n"
                f"Reply: {self._message_preview(message_content)}\n"
                f"View ticket: {ticket_url}\n"
            ),
        )

    def _email_customer_on_status_change(
        self,
        *,
        ticket: SupportTicket,
        actor: User,
    ) -> None:
        customer = ticket.customer or self.db.query(User).filter(User.id == ticket.customer_id).first()
        if customer is None:
            return

        ticket_url = self._customer_ticket_link(ticket.id)
        status_label = ticket.status.value.replace("_", " ")
        self._queue_email(
            to_email=customer.email,
            subject=f"Ticket #{ticket.id} marked {status_label}",
            html_content=(
                f"<p>Your support ticket <strong>{escape(ticket.subject)}</strong> "
                f"was marked {escape(status_label)} by {escape(actor.full_name)}.</p>"
                f"<p><a href=\"{ticket_url}\">View ticket</a></p>"
            ),
            text_content=(
                f"Ticket #{ticket.id} marked {status_label}\n\n"
                f"Subject: {ticket.subject}\n"
                f"Updated by: {actor.full_name}\n"
                f"View ticket: {ticket_url}\n"
            ),
        )

    @staticmethod
    def build_message_file_url(ticket_id: int, message_id: int) -> str:
        return f"{settings.API_PREFIX}/support/tickets/{ticket_id}/messages/{message_id}/attachment"

    def _store_message_attachment(
        self,
        *,
        file_bytes: bytes,
        file_name: str,
        file_mime_type: str | None,
    ) -> tuple[str, str, int, str]:
        normalized_name = Path(file_name or "attachment").name or "attachment"
        normalized_type = (file_mime_type or "application/octet-stream").lower()
        file_ext = Path(normalized_name).suffix.lower()
        if (
            normalized_type not in AttachmentServiceCommonMixin.ALLOWED_TYPES
            and file_ext not in self._SUPPORTED_ATTACHMENT_EXTENSIONS
        ):
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed: {normalized_type}",
            )

        if len(file_bytes) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB",
            )

        AttachmentServiceCommonMixin._validate_magic_bytes(
            file_bytes,
            normalized_name,
            normalized_type,
        )
        try:
            scan_upload_bytes(file_bytes, normalized_name, normalized_type)
        except MalwareDetectedError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except MalwareScannerUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        storage = get_storage_backend()
        storage_key = storage.upload(
            io.BytesIO(file_bytes),
            normalized_name,
            normalized_type,
        )
        return storage_key, normalized_name, len(file_bytes), normalized_type

    def get_message_attachment(
        self,
        ticket_id: int,
        message_id: int,
        current_user: User,
    ) -> tuple[SupportTicketMessage, bytes]:
        ticket = self.db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        self._check_ticket_access(ticket, current_user)

        message = (
            self.db.query(SupportTicketMessage)
            .filter(
                SupportTicketMessage.id == message_id,
                SupportTicketMessage.ticket_id == ticket_id,
            )
            .first()
        )
        if not message or not message.file_storage_key:
            raise HTTPException(status_code=404, detail="Attachment not found")
        if message.is_internal_note and current_user.id == ticket.customer_id:
            raise HTTPException(status_code=404, detail="Attachment not found")

        try:
            content = get_storage_backend().download(message.file_storage_key)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Attachment not found") from exc
        except Exception as exc:
            logger.warning(
                "Failed to download support attachment %s for message %s: %s",
                message.file_storage_key,
                message.id,
                exc,
            )
            raise HTTPException(status_code=503, detail="Attachment temporarily unavailable") from exc

        return message, content

    @staticmethod
    def build_message_event_data(
        msg: SupportTicketMessage,
        sender: User,
    ) -> dict[str, object]:
        return {
            "id": msg.id,
            "ticket_id": msg.ticket_id,
            "sender_id": msg.sender_id,
            "sender_type": msg.sender_type,
            "sender_full_name": sender.full_name,
            "content": msg.content,
            "is_internal_note": msg.is_internal_note,
            "file_url": (
                SupportTicketService.build_message_file_url(msg.ticket_id, msg.id)
                if msg.file_storage_key
                else None
            ),
            "file_name": msg.file_name,
            "file_size": msg.file_size,
            "file_mime_type": msg.file_mime_type,
            "created_at": msg.created_at.isoformat(),
        }

    async def broadcast_message_event(
        self,
        *,
        ticket: SupportTicket,
        msg: SupportTicketMessage,
        sender: User,
    ) -> None:
        from app.ws.manager import chat_manager

        event_data = self.build_message_event_data(msg, sender)
        if msg.is_internal_note:
            connections = chat_manager._support_connections.get(ticket.id, {})
            for uid, ws in list(connections.items()):
                if uid == ticket.customer_id:
                    continue
                await chat_manager._safe_send(
                    ws,
                    json.dumps({"event": "new_message", "data": event_data}),
                )
            return

        await chat_manager.broadcast_to_ticket(ticket.id, "new_message", event_data)

    # ------------------------------------------------------------------
    # Ticket creation
    # ------------------------------------------------------------------

    def create_ticket(
        self,
        customer: User,
        subject: str,
        content: str,
        priority: SupportTicketPriority = SupportTicketPriority.NORMAL,
        category: Optional[str] = None,
        feedback_id: Optional[int] = None,
    ) -> SupportTicket:
        """Create a support ticket, optionally linked to feedback (X1-066)."""
        if feedback_id:
            fb = self.db.query(Feedback).filter(
                Feedback.id == feedback_id, Feedback.user_id == customer.id
            ).first()
            if not fb:
                raise HTTPException(status_code=404, detail="Feedback not found")

        ticket = SupportTicket(
            customer_id=customer.id,
            subject=subject.strip(),
            status=SupportTicketStatus.OPEN,
            priority=priority,
            category=category.strip() if category else None,
            feedback_id=feedback_id,
            tenant_id=customer.tenant_id,
        )
        self.db.add(ticket)
        self.db.flush()

        # Initial message
        initial_message_content = sanitize_html_content(content.strip()) or content.strip()
        self.db.add(SupportTicketMessage(
            ticket_id=ticket.id,
            sender_id=customer.id,
            sender_type="customer",
            content=initial_message_content,
            is_internal_note=False,
        ))
        self._notify_agents_on_new_ticket(ticket=ticket, customer=customer)

        self.db.commit()
        self.db.refresh(ticket)
        self._email_support_agents_about_new_ticket(
            ticket=ticket,
            customer=customer,
            initial_message=initial_message_content,
        )
        return ticket

    def create_ticket_from_feedback(self, customer: User, feedback_id: int) -> SupportTicket:
        """Create a support ticket from an existing feedback item (X1-067)."""
        fb = self.db.query(Feedback).filter(
            Feedback.id == feedback_id, Feedback.user_id == customer.id
        ).first()
        if not fb:
            raise HTTPException(status_code=404, detail="Feedback not found")

        # Check no duplicate ticket for this feedback
        existing = self.db.query(SupportTicket).filter(
            SupportTicket.feedback_id == feedback_id
        ).first()
        if existing:
            return existing

        return self.create_ticket(
            customer=customer,
            subject=f"Support: {fb.content[:100]}",
            content=fb.content,
            feedback_id=feedback_id,
        )

    # ------------------------------------------------------------------
    # Ticket queries
    # ------------------------------------------------------------------

    def get_ticket(self, ticket_id: int, current_user: User) -> SupportTicket:
        """Get ticket with messages and assignments (X1-068)."""
        ticket = (
            self.db.query(SupportTicket)
            .options(
                joinedload(SupportTicket.messages),
                joinedload(SupportTicket.assignments),
                joinedload(SupportTicket.customer),
            )
            .filter(SupportTicket.id == ticket_id)
            .first()
        )
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")

        self._check_ticket_access(ticket, current_user)
        return ticket

    def list_tickets(
        self,
        current_user: User,
        status_filter: Optional[SupportTicketStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[SupportTicket], int]:
        """List tickets visible to the current user (X1-069)."""
        query = self.db.query(SupportTicket).options(joinedload(SupportTicket.customer))

        # Customers/viewers see only their own tickets
        if current_user.role in (UserRole.CUSTOMER, UserRole.VIEWER):
            query = query.filter(SupportTicket.customer_id == current_user.id)
        elif current_user.role != UserRole.SYSTEM_ADMIN:
            # Internal staff see only tickets within their tenant
            if current_user.tenant_id is None:
                # Staff without a tenant should see nothing (not all unscoped tickets)
                query = query.filter(SupportTicket.id == -1)  # yields empty result
            else:
                query = query.filter(SupportTicket.tenant_id == current_user.tenant_id)

        if status_filter:
            query = query.filter(SupportTicket.status == status_filter)

        total = query.count()
        tickets = (
            query
            .order_by(SupportTicket.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return tickets, total

    # ------------------------------------------------------------------
    # Ticket updates
    # ------------------------------------------------------------------

    def update_ticket(
        self,
        ticket_id: int,
        current_user: User,
        subject: Optional[str] = None,
        status: Optional[SupportTicketStatus] = None,
        priority: Optional[SupportTicketPriority] = None,
        category: Optional[str] = None,
    ) -> SupportTicket:
        """Update ticket fields (X1-070)."""
        ticket = self._get_ticket_for_agent(ticket_id, current_user)
        previous_status = ticket.status

        if subject is not None:
            ticket.subject = subject.strip()
        if status is not None:
            allowed = _allowed_transitions(current_user).get(ticket.status, set())
            if status not in allowed:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot transition from {ticket.status.value} to {status.value}",
                )
            ticket.status = status
            if status == SupportTicketStatus.RESOLVED:
                ticket.resolved_at = datetime.utcnow()
        if priority is not None:
            ticket.priority = priority
        if category is not None:
            ticket.category = category.strip() if category else None

        self.db.commit()
        self.db.refresh(ticket)
        if ticket.status != previous_status and ticket.status in (
            SupportTicketStatus.RESOLVED,
            SupportTicketStatus.CLOSED,
        ):
            self._email_customer_on_status_change(ticket=ticket, actor=current_user)
        return ticket

    def close_ticket_as_customer(self, ticket_id: int, customer: User) -> SupportTicket:
        """Customer closes their own ticket (X1-075)."""
        ticket = self.db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        if ticket.customer_id != customer.id:
            raise HTTPException(status_code=403, detail="Access denied")
        if ticket.status not in (SupportTicketStatus.RESOLVED, SupportTicketStatus.OPEN):
            raise HTTPException(status_code=400, detail="Only resolved or open tickets can be closed")
        ticket.status = SupportTicketStatus.CLOSED
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    def send_message(
        self,
        ticket_id: int,
        sender: User,
        content: str,
        is_internal_note: bool = False,
        *,
        file_bytes: bytes | None = None,
        file_name: str | None = None,
        file_mime_type: str | None = None,
    ) -> SupportTicketMessage:
        """Send a message on a ticket (X1-071)."""
        ticket = self.db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        self._check_ticket_access(ticket, sender)

        # M-48: Prevent messaging on closed tickets
        if ticket.status == SupportTicketStatus.CLOSED:
            raise HTTPException(status_code=400, detail="Cannot send messages on closed tickets")

        # Determine sender_type
        if sender.id == ticket.customer_id:
            sender_type = "customer"
            if is_internal_note:
                raise HTTPException(status_code=403, detail="Customers cannot create internal notes")
        else:
            sender_type = "agent"

        has_attachment = file_bytes is not None
        if not (content or "").strip() and not has_attachment:
            raise HTTPException(status_code=400, detail="content or file is required")

        sanitized_content = self._sanitize_message_content(content, allow_empty=has_attachment)
        attachment_storage_key: str | None = None
        attachment_name: str | None = None
        attachment_size: int | None = None
        attachment_mime_type: str | None = None
        if file_bytes is not None:
            (
                attachment_storage_key,
                attachment_name,
                attachment_size,
                attachment_mime_type,
            ) = self._store_message_attachment(
                file_bytes=file_bytes,
                file_name=file_name or "attachment",
                file_mime_type=file_mime_type,
            )

        msg = SupportTicketMessage(
            ticket_id=ticket_id,
            sender_id=sender.id,
            sender_type=sender_type,
            content=sanitized_content,
            is_internal_note=is_internal_note,
            file_name=attachment_name,
            file_size=attachment_size,
            file_mime_type=attachment_mime_type,
            file_storage_key=attachment_storage_key,
        )
        self.db.add(msg)

        # Auto-reopen if customer sends message on resolved ticket
        if sender_type == "customer" and ticket.status == SupportTicketStatus.RESOLVED:
            ticket.status = SupportTicketStatus.OPEN
            ticket.resolved_at = None

        # Notifications (X1-087, X1-101)
        if sender_type == "customer":
            self._notify_agents_on_customer_message(ticket, sender)
            self._email_support_agents_on_customer_message(
                ticket=ticket,
                customer=sender,
                message_content=sanitized_content,
            )
        elif is_internal_note:
            self._notify_mentions_in_note(ticket_id, sender, content)
        else:
            self._notify_customer_on_agent_reply(ticket=ticket, agent=sender)
            self._email_customer_on_agent_reply(
                ticket=ticket,
                agent=sender,
                message_content=sanitized_content,
            )

        try:
            self.db.commit()
        except Exception:
            if attachment_storage_key:
                try:
                    get_storage_backend().delete(attachment_storage_key)
                except Exception as cleanup_exc:
                    logger.warning(
                        "Failed to clean up orphaned support attachment %s: %s",
                        attachment_storage_key,
                        cleanup_exc,
                    )
            raise
        self.db.refresh(msg)
        return msg

    def get_messages(
        self, ticket_id: int, current_user: User
    ) -> list[SupportTicketMessage]:
        """Get messages for a ticket. Internal notes hidden from customers (X1-071)."""
        ticket = self.db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        self._check_ticket_access(ticket, current_user)

        query = (
            self.db.query(SupportTicketMessage)
            .filter(SupportTicketMessage.ticket_id == ticket_id)
            .order_by(SupportTicketMessage.created_at.asc())
        )

        # Hide internal notes from customers
        if current_user.id == ticket.customer_id:
            query = query.filter(SupportTicketMessage.is_internal_note.is_(False))

        return query.all()

    # ------------------------------------------------------------------
    # Agent assignment
    # ------------------------------------------------------------------

    def assign_agent(
        self, ticket_id: int, current_user: User, agent_id: int, is_primary: bool = False
    ) -> SupportTicketAssignment:
        """Assign an agent to a ticket (X1-070)."""
        ticket = self._get_ticket_for_agent(ticket_id, current_user)

        agent = self.db.query(User).filter(User.id == agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        if agent.role in (UserRole.CUSTOMER, UserRole.VIEWER):
            raise HTTPException(status_code=400, detail="User does not have agent permissions")
        # Tenant isolation: agent must belong to the same tenant as the ticket
        if agent.role != UserRole.SYSTEM_ADMIN and ticket.tenant_id is not None:
            if agent.tenant_id != ticket.tenant_id:
                raise HTTPException(status_code=403, detail="Agent does not belong to the same tenant as the ticket")

        existing = (
            self.db.query(SupportTicketAssignment)
            .filter_by(ticket_id=ticket_id, agent_id=agent_id)
            .first()
        )
        if existing:
            existing.is_primary = is_primary
            self.db.commit()
            self.db.refresh(existing)
            return existing

        if is_primary:
            # Demote any existing primary
            self.db.query(SupportTicketAssignment).filter_by(
                ticket_id=ticket_id, is_primary=True
            ).update({"is_primary": False})

        assignment = SupportTicketAssignment(
            ticket_id=ticket_id, agent_id=agent_id, is_primary=is_primary
        )
        self.db.add(assignment)

        # Set ticket to IN_PROGRESS if currently OPEN
        if ticket.status == SupportTicketStatus.OPEN:
            ticket.status = SupportTicketStatus.IN_PROGRESS

        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    def unassign_agent(self, ticket_id: int, current_user: User, agent_id: int) -> None:
        """Remove an agent from a ticket."""
        self._get_ticket_for_agent(ticket_id, current_user)

        assignment = (
            self.db.query(SupportTicketAssignment)
            .filter_by(ticket_id=ticket_id, agent_id=agent_id)
            .first()
        )
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        self.db.delete(assignment)
        self.db.commit()

    def handoff_ticket(
        self,
        ticket_id: int,
        current_user: User,
        target_agent_id: int,
        note: str = "",
    ) -> SupportTicketAssignment:
        """Transfer primary ownership to another agent (X1-102)."""
        ticket = self._get_ticket_for_agent(ticket_id, current_user)

        target = self.db.query(User).filter(User.id == target_agent_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="Target agent not found")
        if target.role in (UserRole.CUSTOMER, UserRole.VIEWER):
            raise HTTPException(status_code=400, detail="Target user is not an agent")
        # Tenant isolation: target agent must belong to the same tenant as the ticket
        if target.role != UserRole.SYSTEM_ADMIN and ticket.tenant_id is not None:
            if target.tenant_id != ticket.tenant_id:
                raise HTTPException(status_code=403, detail="Target agent does not belong to the same tenant as the ticket")

        # Demote all existing primaries
        self.db.query(SupportTicketAssignment).filter_by(
            ticket_id=ticket_id, is_primary=True
        ).update({"is_primary": False})

        # Upsert the target agent as primary
        existing = (
            self.db.query(SupportTicketAssignment)
            .filter_by(ticket_id=ticket_id, agent_id=target_agent_id)
            .first()
        )
        if existing:
            existing.is_primary = True
            assignment = existing
        else:
            assignment = SupportTicketAssignment(
                ticket_id=ticket_id, agent_id=target_agent_id, is_primary=True
            )
            self.db.add(assignment)

        # Add handoff system message
        handoff_content = (
            f"{current_user.full_name} transferred this ticket to {target.full_name}."
        )
        if note.strip():
            handoff_content += f"\nHandoff note: {note.strip()}"

        self.db.add(SupportTicketMessage(
            ticket_id=ticket_id,
            sender_id=current_user.id,
            sender_type="agent",
            content=handoff_content,
            is_internal_note=True,
        ))

        # Notify the target agent
        self.db.add(Notification(
            user_id=target_agent_id,
            type=NotificationType.TICKET_HANDOFF,
            title=f"Ticket #{ticket_id} handed off to you",
            message=f"{current_user.full_name} transferred ticket \"{ticket.subject}\" to you."
                    + (f" Note: {note.strip()}" if note.strip() else ""),
            link=f"/support?ticket={ticket_id}",
        ))

        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    # ------------------------------------------------------------------
    # Notifications helpers (X1-087, X1-101)
    # ------------------------------------------------------------------

    def _notify_agents_on_customer_message(
        self, ticket: SupportTicket, customer: User
    ) -> None:
        """Create notifications for assigned agents when customer sends a message (X1-087)."""
        assignments = (
            self.db.query(SupportTicketAssignment)
            .filter(SupportTicketAssignment.ticket_id == ticket.id)
            .all()
        )
        for a in assignments:
            self.db.add(Notification(
                user_id=a.agent_id,
                type=NotificationType.TICKET_NEW_CUSTOMER_MSG,
                title=f"New message on ticket #{ticket.id}",
                message=f"{customer.full_name} sent a message on \"{ticket.subject}\"",
                link=f"/support?ticket={ticket.id}",
            ))

    def _notify_mentions_in_note(
        self, ticket_id: int, sender: User, content: str
    ) -> None:
        """Parse @mentions in internal notes and notify mentioned agents (X1-101)."""
        usernames = list(dict.fromkeys(MENTION_RE.findall(content)))
        if not usernames:
            return
        mentioned = (
            self.db.query(User)
            .filter(
                User.username.in_(usernames),
                User.is_active.is_(True),
                User.id != sender.id,
            )
            .all()
        )
        for u in mentioned:
            if u.role in (UserRole.CUSTOMER, UserRole.VIEWER):
                continue
            self.db.add(Notification(
                user_id=u.id,
                type=NotificationType.TICKET_MENTION,
                title=f"You were mentioned in ticket #{ticket_id}",
                message=f"{sender.full_name} mentioned you: \"{content[:120]}\"",
                link=f"/support?ticket={ticket_id}",
            ))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _check_ticket_access(self, ticket: SupportTicket, user: User) -> None:
        """Enforce role-based and tenant-scoped access."""
        if user.role == UserRole.SYSTEM_ADMIN:
            return
        # Tenant isolation: if user has no tenant, deny access to any tenant's tickets
        if user.tenant_id is None:
            raise HTTPException(status_code=403, detail="Access denied")
        # Tenant isolation: user's tenant must match ticket's tenant
        if ticket.tenant_id is not None and ticket.tenant_id != user.tenant_id:
            raise HTTPException(status_code=403, detail="Access denied")
        if user.role in (UserRole.ADMIN, UserRole.MANAGER, UserRole.EDITOR):
            return
        # Customers/viewers can only see their own tickets
        if ticket.customer_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    def _get_ticket_for_agent(self, ticket_id: int, user: User) -> SupportTicket:
        """Get ticket ensuring user has agent-level access with tenant scoping."""
        ticket = self.db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        if user.role == UserRole.SYSTEM_ADMIN:
            return ticket
        if user.role in (UserRole.ADMIN, UserRole.MANAGER):
            # Deny access if user has no tenant
            if user.tenant_id is None:
                raise HTTPException(status_code=403, detail="Access denied")
            if ticket.tenant_id is not None and ticket.tenant_id != user.tenant_id:
                raise HTTPException(status_code=403, detail="Access denied")
            return ticket
        raise HTTPException(status_code=403, detail="Agent-level access required")
