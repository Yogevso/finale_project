"""Chat WebSocket endpoint — real-time messaging (X1-019 to X1-023).

Protocol:
  Connect: ws://host/ws/chat?token=JWT
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
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ChatMessage, ChatMessageType, ChatParticipant, Chat, User, UserSession
from app.security import verify_token
from app.auth_context.session_tokens import hash_session_identifier
from app.config import settings
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


@router.websocket("/ws/chat")
async def chat_websocket(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """Main chat WebSocket endpoint (X1-019)."""
    user = _authenticate_ws(token, db)
    if not user:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    # Get all chat IDs this user participates in (X1-020)
    chat_ids = [
        p.chat_id
        for p in db.query(ChatParticipant.chat_id).filter(ChatParticipant.user_id == user.id).all()
    ]

    await chat_manager.connect_chat(websocket, user.id, chat_ids)

    try:
        while True:
            raw = await websocket.receive_text()
            # AD-018: reject excessively large WS frames (32 KB)
            if len(raw) > 32_768:
                await _send_error(websocket, "Message too large")
                continue
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
            elif event == "mark_read":
                await _handle_mark_read(user, data, db)
            elif event == "join_chat":
                await _handle_join_chat(websocket, user, data, db)
            else:
                await _send_error(websocket, f"Unknown event: {event}")

    except WebSocketDisconnect:
        pass
    finally:
        chat_manager.disconnect(websocket, user.id)


async def _handle_send_message(websocket: WebSocket, user: User, data: dict, db: Session) -> None:
    """Process send_message event and broadcast to participants (X1-021)."""
    chat_id = data.get("chat_id")
    content = (data.get("content") or "").strip()

    if not chat_id or not content:
        await _send_error(websocket, "chat_id and content are required")
        return

    # Verify participation
    participant = db.query(ChatParticipant).filter_by(chat_id=chat_id, user_id=user.id).first()
    if not participant:
        await _send_error(websocket, "Not a participant in this chat")
        return

    # Persist message
    msg = ChatMessage(
        chat_id=chat_id,
        sender_id=user.id,
        content=content,
        message_type=ChatMessageType.TEXT,
    )
    db.add(msg)
    db.query(Chat).filter(Chat.id == chat_id).update({"last_message_at": datetime.utcnow()})
    db.commit()
    db.refresh(msg)

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


async def _handle_mark_read(user: User, data: dict, db: Session) -> None:
    """Mark chat as read and broadcast receipt (X1-023)."""
    chat_id = data.get("chat_id")
    if not chat_id:
        return

    db.query(ChatParticipant).filter_by(
        chat_id=chat_id, user_id=user.id
    ).update({"last_read_at": datetime.utcnow()})
    db.commit()

    await chat_manager.broadcast_to_chat(chat_id, "message_read", {
        "chat_id": chat_id,
        "user_id": user.id,
    }, exclude_user=user.id)


async def _handle_join_chat(websocket: WebSocket, user: User, data: dict, db: Session) -> None:
    """Join a new chat room (e.g., after chat creation)."""
    chat_id = data.get("chat_id")
    if not chat_id:
        return

    participant = db.query(ChatParticipant).filter_by(chat_id=chat_id, user_id=user.id).first()
    if participant:
        chat_manager.join_chat(websocket, user.id, chat_id)


async def _send_error(websocket: WebSocket, message: str) -> None:
    await websocket.send_text(json.dumps({"event": "error", "data": {"message": message}}))
