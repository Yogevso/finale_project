"""Support ticket service — customer support chat (Wave X.1)."""

from __future__ import annotations

import io
import json
import logging
import re
from datetime import datetime, timedelta
from html import escape
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.errors import (
    NotFoundError,
    PermissionDeniedError,
    ServiceUnavailableError,
    ValidationError,
)
from app.models import (
    Attachment,
    Comment,
    Document,
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
    Version,
)
from app.repositories import SupportTicketRepository, UserRepository
from app.services.attachment_service.common import AttachmentServiceCommonMixin
from app.services.email_service import email_service
from app.services.malware_scan_service import (
    MalwareDetectedError,
    MalwareScannerUnavailableError,
    scan_upload_bytes,
)
from app.services.notification_service import NotificationService
from app.services.storage_service import get_storage_backend
from app.utils.async_tasks import run_async_task
from app.utils.sanitization import sanitize_html_content

MENTION_RE = re.compile(r"(?<!\w)@(\w[\w.-]{0,99})")
logger = logging.getLogger(__name__)

# H-27: Support ticket state machine — allowed transitions per role category.
_STAFF_TRANSITIONS: dict[SupportTicketStatus, set[SupportTicketStatus]] = {
    SupportTicketStatus.OPEN: {SupportTicketStatus.IN_PROGRESS, SupportTicketStatus.CLOSED},
    SupportTicketStatus.IN_PROGRESS: {
        SupportTicketStatus.RESOLVED,
        SupportTicketStatus.OPEN,
        SupportTicketStatus.CLOSED,
    },
    SupportTicketStatus.RESOLVED: {SupportTicketStatus.CLOSED, SupportTicketStatus.IN_PROGRESS},
    SupportTicketStatus.CLOSED: set(),  # staff cannot reopen closed tickets
}

_CUSTOMER_TRANSITIONS: dict[SupportTicketStatus, set[SupportTicketStatus]] = {
    SupportTicketStatus.OPEN: {SupportTicketStatus.CLOSED},
    SupportTicketStatus.IN_PROGRESS: set(),
    SupportTicketStatus.RESOLVED: {SupportTicketStatus.CLOSED, SupportTicketStatus.OPEN},
    SupportTicketStatus.CLOSED: set(),
}

_SUPPORT_NOTIFICATION_TYPES: tuple[NotificationType, ...] = (
    NotificationType.TICKET_NEW_CUSTOMER_MSG,
    NotificationType.TICKET_HANDOFF,
    NotificationType.TICKET_MENTION,
)
_SUPPORT_NEEDS_ATTENTION_WINDOW = timedelta(hours=24)


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

    def __init__(self, db: Session, chat_db: Session | None = None):
        self.db = db
        self.chat_db = chat_db or db
        self.ticket_repository = SupportTicketRepository(db)
        self.user_repository = UserRepository(db)
        self.notification_service = NotificationService(db, chat_db=self.chat_db)

    @staticmethod
    def _sanitize_message_content(content: str, *, allow_empty: bool = False) -> str:
        normalized_content = (content or "").strip()
        if not normalized_content:
            if allow_empty:
                return ""
            raise ValidationError("content is empty after sanitization")
        sanitized_content = (sanitize_html_content(normalized_content) or "").strip()
        if not sanitized_content:
            raise ValidationError("content is empty after sanitization")
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

    @staticmethod
    def _feedback_management_link(feedback_id: int) -> str:
        return f"/admin/feedback?feedback={feedback_id}"

    @staticmethod
    def _feedback_customer_link(feedback_id: int) -> str:
        return f"/portal/feedback?feedback={feedback_id}"

    def _feedback_ticket_subject(self, feedback: Feedback) -> str:
        document_title: str | None = None
        if getattr(feedback, "document", None) is not None and feedback.document is not None:
            document_title = feedback.document.title
        if not document_title:
            document = self.db.query(Document).filter(Document.id == feedback.document_id).first()
            document_title = document.title if document else f"Document #{feedback.document_id}"

        type_label = feedback.feedback_type.value.replace("_", " ").title()
        subject = f"{type_label} feedback: {document_title}".strip()
        return subject[:500]

    def _feedback_document_title(self, feedback: Feedback) -> str:
        if getattr(feedback, "document", None) is not None and feedback.document is not None:
            return feedback.document.title

        document = self.db.query(Document).filter(Document.id == feedback.document_id).first()
        return document.title if document else f"Document #{feedback.document_id}"

    def _feedback_contributor_user_ids(self, document_id: int) -> set[int]:
        contributor_ids: set[int] = set()

        document = self.db.query(Document).filter(Document.id == document_id).first()
        if document and document.created_by:
            contributor_ids.add(document.created_by)

        for (user_id,) in (
            self.db.query(Version.created_by)
            .filter(Version.document_id == document_id)
            .distinct()
            .all()
        ):
            if user_id:
                contributor_ids.add(user_id)

        for (user_id,) in (
            self.db.query(Attachment.uploaded_by)
            .filter(Attachment.document_id == document_id)
            .distinct()
            .all()
        ):
            if user_id:
                contributor_ids.add(user_id)

        for (user_id,) in (
            self.db.query(Comment.user_id)
            .filter(Comment.document_id == document_id)
            .distinct()
            .all()
        ):
            if user_id:
                contributor_ids.add(user_id)

        return contributor_ids

    def _list_feedback_notification_recipients(
        self,
        *,
        feedback: Feedback,
        tenant_id: int | None,
        exclude_user_id: int | None = None,
    ) -> list[User]:
        recipients: dict[int, User] = {}

        contributor_ids = self._feedback_contributor_user_ids(feedback.document_id)
        for user in self.user_repository.list_by_ids(list(contributor_ids)):
            if not user.is_active:
                continue
            if exclude_user_id is not None and user.id == exclude_user_id:
                continue
            if user.role in (UserRole.CUSTOMER, UserRole.VIEWER):
                continue
            if (
                user.role != UserRole.SYSTEM_ADMIN
                and tenant_id is not None
                and user.tenant_id != tenant_id
            ):
                continue
            recipients[user.id] = user

        for user in self.user_repository.list_active_by_roles(
            [UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER],
            tenant_id=tenant_id,
            exclude_user_id=exclude_user_id,
        ):
            recipients[user.id] = user

        return list(recipients.values())

    def notify_feedback_received(
        self,
        *,
        feedback: Feedback,
        customer: User,
    ) -> None:
        document_title = self._feedback_document_title(feedback)
        type_label = feedback.feedback_type.value.replace("_", " ")
        recipients = self._list_feedback_notification_recipients(
            feedback=feedback,
            tenant_id=customer.tenant_id,
            exclude_user_id=customer.id,
        )
        for recipient in recipients:
            self.notification_service.create_notification(
                user_id=recipient.id,
                notification_type=NotificationType.FEEDBACK_RECEIVED,
                title=f'New feedback on "{document_title}"',
                message=f"{customer.full_name} submitted {type_label} feedback.",
                link=self._feedback_management_link(feedback.id),
            )

    def notify_feedback_responded(
        self,
        *,
        feedback: Feedback,
        agent: User,
    ) -> None:
        self.notification_service.create_notification(
            user_id=feedback.user_id,
            notification_type=NotificationType.FEEDBACK_RESPONDED,
            title="New response to your feedback",
            message=f'{agent.full_name} replied about "{self._feedback_document_title(feedback)}".',
            link=self._feedback_customer_link(feedback.id),
        )

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
        recipients = self.ticket_repository.list_assigned_active_agents(
            ticket.id,
            exclude_user_id=exclude_user_id,
        )
        if recipients:
            return recipients

        support_roles = [UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER]
        return self.user_repository.list_active_by_roles(
            support_roles,
            tenant_id=ticket.tenant_id,
            exclude_user_id=exclude_user_id,
        )

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
            self.notification_service.create_notification(
                user_id=recipient.id,
                notification_type=NotificationType.TICKET_NEW_CUSTOMER_MSG,
                title=f"New support ticket #{ticket.id}",
                message=f'{customer.full_name} opened "{ticket.subject}"',
                link=f"/support?ticket={ticket.id}",
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
                    f'<p><a href="{ticket_url}">Open ticket</a></p>'
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
                    f'<p><a href="{ticket_url}">Open ticket</a></p>'
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
        self.notification_service.create_notification(
            user_id=ticket.customer_id,
            notification_type=NotificationType.SYSTEM,
            title=f"New reply on ticket #{ticket.id}",
            message=f'{agent.full_name} replied to "{ticket.subject}".',
            link=f"/portal/support?ticket={ticket.id}",
        )

    def _email_customer_on_agent_reply(
        self,
        *,
        ticket: SupportTicket,
        agent: User,
        message_content: str,
    ) -> None:
        customer = ticket.customer or self.user_repository.get_by_id(ticket.customer_id)
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
                f'<p><a href="{ticket_url}">View ticket</a></p>'
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
        customer = ticket.customer or self.user_repository.get_by_id(ticket.customer_id)
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
                f'<p><a href="{ticket_url}">View ticket</a></p>'
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
            raise ValidationError(f"File type not allowed: {normalized_type}")

        if len(file_bytes) > settings.MAX_UPLOAD_SIZE:
            raise ValidationError(
                f"File too large. Max size: {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB"
            )

        AttachmentServiceCommonMixin._validate_magic_bytes(
            file_bytes,
            normalized_name,
            normalized_type,
        )
        try:
            scan_upload_bytes(file_bytes, normalized_name, normalized_type)
        except MalwareDetectedError as exc:
            raise ValidationError(str(exc)) from exc
        except MalwareScannerUnavailableError as exc:
            raise ServiceUnavailableError(str(exc)) from exc

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
        ticket = self.ticket_repository.get_by_id(ticket_id)
        if not ticket:
            raise NotFoundError("Ticket not found")
        self._check_ticket_access(ticket, current_user)

        message = self.ticket_repository.get_message(ticket_id, message_id)
        if not message or not message.file_storage_key:
            raise NotFoundError("Attachment not found")
        if message.is_internal_note and current_user.id == ticket.customer_id:
            raise NotFoundError("Attachment not found")

        try:
            content = get_storage_backend().download(message.file_storage_key)
        except FileNotFoundError as exc:
            raise NotFoundError("Attachment not found") from exc
        except (
            Exception
        ) as exc:  # policy: BOUNDARY — attachment download failure becomes a stable HTTP error
            logger.warning(
                "Failed to download support attachment %s for message %s: %s",
                message.file_storage_key,
                message.id,
                exc,
            )
            raise ServiceUnavailableError("Attachment temporarily unavailable") from exc

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
            fb = (
                self.db.query(Feedback)
                .filter(Feedback.id == feedback_id, Feedback.user_id == customer.id)
                .first()
            )
            if not fb:
                raise NotFoundError("Feedback not found")

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
        self.db.add(
            SupportTicketMessage(
                ticket_id=ticket.id,
                sender_id=customer.id,
                sender_type="customer",
                content=initial_message_content,
                is_internal_note=False,
            )
        )
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
        fb = self.db.query(Feedback).filter(Feedback.id == feedback_id).first()
        if not fb:
            raise NotFoundError("Feedback not found")

        if customer.role in (UserRole.CUSTOMER, UserRole.VIEWER):
            if fb.user_id != customer.id:
                raise PermissionDeniedError("Access denied")
        elif customer.role != UserRole.SYSTEM_ADMIN:
            customer_record = fb.user or self.user_repository.get_by_id(fb.user_id)
            if customer_record is None:
                raise NotFoundError("Customer not found")
            if customer.tenant_id is None or customer_record.tenant_id != customer.tenant_id:
                raise PermissionDeniedError("Access denied")

        return self.get_or_create_feedback_ticket(fb)

    def get_or_create_feedback_ticket(self, feedback: Feedback) -> SupportTicket:
        """Return the support ticket linked to feedback, creating it on first use."""
        existing = self.ticket_repository.get_by_feedback_id(feedback.id)
        if existing:
            return existing

        customer = feedback.user or self.user_repository.get_by_id(feedback.user_id)
        if customer is None:
            raise NotFoundError("Customer not found")

        return self.create_ticket(
            customer=customer,
            subject=self._feedback_ticket_subject(feedback),
            content=self._feedback_ticket_initial_message(feedback),
            category=feedback.feedback_type.value,
            feedback_id=feedback.id,
        )

    @staticmethod
    def _feedback_ticket_initial_message(feedback: Feedback) -> str:
        excerpt = " ".join((feedback.anchor_text or "").split()).strip()
        if not excerpt:
            return feedback.content
        return f'Selected text: "{excerpt}"\n\n{feedback.content}'

    def get_ticket_activity_map(
        self,
        current_user: User,
        tickets: list[SupportTicket],
    ) -> dict[int, dict[str, object]]:
        if not tickets:
            return {}

        ticket_ids = [ticket.id for ticket in tickets]
        public_messages = (
            self.db.query(SupportTicketMessage)
            .filter(
                SupportTicketMessage.ticket_id.in_(ticket_ids),
                SupportTicketMessage.is_internal_note.is_(False),
            )
            .order_by(SupportTicketMessage.ticket_id.asc(), SupportTicketMessage.created_at.asc())
            .all()
        )

        message_state: dict[int, dict[str, object]] = {
            ticket_id: {
                "last_customer_message_at": None,
                "latest_sender_type": None,
            }
            for ticket_id in ticket_ids
        }
        for message in public_messages:
            state = message_state.setdefault(
                message.ticket_id,
                {"last_customer_message_at": None, "latest_sender_type": None},
            )
            if message.sender_type == "customer":
                state["last_customer_message_at"] = message.created_at
            state["latest_sender_type"] = message.sender_type

        ticket_links = {f"/support?ticket={ticket_id}": ticket_id for ticket_id in ticket_ids}
        unread_ticket_ids = {
            ticket_links[link]
            for (link,) in self.chat_db.query(Notification.link)
            .filter(
                Notification.user_id == current_user.id,
                Notification.is_read.is_(False),
                Notification.type.in_(list(_SUPPORT_NOTIFICATION_TYPES)),
                Notification.link.in_(list(ticket_links.keys())),
            )
            .all()
            if link in ticket_links
        }

        now = datetime.utcnow()
        indicators: dict[int, dict[str, object]] = {}
        for ticket in tickets:
            state = message_state.get(ticket.id, {})
            last_customer_message_at = state.get("last_customer_message_at")
            latest_sender_type = state.get("latest_sender_type")
            awaiting_agent_reply = (
                latest_sender_type == "customer" and ticket.status != SupportTicketStatus.CLOSED
            )
            needs_attention = (
                ticket.status in (SupportTicketStatus.OPEN, SupportTicketStatus.IN_PROGRESS)
                and isinstance(last_customer_message_at, datetime)
                and (now - last_customer_message_at) <= _SUPPORT_NEEDS_ATTENTION_WINDOW
            )
            indicators[ticket.id] = {
                "has_unread_activity": ticket.id in unread_ticket_ids,
                "awaiting_agent_reply": awaiting_agent_reply,
                "needs_attention": needs_attention,
                "last_customer_message_at": last_customer_message_at,
            }

        return indicators

    def get_ticket_summary(self, current_user: User) -> dict[str, int]:
        tickets = self.ticket_repository.list_all_visible_to_user(current_user)
        indicators = self.get_ticket_activity_map(current_user, tickets)

        unread_ticket_ids = {
            ticket_id for ticket_id, item in indicators.items() if bool(item["has_unread_activity"])
        }
        customer_reply_ticket_ids = {
            ticket_id
            for ticket_id, item in indicators.items()
            if bool(item["awaiting_agent_reply"])
        }
        needs_attention_ticket_ids = {
            ticket_id for ticket_id, item in indicators.items() if bool(item["needs_attention"])
        }
        nav_ticket_ids = unread_ticket_ids | customer_reply_ticket_ids | needs_attention_ticket_ids

        return {
            "unread_count": len(unread_ticket_ids),
            "customer_reply_count": len(customer_reply_ticket_ids),
            "needs_attention_count": len(needs_attention_ticket_ids),
            "nav_badge_count": len(nav_ticket_ids),
        }

    # ------------------------------------------------------------------
    # Ticket queries
    # ------------------------------------------------------------------

    def get_ticket(self, ticket_id: int, current_user: User) -> SupportTicket:
        """Get ticket with messages and assignments (X1-068)."""
        ticket = self.ticket_repository.get_by_id_with_detail(ticket_id)
        if not ticket:
            raise NotFoundError("Ticket not found")

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
        return self.ticket_repository.list_visible_to_user(
            current_user,
            status_filter=status_filter,
            page=page,
            page_size=page_size,
        )

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
                raise ValidationError(
                    f"Cannot transition from {ticket.status.value} to {status.value}"
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
        ticket = self.ticket_repository.get_by_id(ticket_id)
        if not ticket:
            raise NotFoundError("Ticket not found")
        if ticket.customer_id != customer.id:
            raise PermissionDeniedError("Access denied")
        if ticket.status not in (SupportTicketStatus.RESOLVED, SupportTicketStatus.OPEN):
            raise ValidationError("Only resolved or open tickets can be closed")
        ticket.status = SupportTicketStatus.CLOSED
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def delete_ticket(self, ticket_id: int, current_user: User) -> None:
        """Delete a closed ticket. Only managers/admins can delete, and only if ticket is closed."""
        ticket = self.ticket_repository.get_by_id(ticket_id)
        if not ticket:
            raise NotFoundError("Ticket not found")
        if ticket.status != SupportTicketStatus.CLOSED:
            raise ValidationError("Only closed tickets can be deleted")
        self.db.delete(ticket)
        self.db.commit()

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
        ticket = self.ticket_repository.get_by_id(ticket_id)
        if not ticket:
            raise NotFoundError("Ticket not found")
        self._check_ticket_access(ticket, sender)

        # M-48: Prevent messaging on closed tickets
        if ticket.status == SupportTicketStatus.CLOSED:
            raise ValidationError("Cannot send messages on closed tickets")

        # Determine sender_type
        if sender.id == ticket.customer_id:
            sender_type = "customer"
            if is_internal_note:
                raise PermissionDeniedError("Customers cannot create internal notes")
        else:
            sender_type = "agent"

        has_attachment = file_bytes is not None
        if not (content or "").strip() and not has_attachment:
            raise ValidationError("content or file is required")

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
            self._notify_mentions_in_note(ticket, sender, content)
        else:
            self._notify_customer_on_agent_reply(ticket=ticket, agent=sender)
            self._email_customer_on_agent_reply(
                ticket=ticket,
                agent=sender,
                message_content=sanitized_content,
            )

        try:
            self.db.commit()
        except Exception:  # policy: COMPENSATING — message persistence failure must clean up orphaned attachment state
            if attachment_storage_key:
                try:
                    get_storage_backend().delete(attachment_storage_key)
                except Exception as cleanup_exc:  # policy: COMPENSATING — orphan cleanup is best-effort during rollback
                    logger.warning(
                        "Failed to clean up orphaned support attachment %s: %s",
                        attachment_storage_key,
                        cleanup_exc,
                    )
            raise
        self.db.refresh(msg)
        return msg

    def get_messages(self, ticket_id: int, current_user: User) -> list[SupportTicketMessage]:
        """Get messages for a ticket. Internal notes hidden from customers (X1-071)."""
        ticket = self.ticket_repository.get_by_id(ticket_id)
        if not ticket:
            raise NotFoundError("Ticket not found")
        self._check_ticket_access(ticket, current_user)
        return self.ticket_repository.list_messages(
            ticket_id,
            include_internal_notes=current_user.id != ticket.customer_id,
        )

    # ------------------------------------------------------------------
    # Agent assignment
    # ------------------------------------------------------------------

    def assign_agent(
        self, ticket_id: int, current_user: User, agent_id: int, is_primary: bool = False
    ) -> SupportTicketAssignment:
        """Assign an agent to a ticket (X1-070)."""
        ticket = self._get_ticket_for_agent(ticket_id, current_user)

        agent = self.user_repository.get_by_id(agent_id)
        if not agent:
            raise NotFoundError("Agent not found")
        if agent.role in (UserRole.CUSTOMER, UserRole.VIEWER):
            raise ValidationError("User does not have agent permissions")
        # Tenant isolation: agent must belong to the same tenant as the ticket
        if agent.role != UserRole.SYSTEM_ADMIN and ticket.tenant_id is not None:
            if agent.tenant_id != ticket.tenant_id:
                raise PermissionDeniedError(
                    "Agent does not belong to the same tenant as the ticket"
                )

        existing = self.ticket_repository.get_assignment(ticket_id, agent_id)
        if existing:
            existing.is_primary = is_primary
            self.db.commit()
            self.db.refresh(existing)
            return existing

        if is_primary:
            self.ticket_repository.demote_primary_assignments(ticket_id)

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

        assignment = self.ticket_repository.get_assignment(ticket_id, agent_id)
        if not assignment:
            raise NotFoundError("Assignment not found")

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

        target = self.user_repository.get_by_id(target_agent_id)
        if not target:
            raise NotFoundError("Target agent not found")
        if target.role in (UserRole.CUSTOMER, UserRole.VIEWER):
            raise ValidationError("Target user is not an agent")
        # Tenant isolation: target agent must belong to the same tenant as the ticket
        if target.role != UserRole.SYSTEM_ADMIN and ticket.tenant_id is not None:
            if target.tenant_id != ticket.tenant_id:
                raise PermissionDeniedError(
                    "Target agent does not belong to the same tenant as the ticket"
                )

        # Demote all existing primaries
        self.ticket_repository.demote_primary_assignments(ticket_id)

        existing = self.ticket_repository.get_assignment(ticket_id, target_agent_id)
        if existing:
            existing.is_primary = True
            assignment = existing
        else:
            assignment = SupportTicketAssignment(
                ticket_id=ticket_id, agent_id=target_agent_id, is_primary=True
            )
            self.db.add(assignment)

        # Add handoff system message
        handoff_content = f"{current_user.full_name} transferred this ticket to {target.full_name}."
        if note.strip():
            handoff_content += f"\nHandoff note: {note.strip()}"

        self.db.add(
            SupportTicketMessage(
                ticket_id=ticket_id,
                sender_id=current_user.id,
                sender_type="agent",
                content=handoff_content,
                is_internal_note=True,
            )
        )

        # Notify the target agent
        self.notification_service.create_notification(
            user_id=target_agent_id,
            notification_type=NotificationType.TICKET_HANDOFF,
            title=f"Ticket #{ticket_id} handed off to you",
            message=f'{current_user.full_name} transferred ticket "{ticket.subject}" to you.'
            + (f" Note: {note.strip()}" if note.strip() else ""),
            link=f"/support?ticket={ticket_id}",
        )

        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    # ------------------------------------------------------------------
    # Notifications helpers (X1-087, X1-101)
    # ------------------------------------------------------------------

    def _notify_agents_on_customer_message(self, ticket: SupportTicket, customer: User) -> None:
        """Create notifications for the responsible internal recipients (X1-087)."""
        for recipient in self._list_support_notification_recipients(
            ticket,
            exclude_user_id=customer.id,
        ):
            self.notification_service.create_notification(
                user_id=recipient.id,
                notification_type=NotificationType.TICKET_NEW_CUSTOMER_MSG,
                title=f"New message on ticket #{ticket.id}",
                message=f'{customer.full_name} sent a message on "{ticket.subject}"',
                link=f"/support?ticket={ticket.id}",
            )

    def _notify_mentions_in_note(self, ticket: SupportTicket, sender: User, content: str) -> None:
        """Parse @mentions in internal notes and notify mentioned agents (X1-101)."""
        usernames = list(dict.fromkeys(MENTION_RE.findall(content)))
        if not usernames:
            return
        mentioned = self.user_repository.list_active_by_usernames(
            usernames,
            tenant_id=ticket.tenant_id,
            exclude_user_id=sender.id,
        )
        for u in mentioned:
            if u.role in (UserRole.CUSTOMER, UserRole.VIEWER):
                continue
            self.notification_service.create_notification(
                user_id=u.id,
                notification_type=NotificationType.TICKET_MENTION,
                title=f"You were mentioned in ticket #{ticket.id}",
                message=f'{sender.full_name} mentioned you: "{content[:120]}"',
                link=f"/support?ticket={ticket.id}",
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _check_ticket_access(self, ticket: SupportTicket, user: User) -> None:
        """Enforce role-based and tenant-scoped access."""
        if user.role == UserRole.SYSTEM_ADMIN:
            return
        # Tenant isolation: if user has no tenant, deny access to any tenant's tickets
        if user.tenant_id is None:
            raise PermissionDeniedError("Access denied")
        # Tenant isolation: user's tenant must match ticket's tenant
        if ticket.tenant_id is not None and ticket.tenant_id != user.tenant_id:
            raise PermissionDeniedError("Access denied")
        if user.role in (UserRole.ADMIN, UserRole.MANAGER, UserRole.EDITOR):
            return
        # Customers/viewers can only see their own tickets
        if ticket.customer_id != user.id:
            raise PermissionDeniedError("Access denied")

    def _get_ticket_for_agent(self, ticket_id: int, user: User) -> SupportTicket:
        """Get ticket ensuring user has agent-level access with tenant scoping."""
        ticket = self.ticket_repository.get_by_id(ticket_id)
        if not ticket:
            raise NotFoundError("Ticket not found")
        if user.role == UserRole.SYSTEM_ADMIN:
            return ticket
        if user.role in (UserRole.ADMIN, UserRole.MANAGER):
            # Deny access if user has no tenant
            if user.tenant_id is None:
                raise PermissionDeniedError("Access denied")
            if ticket.tenant_id is not None and ticket.tenant_id != user.tenant_id:
                raise PermissionDeniedError("Access denied")
            return ticket
        raise PermissionDeniedError("Agent-level access required")
