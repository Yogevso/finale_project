"""Conversation CRUD for the AI assistant."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import AssistantConversation, AssistantMessage

logger = logging.getLogger(__name__)

_TITLE_MAX_LEN = 100


class ConversationManager:
    """Manages assistant conversations and messages in the database."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Conversation CRUD
    # ------------------------------------------------------------------

    def create_conversation(
        self,
        user_id: int,
        tenant_id: int | None,
        title: str = "New Chat",
    ) -> AssistantConversation:
        conv = AssistantConversation(
            user_id=user_id,
            tenant_id=tenant_id,
            title=title[:_TITLE_MAX_LEN],
        )
        self._db.add(conv)
        self._db.commit()
        self._db.refresh(conv)
        return conv

    def get_conversation(
        self, conversation_id: int, user_id: int
    ) -> AssistantConversation | None:
        """Return conversation only if owned by *user_id*."""
        return (
            self._db.query(AssistantConversation)
            .filter(
                AssistantConversation.id == conversation_id,
                AssistantConversation.user_id == user_id,
            )
            .first()
        )

    def list_conversations(
        self, user_id: int, limit: int = 50, offset: int = 0
    ) -> list[AssistantConversation]:
        return (
            self._db.query(AssistantConversation)
            .filter(
                AssistantConversation.user_id == user_id,
                AssistantConversation.is_archived.is_(False),
            )
            .order_by(AssistantConversation.updated_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def delete_conversation(self, conversation_id: int, user_id: int) -> bool:
        """Delete a conversation owned by *user_id*. Returns True if deleted."""
        conv = self.get_conversation(conversation_id, user_id)
        if conv is None:
            return False
        self._db.delete(conv)
        self._db.commit()
        return True

    def update_title(self, conversation_id: int, title: str) -> None:
        conv = (
            self._db.query(AssistantConversation)
            .filter(AssistantConversation.id == conversation_id)
            .first()
        )
        if conv:
            conv.title = title[:_TITLE_MAX_LEN]
            self._db.commit()

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
        tool_name: str | None = None,
        token_count: int | None = None,
    ) -> AssistantMessage:
        msg = AssistantMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_calls=json.dumps(tool_calls) if tool_calls else None,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            token_count=token_count,
        )
        self._db.add(msg)
        self._db.commit()
        self._db.refresh(msg)
        return msg

    def get_messages(
        self, conversation_id: int, limit: int = 100
    ) -> list[AssistantMessage]:
        return (
            self._db.query(AssistantMessage)
            .filter(AssistantMessage.conversation_id == conversation_id)
            .order_by(AssistantMessage.created_at.asc())
            .limit(limit)
            .all()
        )

    def build_message_history(self, conversation_id: int) -> list[dict[str, Any]]:
        """Convert stored messages into the Ollama chat message format."""
        messages = self.get_messages(conversation_id)
        history: list[dict[str, Any]] = []
        for msg in messages:
            entry: dict[str, Any] = {"role": msg.role, "content": msg.content or ""}
            if msg.tool_calls:
                try:
                    entry["tool_calls"] = json.loads(msg.tool_calls)
                except json.JSONDecodeError:
                    pass
            if msg.tool_call_id:
                entry["tool_call_id"] = msg.tool_call_id
            history.append(entry)
        return history

    def get_message_count(self, conversation_id: int) -> int:
        return (
            self._db.query(func.count(AssistantMessage.id))
            .filter(AssistantMessage.conversation_id == conversation_id)
            .scalar()
            or 0
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def generate_title_from_message(message: str) -> str:
        """Derive a short title from the first user message."""
        title = message.strip().split("\n")[0]
        if len(title) > _TITLE_MAX_LEN:
            title = title[: _TITLE_MAX_LEN - 1] + "…"
        return title
