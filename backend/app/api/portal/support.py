"""Portal Support API — customer-facing support ticket endpoints (X1-072 to X1-075)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import SupportTicketStatus, User, UserRole
from app.schemas.chat import (
    SendTicketMessageRequest,
    SupportTicketCreate,
    SupportTicketDetailResponse,
    SupportTicketListResponse,
    SupportTicketMessageResponse,
    SupportTicketResponse,
)
from app.security import get_current_active_user
from app.services.support_service import SupportTicketService

router = APIRouter(prefix="/portal/support", tags=["Customer Support"])


def _require_customer(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role != UserRole.CUSTOMER:
        raise HTTPException(status_code=403, detail="This endpoint is only for customer users.")
    return current_user


def _get_svc(db: Session = Depends(get_db)) -> SupportTicketService:
    return SupportTicketService(db)


@router.get("/tickets", response_model=SupportTicketListResponse)
def list_my_tickets(
    status_filter: SupportTicketStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(_require_customer),
    svc: SupportTicketService = Depends(_get_svc),
):
    """List customer's own support tickets (X1-072)."""
    tickets, total = svc.list_tickets(current_user, status_filter=status_filter, page=page, page_size=page_size)
    return SupportTicketListResponse(
        items=[
            SupportTicketResponse(
                id=t.id, customer_id=t.customer_id, subject=t.subject,
                status=t.status, priority=t.priority, category=t.category,
                feedback_id=t.feedback_id, tenant_id=t.tenant_id,
                created_at=t.created_at, updated_at=t.updated_at, resolved_at=t.resolved_at,
            )
            for t in tickets
        ],
        total=total, page=page, page_size=page_size,
    )


@router.get("/tickets/{ticket_id}", response_model=SupportTicketDetailResponse)
def get_my_ticket(
    ticket_id: int,
    current_user: User = Depends(_require_customer),
    svc: SupportTicketService = Depends(_get_svc),
):
    """Get ticket detail with messages — internal notes excluded (X1-073)."""
    ticket = svc.get_ticket(ticket_id, current_user)
    # Filter out internal notes
    visible_messages = [m for m in ticket.messages if not m.is_internal_note]
    return SupportTicketDetailResponse(
        id=ticket.id, customer_id=ticket.customer_id, subject=ticket.subject,
        status=ticket.status, priority=ticket.priority, category=ticket.category,
        feedback_id=ticket.feedback_id, tenant_id=ticket.tenant_id,
        created_at=ticket.created_at, updated_at=ticket.updated_at, resolved_at=ticket.resolved_at,
        messages=[
            SupportTicketMessageResponse(
                id=m.id, ticket_id=m.ticket_id, sender_id=m.sender_id,
                sender_type=m.sender_type, content=m.content,
                is_internal_note=m.is_internal_note, created_at=m.created_at,
            )
            for m in visible_messages
        ],
        assignments=[],
    )


@router.post("/tickets", response_model=SupportTicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(
    body: SupportTicketCreate,
    current_user: User = Depends(_require_customer),
    svc: SupportTicketService = Depends(_get_svc),
):
    """Create a new support ticket (X1-072)."""
    ticket = svc.create_ticket(
        customer=current_user, subject=body.subject, content=body.content,
        priority=body.priority, category=body.category, feedback_id=body.feedback_id,
    )
    return SupportTicketResponse(
        id=ticket.id, customer_id=ticket.customer_id, subject=ticket.subject,
        status=ticket.status, priority=ticket.priority, category=ticket.category,
        feedback_id=ticket.feedback_id, tenant_id=ticket.tenant_id,
        created_at=ticket.created_at, updated_at=ticket.updated_at, resolved_at=ticket.resolved_at,
    )


@router.post("/tickets/{ticket_id}/messages", response_model=SupportTicketMessageResponse, status_code=status.HTTP_201_CREATED)
def send_message(
    ticket_id: int,
    body: SendTicketMessageRequest,
    current_user: User = Depends(_require_customer),
    svc: SupportTicketService = Depends(_get_svc),
):
    """Customer sends a message on a ticket (X1-074)."""
    msg = svc.send_message(ticket_id, current_user, body.content, is_internal_note=False)
    return SupportTicketMessageResponse(
        id=msg.id, ticket_id=msg.ticket_id, sender_id=msg.sender_id,
        sender_type=msg.sender_type, content=msg.content,
        is_internal_note=msg.is_internal_note, created_at=msg.created_at,
    )


@router.post("/tickets/{ticket_id}/close", status_code=status.HTTP_204_NO_CONTENT)
def close_ticket(
    ticket_id: int,
    current_user: User = Depends(_require_customer),
    svc: SupportTicketService = Depends(_get_svc),
):
    """Customer closes a resolved ticket (X1-075)."""
    svc.close_ticket_as_customer(ticket_id, current_user)
