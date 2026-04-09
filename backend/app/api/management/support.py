"""Support ticket API endpoints — customer support (Wave X.1)."""

from __future__ import annotations

import asyncio
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.support_message_utils import (
    parse_support_message_request,
    support_message_to_response,
)
from app.db import get_db
from app.dependencies.permissions import require_internal_user, require_manager
from app.dependencies.services import get_support_ticket_service
from app.models import SupportTicketStatus, User
from app.schemas.chat import (
    AssignAgentRequest,
    HandoffRequest,
    SupportTicketAssignmentResponse,
    SupportTicketCreate,
    SupportTicketDetailResponse,
    SupportTicketListResponse,
    SupportTicketMessageResponse,
    SupportTicketResponse,
    SupportTicketSummaryResponse,
    SupportTicketUpdate,
)
from app.security import get_current_active_user
from app.utils.async_tasks import run_async_task
from app.ws.manager import chat_manager

router = APIRouter()


def _ticket_to_response(t, indicators: dict[str, object] | None = None) -> SupportTicketResponse:
    indicators = indicators or {}
    return SupportTicketResponse(
        id=t.id,
        customer_id=t.customer_id,
        subject=t.subject,
        status=t.status,
        priority=t.priority,
        category=t.category,
        feedback_id=t.feedback_id,
        tenant_id=t.tenant_id,
        created_at=t.created_at,
        updated_at=t.updated_at,
        resolved_at=t.resolved_at,
        customer_full_name=t.customer.full_name if t.customer else None,
        last_customer_message_at=indicators.get("last_customer_message_at"),
        has_unread_activity=bool(indicators.get("has_unread_activity", False)),
        awaiting_agent_reply=bool(indicators.get("awaiting_agent_reply", False)),
        needs_attention=bool(indicators.get("needs_attention", False)),
    )


def _msg_to_response(m) -> SupportTicketMessageResponse:
    return support_message_to_response(m)


# ---- Tickets ----


@router.get("/support/tickets", response_model=SupportTicketListResponse)
def list_tickets(
    status_filter: SupportTicketStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_internal_user),
    svc = Depends(get_support_ticket_service),
):
    """List support tickets visible to the current user."""
    tickets, total = svc.list_tickets(current_user, status_filter=status_filter, page=page, page_size=page_size)
    indicators = svc.get_ticket_activity_map(current_user, tickets)
    return SupportTicketListResponse(
        items=[_ticket_to_response(t, indicators.get(t.id)) for t in tickets],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/support/tickets/summary", response_model=SupportTicketSummaryResponse)
def get_ticket_summary(
    current_user: User = Depends(require_internal_user),
    svc = Depends(get_support_ticket_service),
):
    """Get aggregate support activity counts for navigation and queue summaries."""
    return SupportTicketSummaryResponse(**svc.get_ticket_summary(current_user))


@router.post("/support/tickets", response_model=SupportTicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(
    body: SupportTicketCreate,
    current_user: User = Depends(require_internal_user),
    svc = Depends(get_support_ticket_service),
):
    """Create a new support ticket."""
    ticket = svc.create_ticket(
        customer=current_user,
        subject=body.subject,
        content=body.content,
        priority=body.priority,
        category=body.category,
        feedback_id=body.feedback_id,
    )
    return _ticket_to_response(ticket)


@router.post("/support/tickets/from-feedback/{feedback_id}", response_model=SupportTicketResponse, status_code=status.HTTP_201_CREATED)
def create_from_feedback(
    feedback_id: int,
    current_user: User = Depends(require_internal_user),
    svc = Depends(get_support_ticket_service),
):
    """Create a support ticket from existing feedback."""
    ticket = svc.create_ticket_from_feedback(current_user, feedback_id)
    return _ticket_to_response(ticket)


@router.get("/support/tickets/{ticket_id}", response_model=SupportTicketDetailResponse)
def get_ticket(
    ticket_id: int,
    current_user: User = Depends(require_internal_user),
    svc = Depends(get_support_ticket_service),
):
    """Get ticket details with messages and assignments."""
    ticket = svc.get_ticket(ticket_id, current_user)
    indicators = svc.get_ticket_activity_map(current_user, [ticket]).get(ticket.id, {})
    return SupportTicketDetailResponse(
        id=ticket.id,
        customer_id=ticket.customer_id,
        subject=ticket.subject,
        status=ticket.status,
        priority=ticket.priority,
        category=ticket.category,
        feedback_id=ticket.feedback_id,
        tenant_id=ticket.tenant_id,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
        customer_full_name=ticket.customer.full_name if ticket.customer else None,
        last_customer_message_at=indicators.get("last_customer_message_at"),
        has_unread_activity=bool(indicators.get("has_unread_activity", False)),
        awaiting_agent_reply=bool(indicators.get("awaiting_agent_reply", False)),
        needs_attention=bool(indicators.get("needs_attention", False)),
        messages=[_msg_to_response(m) for m in ticket.messages],
        assignments=[
            SupportTicketAssignmentResponse(
                id=a.id,
                ticket_id=a.ticket_id,
                agent_id=a.agent_id,
                is_primary=a.is_primary,
                assigned_at=a.assigned_at,
                agent_full_name=a.agent.full_name if a.agent else None,
            )
            for a in ticket.assignments
        ],
    )


@router.patch("/support/tickets/{ticket_id}", response_model=SupportTicketResponse)
def update_ticket(
    ticket_id: int,
    body: SupportTicketUpdate,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
    svc = Depends(get_support_ticket_service),
):
    """Update ticket status, priority, etc. Requires agent-level access."""
    old_status = None
    if body.status:
        # Fetch current status before updating (for WS broadcast)
        from app.models import SupportTicket
        existing = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
        if existing:
            old_status = existing.status

    ticket = svc.update_ticket(
        ticket_id, current_user,
        subject=body.subject,
        status=body.status,
        priority=body.priority,
        category=body.category,
    )

    # Broadcast status change via WS (X1-085)
    if body.status and old_status and body.status != old_status:
        asyncio.get_event_loop().create_task(
            chat_manager.broadcast_to_ticket(ticket_id, "status_update", {
                "ticket_id": ticket_id,
                "status": body.status.value if hasattr(body.status, 'value') else body.status,
                "changed_by": current_user.full_name,
            })
        )

    return _ticket_to_response(ticket)


# ---- Messages ----


@router.get("/support/tickets/{ticket_id}/messages", response_model=list[SupportTicketMessageResponse])
def get_ticket_messages(
    ticket_id: int,
    current_user: User = Depends(require_internal_user),
    svc = Depends(get_support_ticket_service),
):
    """Get messages for a ticket. Internal notes hidden from customers."""
    messages = svc.get_messages(ticket_id, current_user)
    return [_msg_to_response(m) for m in messages]


@router.post(
    "/support/tickets/{ticket_id}/messages",
    response_model=SupportTicketMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_ticket_message(
    ticket_id: int,
    request: Request,
    current_user: User = Depends(require_internal_user),
    svc = Depends(get_support_ticket_service),
):
    """Send a message on a support ticket."""
    content, is_internal_note, upload = await parse_support_message_request(
        request,
        allow_internal_note=True,
    )
    file_bytes = await upload.read() if upload else None
    msg = svc.send_message(
        ticket_id,
        current_user,
        content,
        is_internal_note=is_internal_note,
        file_bytes=file_bytes,
        file_name=upload.filename if upload else None,
        file_mime_type=upload.content_type if upload else None,
    )
    ticket = svc.get_ticket(ticket_id, current_user)
    run_async_task(
        svc.broadcast_message_event(
            ticket=ticket,
            msg=msg,
            sender=current_user,
        )
    )
    return _msg_to_response(msg)


@router.get("/support/tickets/{ticket_id}/messages/{message_id}/attachment")
def download_ticket_message_attachment(
    ticket_id: int,
    message_id: int,
    current_user: User = Depends(get_current_active_user),
    svc = Depends(get_support_ticket_service),
):
    """Download a support ticket message attachment for any authorized ticket participant."""
    msg, content = svc.get_message_attachment(ticket_id, message_id, current_user)
    filename = msg.file_name or "attachment"
    return Response(
        content=content,
        media_type=msg.file_mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
            "Content-Length": str(len(content)),
        },
    )


# ---- Agent Assignment ----


@router.post(
    "/support/tickets/{ticket_id}/assign",
    response_model=SupportTicketAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def assign_agent(
    ticket_id: int,
    body: AssignAgentRequest,
    current_user: User = Depends(require_manager),
    svc = Depends(get_support_ticket_service),
):
    """Assign an agent to a support ticket."""
    assignment = svc.assign_agent(ticket_id, current_user, body.agent_id, is_primary=body.is_primary)
    return SupportTicketAssignmentResponse(
        id=assignment.id,
        ticket_id=assignment.ticket_id,
        agent_id=assignment.agent_id,
        is_primary=assignment.is_primary,
        assigned_at=assignment.assigned_at,
    )


@router.delete("/support/tickets/{ticket_id}/assign/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def unassign_agent(
    ticket_id: int,
    agent_id: int,
    current_user: User = Depends(require_manager),
    svc = Depends(get_support_ticket_service),
):
    """Remove an agent from a support ticket."""
    svc.unassign_agent(ticket_id, current_user, agent_id)


@router.post(
    "/support/tickets/{ticket_id}/handoff",
    response_model=SupportTicketAssignmentResponse,
)
def handoff_ticket(
    ticket_id: int,
    body: HandoffRequest,
    current_user: User = Depends(require_manager),
    svc = Depends(get_support_ticket_service),
):
    """Transfer ticket ownership to another agent with optional note (X1-102)."""
    assignment = svc.handoff_ticket(
        ticket_id, current_user, body.target_agent_id, note=body.note
    )
    return SupportTicketAssignmentResponse(
        id=assignment.id,
        ticket_id=assignment.ticket_id,
        agent_id=assignment.agent_id,
        is_primary=assignment.is_primary,
        assigned_at=assignment.assigned_at,
        agent_full_name=assignment.agent.full_name if assignment.agent else None,
    )


@router.get("/support/tickets/{ticket_id}/viewers")
def get_ticket_viewers(
    ticket_id: int,
    current_user: User = Depends(require_internal_user),
):
    """Get list of agents currently viewing this ticket (X1-100)."""
    user_ids = chat_manager.get_online_users_in_ticket(ticket_id)
    return {"ticket_id": ticket_id, "viewer_ids": user_ids}
