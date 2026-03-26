"""Chat WebSocket endpoint — real-time messaging (X1-019 to X1-023).

Protocol:
  Connect: ws://host/ws/chat
  First message (H-21):
    {"event": "authenticate", "data": {"token": "JWT"}}
  Events sent by client:
    {"event": "send_message", "data": {"chat_id": 1, "content": "hello"}}
    {"event": "typing", "data": {"chat_id": 1}}
    {"event": "mark_read", "data": {"chat_id": 1}}
    {"event": "join_chat", "data": {"chat_id": 1}}
  Events sent by server:
    {"event": "new_message", "data": {message...}}
    {"event": "user_typing", "data": {"chat_id": 1, "user_id": 2, "username": "..."}}
    {"event": "message_read", "data": {"chat_id": 1, "user_id": 2}}
    {"event": "error", "data": {"message": "..."}}
"""

from __future__ import annotations

import json
from datetime import datetime
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException as FastAPIHTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.db import get_chat_db, get_db
from app.models import ChatParticipant, User
from app.services.chat_service import ChatService
from app.ws.auth import authenticate_ws
from app.ws.manager import chat_manager

router = APIRouter()


@router.websocket("/ws/chat")
async def chat_websocket(
    websocket: WebSocket,
    token: str = Query(default=None),
    db: Session = Depends(get_db),
    chat_db: Session = Depends(get_chat_db),
):
    """Main chat WebSocket endpoint (X1-019).

    H-21: Token is sent in the first WS message (``authenticate`` event)
    rather than in the query string to avoid leaking credentials into
    proxy/access logs.  The legacy ``?token=`` query param is still
    accepted for backwards compatibility but the first-message approach
    is preferred.
    """
    await websocket.accept()

    # H-21: prefer token from first message over query string
    if not token:
        try:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            if msg.get("event") == "authenticate":
                token = msg.get("data", {}).get("token")
        except Exception:
            pass  # Auth parse failed; token stays None and connection will be closed below

    if not token:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    user = authenticate_ws(token, db)
    if not user:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    # Get all chat IDs this user participates in (X1-020)
    chat_ids = [
        p.chat_id
        for p in chat_db.query(ChatParticipant.chat_id).filter(ChatParticipant.user_id == user.id).all()
    ]

    await chat_manager.connect_chat(websocket, user.id, chat_ids)

    # H-19: periodically re-validate the JWT so revoked sessions are caught
    _REAUTH_INTERVAL = 60  # seconds
    last_auth_check = monotonic()

    try:
        while True:
            raw = await websocket.receive_text()
            # AD-018: reject excessively large WS frames (32 KB)
            if len(raw) > 32_768:
                await _send_error(websocket, "Message too large")
                continue

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
                await _handle_send_message(websocket, user, data, chat_db, db)
            elif event == "typing":
                await _handle_typing(user, data)
            elif event == "mark_read":
                await _handle_mark_read(user, data, chat_db)
            elif event == "join_chat":
                await _handle_join_chat(websocket, user, data, chat_db)
            else:
                await _send_error(websocket, f"Unknown event: {event}")

    except WebSocketDisconnect:
        pass
    finally:
        chat_manager.disconnect(websocket, user.id)


async def _handle_send_message(websocket: WebSocket, user: User, data: dict, chat_db: Session, core_db: Session) -> None:
    """Process send_message event and broadcast to participants (X1-021)."""
    chat_id = data.get("chat_id")
    content = (data.get("content") or "").strip()

    if not chat_id or not content:
        await _send_error(websocket, "chat_id and content are required")
        return

    try:
        svc = ChatService(chat_db, core_db=core_db)
        msg = svc.send_message(chat_id, user, content)
    except FastAPIHTTPException as exc:
        await _send_error(websocket, exc.detail)
        return

    # Broadcast to all participants (X1-021)
    await chat_manager.broadcast_to_chat(chat_id, "new_message", {
        "id": msg.id,
        "chat_id": msg.chat_id,
        "sender_id": msg.sender_id,
        "sender_full_name": user.full_name,
        "content": msg.content,
        "message_type": msg.message_type.value,
        "created_at": msg.created_at.isoformat(),
    })


async def _handle_typing(user: User, data: dict) -> None:
    """Broadcast typing indicator with 3-second debounce on client (X1-022)."""
    chat_id = data.get("chat_id")
    if not chat_id:
        return

    await chat_manager.broadcast_to_chat(chat_id, "user_typing", {
        "chat_id": chat_id,
        "user_id": user.id,
        "username": user.full_name,
    }, exclude_user=user.id)


async def _handle_mark_read(user: User, data: dict, chat_db: Session) -> None:
    """Mark chat as read and broadcast receipt (X1-023)."""
    chat_id = data.get("chat_id")
    if not chat_id:
        return

    chat_db.query(ChatParticipant).filter_by(
        chat_id=chat_id, user_id=user.id
    ).update({"last_read_at": datetime.utcnow()})
    chat_db.commit()

    await chat_manager.broadcast_to_chat(chat_id, "message_read", {
        "chat_id": chat_id,
        "user_id": user.id,
    }, exclude_user=user.id)


async def _handle_join_chat(websocket: WebSocket, user: User, data: dict, chat_db: Session) -> None:
    """Join a new chat room (e.g., after chat creation)."""
    chat_id = data.get("chat_id")
    if not chat_id:
        return

    participant = chat_db.query(ChatParticipant).filter_by(chat_id=chat_id, user_id=user.id).first()
    if participant:
        chat_manager.join_chat(websocket, user.id, chat_id)


async def _send_error(websocket: WebSocket, message: str) -> None:
    await websocket.send_text(json.dumps({"event": "error", "data": {"message": message}}))
