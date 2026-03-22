"""Support ticket tools."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.assistant.tools.base import BaseTool
from app.models import SupportTicket, SupportTicketMessage, User


class CreateSupportTicketTool(BaseTool):
    name = "create_support_ticket"
    description = "Create a new support ticket with a subject and description."
    parameters = {
        "type": "object",
        "properties": {
            "subject": {"type": "string", "description": "Ticket subject", "maxLength": 255},
            "description": {"type": "string", "description": "Detailed description of the issue", "maxLength": 5000},
            "priority": {
                "type": "string",
                "description": "Priority level (default: normal)",
                "enum": ["low", "normal", "high", "urgent"],
            },
        },
        "required": ["subject", "description"],
    }

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        if tenant_id is None:
            return {"success": False, "result": "", "error": "Support tickets require a tenant context. Please switch to a tenant-scoped account."}

        ticket = SupportTicket(
            subject=params["subject"],
            status="open",
            priority=params.get("priority", "normal"),
            customer_id=user.id,
            tenant_id=tenant_id,
        )
        db.add(ticket)
        db.flush()

        # First message
        msg = SupportTicketMessage(
            ticket_id=ticket.id,
            sender_id=user.id,
            sender_type="customer",
            content=params["description"],
            is_internal_note=False,
        )
        db.add(msg)
        db.commit()
        db.refresh(ticket)
        return {"success": True, "result": f"Support ticket created (ID: {ticket.id}, subject: '{ticket.subject}')."}


class ListMyTicketsTool(BaseTool):
    name = "list_my_tickets"
    description = "List your support tickets."
    parameters = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "Filter by status (default: all)",
                "enum": ["open", "in_progress", "resolved", "closed"],
            },
            "limit": {"type": "integer", "description": "Max results (default 10)"},
        },
        "required": [],
    }

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        query = db.query(SupportTicket).filter(SupportTicket.customer_id == user.id)
        if params.get("status"):
            query = query.filter(SupportTicket.status == params["status"])
        tickets = query.order_by(SupportTicket.created_at.desc()).limit(min(params.get("limit", 10), 50)).all()
        if not tickets:
            return {"success": True, "result": "You have no support tickets."}
        lines = [f"{len(tickets)} ticket(s):"]
        for t in tickets:
            lines.append(f"- [{t.id}] {t.subject} (status: {t.status}, priority: {t.priority})")
        return {"success": True, "result": "\n".join(lines)}


class GetTicketDetailsTool(BaseTool):
    name = "get_ticket_details"
    description = "Get details and messages of a specific support ticket."
    parameters = {
        "type": "object",
        "properties": {
            "ticket_id": {"type": "integer", "description": "The ticket ID"},
        },
        "required": ["ticket_id"],
    }

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        ticket = db.query(SupportTicket).filter(SupportTicket.id == params["ticket_id"]).first()
        if ticket is None:
            return {"success": False, "result": "", "error": "Ticket not found."}
        if ticket.customer_id != user.id:
            return {"success": False, "result": "", "error": "Ticket not found."}

        messages = (
            db.query(SupportTicketMessage)
            .filter(
                SupportTicketMessage.ticket_id == ticket.id,
                SupportTicketMessage.is_internal_note.is_(False),
            )
            .order_by(SupportTicketMessage.created_at.asc())
            .all()
        )

        lines = [
            f"Ticket #{ticket.id}: {ticket.subject}",
            f"Status: {ticket.status} | Priority: {ticket.priority}",
            f"Created: {ticket.created_at}",
            "",
            "Messages:",
        ]
        for m in messages:
            lines.append(f"  [{m.created_at}] {m.content}")
        return {"success": True, "result": "\n".join(lines)}
