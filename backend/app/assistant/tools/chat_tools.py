"""Chat & messaging tools — DMs, group chats, messages."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.assistant.tools.base import BaseTool
from app.models import (
    Chat,
    ChatMessage,
    ChatParticipant,
    User,
)
from app.services.permissions import Permission


class ListMyChatsTool(BaseTool):
    name = "list_my_chats"
    description = "List your chat conversations (direct messages and group chats)."
    parameters = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Max results (default 15)"},
        },
        "required": [],
    }
    required_permission = Permission.ADD_COMMENTS

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        limit = min(params.get("limit", 15), 50)
        participations = db.query(ChatParticipant).filter(ChatParticipant.user_id == user.id).all()
        chat_ids = [p.chat_id for p in participations]
        if not chat_ids:
            return {"success": True, "result": "You have no chats."}
        chats = (
            db.query(Chat)
            .filter(Chat.id.in_(chat_ids))
            .order_by(Chat.last_message_at.desc().nullslast())
            .limit(limit)
            .all()
        )
        lines = [f"{len(chats)} chat(s):"]
        for c in chats:
            pcount = (
                db.query(func.count(ChatParticipant.id))
                .filter(ChatParticipant.chat_id == c.id)
                .scalar()
            )
            label = c.name or f"DM (chat #{c.id})"
            last = (
                c.last_message_at.strftime("%Y-%m-%d %H:%M") if c.last_message_at else "no messages"
            )
            lines.append(f"- [{c.id}] {label} ({c.type.value}, {pcount} members, last: {last})")
        return {"success": True, "result": "\n".join(lines)}


class GetChatMessagesTool(BaseTool):
    name = "get_chat_messages"
    description = "Retrieve recent messages from a specific chat."
    parameters = {
        "type": "object",
        "properties": {
            "chat_id": {"type": "integer", "description": "The chat ID"},
            "limit": {"type": "integer", "description": "Number of messages (default 20)"},
        },
        "required": ["chat_id"],
    }
    required_permission = Permission.ADD_COMMENTS

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        chat_id = params["chat_id"]
        # Verify the user is a participant
        is_member = (
            db.query(ChatParticipant)
            .filter(ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == user.id)
            .first()
        )
        if not is_member:
            return {"success": False, "result": "You are not a member of this chat."}
        limit = min(params.get("limit", 20), 50)
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.chat_id == chat_id, ChatMessage.deleted_at.is_(None))
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        if not messages:
            return {"success": True, "result": "No messages in this chat yet."}
        messages.reverse()  # Show oldest first
        lines = [f"Last {len(messages)} message(s) in chat #{chat_id}:"]
        for m in messages:
            sender = db.query(User).filter(User.id == m.sender_id).first()
            sender_name = sender.full_name if sender else "Unknown"
            time_str = m.created_at.strftime("%Y-%m-%d %H:%M")
            content_preview = m.content[:200] + ("..." if len(m.content) > 200 else "")
            lines.append(f"- [{time_str}] {sender_name}: {content_preview}")
        return {"success": True, "result": "\n".join(lines)}


class SendChatMessageTool(BaseTool):
    name = "send_chat_message"
    description = "Send a message to a chat you are a member of."
    parameters = {
        "type": "object",
        "properties": {
            "chat_id": {"type": "integer", "description": "The chat ID"},
            "content": {"type": "string", "description": "Message text to send"},
        },
        "required": ["chat_id", "content"],
    }
    required_permission = Permission.ADD_COMMENTS
    confirm_before_execute = True

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        chat_id = params["chat_id"]
        is_member = (
            db.query(ChatParticipant)
            .filter(ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == user.id)
            .first()
        )
        if not is_member:
            return {"success": False, "result": "You are not a member of this chat."}
        msg = ChatMessage(
            chat_id=chat_id,
            sender_id=user.id,
            content=params["content"],
        )
        db.add(msg)
        # Update last_message_at
        chat = db.query(Chat).filter(Chat.id == chat_id).first()
        if chat:
            chat.last_message_at = msg.created_at
        db.commit()
        return {"success": True, "result": f"Message sent to chat #{chat_id}."}


class SearchChatMessagesTool(BaseTool):
    name = "search_chat_messages"
    description = "Search for messages across your chats by keyword."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search keyword or phrase",
                "maxLength": 500,
            },
            "chat_id": {"type": "integer", "description": "Limit to a specific chat (optional)"},
            "limit": {"type": "integer", "description": "Max results (default 15)"},
        },
        "required": ["query"],
    }
    required_permission = Permission.ADD_COMMENTS

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        query = params["query"]
        limit = min(params.get("limit", 15), 50)
        # Get user's chats
        my_chat_ids = [
            p.chat_id
            for p in db.query(ChatParticipant).filter(ChatParticipant.user_id == user.id).all()
        ]
        if not my_chat_ids:
            return {"success": True, "result": "You have no chats to search."}
        q = db.query(ChatMessage).filter(
            ChatMessage.chat_id.in_(my_chat_ids),
            ChatMessage.deleted_at.is_(None),
            ChatMessage.content.ilike(f"%{query}%"),
        )
        if params.get("chat_id"):
            target = params["chat_id"]
            if target not in my_chat_ids:
                return {"success": False, "result": "You are not a member of that chat."}
            q = q.filter(ChatMessage.chat_id == target)
        messages = q.order_by(ChatMessage.created_at.desc()).limit(limit).all()
        if not messages:
            return {"success": True, "result": f"No messages found matching '{query}'."}
        lines = [f"Found {len(messages)} message(s) matching '{query}':"]
        for m in messages:
            sender = db.query(User).filter(User.id == m.sender_id).first()
            sender_name = sender.full_name if sender else "Unknown"
            preview = m.content[:150] + ("..." if len(m.content) > 150 else "")
            lines.append(
                f"- [chat #{m.chat_id}, {m.created_at:%Y-%m-%d %H:%M}] {sender_name}: {preview}"
            )
        return {"success": True, "result": "\n".join(lines)}


class GetChatParticipantsTool(BaseTool):
    name = "get_chat_participants"
    description = "List the participants of a chat you are in."
    parameters = {
        "type": "object",
        "properties": {
            "chat_id": {"type": "integer", "description": "The chat ID"},
        },
        "required": ["chat_id"],
    }
    required_permission = Permission.ADD_COMMENTS

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        chat_id = params["chat_id"]
        is_member = (
            db.query(ChatParticipant)
            .filter(ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == user.id)
            .first()
        )
        if not is_member:
            return {"success": False, "result": "You are not a member of this chat."}
        participants = db.query(ChatParticipant).filter(ChatParticipant.chat_id == chat_id).all()
        lines = [f"{len(participants)} participant(s) in chat #{chat_id}:"]
        for p in participants:
            u = db.query(User).filter(User.id == p.user_id).first()
            name = u.full_name if u else "Unknown"
            muted = " (muted)" if p.is_muted else ""
            lines.append(f"- {name} — role: {p.role.value}{muted}")
        return {"success": True, "result": "\n".join(lines)}


class GetUnreadChatsTool(BaseTool):
    name = "get_unread_chats"
    description = "Show chats that have new messages you haven't read."
    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
    }
    required_permission = Permission.ADD_COMMENTS

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        participations = db.query(ChatParticipant).filter(ChatParticipant.user_id == user.id).all()
        if not participations:
            return {"success": True, "result": "You have no chats."}
        unread = []
        for p in participations:
            q = db.query(func.count(ChatMessage.id)).filter(
                ChatMessage.chat_id == p.chat_id,
                ChatMessage.deleted_at.is_(None),
            )
            if p.last_read_at:
                q = q.filter(ChatMessage.created_at > p.last_read_at)
            count = q.scalar()
            if count and count > 0:
                chat = db.query(Chat).filter(Chat.id == p.chat_id).first()
                label = chat.name or f"DM (chat #{chat.id})" if chat else f"Chat #{p.chat_id}"
                unread.append(f"- [{p.chat_id}] {label}: {count} new message(s)")
        if not unread:
            return {"success": True, "result": "All chats are up to date — no unread messages."}
        return {
            "success": True,
            "result": f"{len(unread)} chat(s) with unread messages:\n" + "\n".join(unread),
        }


class MarkChatReadTool(BaseTool):
    name = "mark_chat_read"
    description = "Mark all messages in a chat as read."
    parameters = {
        "type": "object",
        "properties": {
            "chat_id": {"type": "integer", "description": "The chat ID to mark as read"},
        },
        "required": ["chat_id"],
    }
    required_permission = Permission.ADD_COMMENTS

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        from datetime import datetime as dt

        chat_id = params["chat_id"]
        p = (
            db.query(ChatParticipant)
            .filter(ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == user.id)
            .first()
        )
        if not p:
            return {"success": False, "result": "You are not a member of this chat."}
        p.last_read_at = dt.utcnow()
        db.commit()
        return {"success": True, "result": f"Chat #{chat_id} marked as read."}
