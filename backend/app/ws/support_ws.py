"""Support ticket WebSocket endpoint — real-time support chat (X1-083 to X1-087).

Protocol:
  Connect: ws://host/ws/support?token=JWT
  Events sent by client:
    {"event": "send_message", "data": {"ticket_id": 1, "content": "hello", "is_internal_note": false}}
    {"event": "typing", "data": {"ticket_id": 1}}
    {"event": "join_ticket", "data": {"ticket_id": 1}}
  Events sent by server:
    {"event": "new_message", "data": {message...}}
    {"event": "agent_typing", "data": {"ticket_id": 1, "user_id": 2, "username": "..."}}
    {"event": "status_update", "data": {"ticket_id": 1, "status": "in_progress"}}
    {"event": "viewers_update", "data": {"ticket_id": 1, "viewer_ids": [2, 3]}}
    {"event": "error", "data": {"message": "..."}}
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.auth_context.session_tokens import hash_session_identifier
from app.config import settings
from app.db import get_db
from app.models import (
    SupportTicket,
    SupportTicketAssignment,
    SupportTicketMessage,
    SupportTicketStatus,
    User,
    UserRole,
    UserSession,
)
from app.security import verify_token
from app.ws.manager import chat_manager

router = APIRouter()


def _authenticate_ws(token: str, db: Session) -> User | None:
    """Validate JWT *and* check session revocation/inactivity (AD-003)."""
    payload = verify_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None

    user = db.query(User).filter(User.id == int(user_id), User.is_active.is_(True)).first()
    if not user:
        return None

    # Verify session is still valid (revocation + inactivity)
    session_identifier = payload.get("sid")
    if isinstance(session_identifier, str) and session_identifier.strip():
        session_hash = hash_session_identifier(session_identifier)
        user_session = (
            db.query(UserSession)
            .filter(
                UserSession.user_id == user.id,
                UserSession.session_token_hash == session_hash,
            )
            .first()
        )
        if user_session is None or user_session.revoked_at is not None:
            return None
        inactivity_cutoff = datetime.utcnow() - timedelta(days=settings.SESSION_INACTIVITY_DAYS)
        if user_session.last_active_at < inactivity_cutoff:
            return None

    return user


@router.websocket("/ws/support")
async def support_websocket(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """Support ticket WebSocket endpoint (X1-083)."""
    user = _authenticate_ws(token, db)
    if not user:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    # Get ticket IDs visible to this user
    if user.role in (UserRole.CUSTOMER, UserRole.VIEWER):
        ticket_ids = [
            t.id for t in db.query(SupportTicket.id).filter(SupportTicket.customer_id == user.id).all()
        ]
    else:
        # Agents see assigned tickets
        assigned = [
            a.ticket_id
            for a in db.query(SupportTicketAssignment.ticket_id).filter(
                SupportTicketAssignment.agent_id == user.id
            ).all()
        ]
        # Also include unassigned tickets in their tenant
        unassigned = [
            t.id
            for t in db.query(SupportTicket.id)
            .filter(SupportTicket.tenant_id == user.tenant_id)
            .all()
        ]
        ticket_ids = list(set(assigned + unassigned))

    await chat_manager.connect_support(websocket, user.id, ticket_ids)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await _send_error(websocket, "Invalid JSON")
                continue

            event = msg.get("event")
            data = msg.get("data", {})

            if event == "send_message":
                await _handle_send_message(websocket, user, data, db)
            elif event == "typing":
                await _handle_typing(user, data)
            elif event == "join_ticket":
                await _handle_join_ticket(websocket, user, data, db)
            else:
                await _send_error(websocket, f"Unknown event: {event}")

    except WebSocketDisconnect:
        pass
    finally:
        chat_manager.disconnect(websocket, user.id)


async def _handle_send_message(websocket: WebSocket, user: User, data: dict, db: Session) -> None:
    """Handle message send with real-time broadcast (X1-084)."""
    ticket_id = data.get("ticket_id")
    content = (data.get("content") or "").strip()
    is_internal_note = data.get("is_internal_note", False)

    if not ticket_id or not content:
        await _send_error(websocket, "ticket_id and content are required")
        return

    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        await _send_error(websocket, "Ticket not found")
        return

    # Access check
    if user.role in (UserRole.CUSTOMER, UserRole.VIEWER):
        if ticket.customer_id != user.id:
            await _send_error(websocket, "Access denied")
            return
        sender_type = "customer"
        is_internal_note = False  # Customers can't add notes
    elif ticket.tenant_id != user.tenant_id and user.role != UserRole.SYSTEM_ADMIN:
        await _send_error(websocket, "Access denied")
        return
    else:
        sender_type = "agent"

    msg = SupportTicketMessage(
        ticket_id=ticket_id,
        sender_id=user.id,
        sender_type=sender_type,
        content=content,
        is_internal_note=is_internal_note,
    )
    db.add(msg)

    # Auto-reopen if customer replies to resolved ticket
    if sender_type == "customer" and ticket.status == SupportTicketStatus.RESOLVED:
        ticket.status = SupportTicketStatus.OPEN
        ticket.resolved_at = None

    db.commit()
    db.refresh(msg)

    event_data = {
        "id": msg.id,
        "ticket_id": msg.ticket_id,
        "sender_id": msg.sender_id,
        "sender_type": msg.sender_type,
        "sender_full_name": user.full_name,
        "content": msg.content,
        "is_internal_note": msg.is_internal_note,
        "created_at": msg.created_at.isoformat(),
    }

    # Broadcast: internal notes only go to agents
    if is_internal_note:
        # Only send to agents in the ticket room (not customers)
        connections = chat_manager._support_connections.get(ticket_id, {})
        for uid, ws in list(connections.items()):
            if uid == ticket.customer_id:
                continue  # Skip customer
            await chat_manager._safe_send(
                ws, json.dumps({"event": "new_message", "data": event_data})
            )
    else:
        await chat_manager.broadcast_to_ticket(ticket_id, "new_message", event_data)


async def _handle_typing(user: User, data: dict) -> None:
    """Broadcast typing indicator (X1-086)."""
    ticket_id = data.get("ticket_id")
    if not ticket_id:
        return

    await chat_manager.broadcast_to_ticket(ticket_id, "agent_typing", {
        "ticket_id": ticket_id,
        "user_id": user.id,
        "username": user.full_name,
    }, exclude_user=user.id)


async def _handle_join_ticket(websocket: WebSocket, user: User, data: dict, db: Session) -> None:
    """Join a specific ticket room and broadcast viewers update (X1-100)."""
    ticket_id = data.get("ticket_id")
    if not ticket_id:
        return

    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        return

    # Verify access
    has_access = (
        user.role == UserRole.SYSTEM_ADMIN
        or ticket.customer_id == user.id
        or (ticket.tenant_id == user.tenant_id and user.role not in (UserRole.CUSTOMER, UserRole.VIEWER))
    )
    if has_access:
        if ticket_id not in chat_manager._support_connections:
            chat_manager._support_connections[ticket_id] = {}
        chat_manager._support_connections[ticket_id][user.id] = websocket

        # Broadcast updated viewers list to all in room (X1-100)
        viewer_ids = chat_manager.get_online_users_in_ticket(ticket_id)
        await chat_manager.broadcast_to_ticket(ticket_id, "viewers_update", {
            "ticket_id": ticket_id,
            "viewer_ids": viewer_ids,
        })


async def _send_error(websocket: WebSocket, message: str) -> None:
    await websocket.send_text(json.dumps({"event": "error", "data": {"message": message}}))
