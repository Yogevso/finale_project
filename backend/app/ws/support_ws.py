"""Support ticket WebSocket endpoint — real-time support chat (X1-083 to X1-087).

Protocol:
  Connect: ws://host/ws/support
  First message (H-21):
    {"event": "authenticate", "data": {"token": "JWT"}}
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
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.container import build_container
from app.db import get_db
from app.errors import DomainError
from app.models import (
    SupportTicket,
    SupportTicketAssignment,
    User,
    UserRole,
)
from app.ws.auth import authenticate_ws
from app.ws.manager import chat_manager

router = APIRouter()


@router.websocket("/ws/support")
async def support_websocket(
    websocket: WebSocket,
    token: str = Query(default=None),
    db: Session = Depends(get_db),
):
    """Support ticket WebSocket endpoint (X1-083).

    H-21: Token is sent in the first WS message (``authenticate`` event)
    rather than in the query string.  Legacy ``?token=`` query param is
    still accepted for backwards compatibility.
    """
    await websocket.accept()

    # H-21: prefer token from first message over query string
    if not token:
        try:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            if msg.get("event") == "authenticate":
                token = msg.get("data", {}).get("token")
        except Exception:  # policy: LOSSY — websocket send failure is handled by disconnect cleanup
            pass  # Auth parse failed; token stays None and connection will be closed below

    if not token:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    user = authenticate_ws(token, db)
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

    # H-19: periodically re-validate the JWT so revoked sessions are caught
    _REAUTH_INTERVAL = 60  # seconds
    last_auth_check = monotonic()

    try:
        while True:
            raw = await websocket.receive_text()

            # H-19: periodic session re-validation
            now = monotonic()
            if now - last_auth_check >= _REAUTH_INTERVAL:
                last_auth_check = now
                if not authenticate_ws(token, db):
                    await websocket.close(code=4001, reason="Session expired or revoked")
                    return

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

    app = getattr(websocket, "app", None)
    container = getattr(getattr(app, "state", None), "container", None) or build_container()
    svc = container.support_ticket_service(db)
    try:
        msg = svc.send_message(
            ticket_id,
            user,
            content,
            is_internal_note=bool(is_internal_note),
        )
        ticket = svc.get_ticket(ticket_id, user)
    except DomainError as exc:
        await _send_error(websocket, exc.message)
        return

    await svc.broadcast_message_event(ticket=ticket, msg=msg, sender=user)


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
