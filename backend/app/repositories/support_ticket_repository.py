"""Repository for support ticket aggregate access patterns."""

from __future__ import annotations

from sqlalchemy.orm import joinedload

from app.models import (
    SupportTicket,
    SupportTicketAssignment,
    SupportTicketMessage,
    SupportTicketStatus,
    User,
    UserRole,
)
from app.repositories.base import BaseRepository


class SupportTicketRepository(BaseRepository):
    """Support ticket persistence/query access."""

    def get_by_id(self, ticket_id: int) -> SupportTicket | None:
        return self.db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()

    def get_by_id_with_detail(self, ticket_id: int) -> SupportTicket | None:
        return (
            self.db.query(SupportTicket)
            .options(
                joinedload(SupportTicket.messages),
                joinedload(SupportTicket.assignments),
                joinedload(SupportTicket.customer),
            )
            .filter(SupportTicket.id == ticket_id)
            .first()
        )

    def get_by_feedback_id(self, feedback_id: int) -> SupportTicket | None:
        return self.db.query(SupportTicket).filter(SupportTicket.feedback_id == feedback_id).first()

    def list_visible_to_user(
        self,
        current_user: User,
        *,
        status_filter: SupportTicketStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[SupportTicket], int]:
        query = self.db.query(SupportTicket).options(joinedload(SupportTicket.customer))

        if current_user.role in (UserRole.CUSTOMER, UserRole.VIEWER):
            query = query.filter(SupportTicket.customer_id == current_user.id)
        elif current_user.role != UserRole.SYSTEM_ADMIN:
            if current_user.tenant_id is None:
                query = query.filter(SupportTicket.id == -1)
            else:
                query = query.filter(SupportTicket.tenant_id == current_user.tenant_id)

        if status_filter:
            query = query.filter(SupportTicket.status == status_filter)

        total = query.count()
        items = (
            query.order_by(SupportTicket.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def get_message(self, ticket_id: int, message_id: int) -> SupportTicketMessage | None:
        return (
            self.db.query(SupportTicketMessage)
            .filter(
                SupportTicketMessage.id == message_id,
                SupportTicketMessage.ticket_id == ticket_id,
            )
            .first()
        )

    def list_messages(
        self,
        ticket_id: int,
        *,
        include_internal_notes: bool = True,
    ) -> list[SupportTicketMessage]:
        query = (
            self.db.query(SupportTicketMessage)
            .filter(SupportTicketMessage.ticket_id == ticket_id)
            .order_by(SupportTicketMessage.created_at.asc())
        )
        if not include_internal_notes:
            query = query.filter(SupportTicketMessage.is_internal_note.is_(False))
        return query.all()

    def get_assignment(
        self,
        ticket_id: int,
        agent_id: int,
    ) -> SupportTicketAssignment | None:
        return (
            self.db.query(SupportTicketAssignment)
            .filter_by(ticket_id=ticket_id, agent_id=agent_id)
            .first()
        )

    def list_assignments(self, ticket_id: int) -> list[SupportTicketAssignment]:
        return (
            self.db.query(SupportTicketAssignment)
            .filter(SupportTicketAssignment.ticket_id == ticket_id)
            .all()
        )

    def demote_primary_assignments(self, ticket_id: int) -> None:
        self.db.query(SupportTicketAssignment).filter_by(
            ticket_id=ticket_id,
            is_primary=True,
        ).update({"is_primary": False})

    def list_assigned_active_agents(
        self,
        ticket_id: int,
        *,
        exclude_user_id: int | None = None,
    ) -> list[User]:
        query = (
            self.db.query(User)
            .join(
                SupportTicketAssignment,
                SupportTicketAssignment.agent_id == User.id,
            )
            .filter(
                SupportTicketAssignment.ticket_id == ticket_id,
                User.is_active.is_(True),
            )
        )
        if exclude_user_id is not None:
            query = query.filter(User.id != exclude_user_id)
        return query.all()
