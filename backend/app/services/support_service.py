"""Support ticket service — customer support chat (Wave X.1)."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

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

MENTION_RE = re.compile(r"(?<!\w)@(\w[\w.-]{0,99})")


class SupportTicketService:
    def __init__(self, db: Session):
        self.db = db

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
        self.db.add(SupportTicketMessage(
            ticket_id=ticket.id,
            sender_id=customer.id,
            sender_type="customer",
            content=content.strip(),
            is_internal_note=False,
        ))

        self.db.commit()
        self.db.refresh(ticket)
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

        # Customers/viewers see only their own tickets; internal staff see all
        if current_user.role in (UserRole.CUSTOMER, UserRole.VIEWER):
            query = query.filter(SupportTicket.customer_id == current_user.id)

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

        if subject is not None:
            ticket.subject = subject.strip()
        if status is not None:
            ticket.status = status
            if status == SupportTicketStatus.RESOLVED:
                ticket.resolved_at = datetime.utcnow()
        if priority is not None:
            ticket.priority = priority
        if category is not None:
            ticket.category = category.strip() if category else None

        self.db.commit()
        self.db.refresh(ticket)
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
    ) -> SupportTicketMessage:
        """Send a message on a ticket (X1-071)."""
        ticket = self.db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        self._check_ticket_access(ticket, sender)

        # Determine sender_type
        if sender.id == ticket.customer_id:
            sender_type = "customer"
            if is_internal_note:
                raise HTTPException(status_code=403, detail="Customers cannot create internal notes")
        else:
            sender_type = "agent"

        msg = SupportTicketMessage(
            ticket_id=ticket_id,
            sender_id=sender.id,
            sender_type=sender_type,
            content=content.strip(),
            is_internal_note=is_internal_note,
        )
        self.db.add(msg)

        # Auto-reopen if customer sends message on resolved ticket
        if sender_type == "customer" and ticket.status == SupportTicketStatus.RESOLVED:
            ticket.status = SupportTicketStatus.OPEN
            ticket.resolved_at = None

        # Notifications (X1-087, X1-101)
        if sender_type == "customer":
            self._notify_agents_on_customer_message(ticket, sender)
        if is_internal_note:
            self._notify_mentions_in_note(ticket_id, sender, content)

        self.db.commit()
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
        """Enforce role-based access. Internal staff can access all tickets."""
        if user.role in (UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER, UserRole.EDITOR):
            return
        # Customers/viewers can only see their own tickets
        if ticket.customer_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    def _get_ticket_for_agent(self, ticket_id: int, user: User) -> SupportTicket:
        """Get ticket ensuring user has agent-level access."""
        ticket = self.db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        if user.role in (UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER, UserRole.EDITOR):
            return ticket
        raise HTTPException(status_code=403, detail="Agent-level access required")
