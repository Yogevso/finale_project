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

    def build_message_history(
        self,
        conversation_id: int,
        max_tokens: int | None = None,
    ) -> list[dict[str, Any]]:
        """Convert stored messages into the Ollama chat message format.

        If the conversation has >10 messages and a summary exists, use
        summary + last 6 messages instead of full history.
        If *max_tokens* is set, only the most recent messages that fit
        within the budget are returned (oldest messages are dropped).
        Rough estimation: 1 token ≈ 4 characters.
        """
        messages = self.get_messages(conversation_id)

        # If conversation is long and has a summary, use compact representation
        conv = (
            self._db.query(AssistantConversation)
            .filter(AssistantConversation.id == conversation_id)
            .first()
        )
        if conv and conv.summary and len(messages) > 10:
            # Prepend summary as system context, then last 6 messages
            history: list[dict[str, Any]] = [
                {"role": "system", "content": f"[Conversation summary so far]: {conv.summary}"},
            ]
            recent = messages[-6:]
            for msg in recent:
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

        history = []
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

        if max_tokens and history:
            # Truncate from the front (drop oldest) to stay within budget
            chars_per_token = 4
            budget = max_tokens * chars_per_token
            total_chars = 0
            keep_from = len(history)
            for i in range(len(history) - 1, -1, -1):
                msg_chars = len(history[i].get("content", "") or "")
                if total_chars + msg_chars > budget:
                    break
                total_chars += msg_chars
                keep_from = i
            history = history[keep_from:]

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

    async def auto_summarize_if_needed(
        self,
        conversation_id: int,
        ollama_client: Any | None = None,
    ) -> None:
        """Summarize conversation every 10 messages to compress context."""
        msg_count = self.get_message_count(conversation_id)
        # Only summarize at multiples of 10 (10, 20, 30, ...)
        if msg_count < 10 or msg_count % 10 != 0:
            return

        conv = (
            self._db.query(AssistantConversation)
            .filter(AssistantConversation.id == conversation_id)
            .first()
        )
        if not conv:
            return

        messages = self.get_messages(conversation_id, limit=200)
        # Build text from messages for summarization
        text_parts: list[str] = []
        for msg in messages:
            if msg.role in ("user", "assistant") and msg.content:
                text_parts.append(f"{msg.role}: {msg.content[:300]}")

        if not text_parts:
            return

        full_text = "\n".join(text_parts)[:4000]

        if ollama_client is None:
            from app.assistant.ollama_client import OllamaClient
            ollama_client = OllamaClient()

        try:
            from app.config import settings
            response = await ollama_client.chat(
                messages=[
                    {"role": "system", "content": "Summarize this conversation concisely in 2-3 sentences. Focus on what was discussed and what actions were taken."},
                    {"role": "user", "content": full_text},
                ],
                tools=None,
                temperature=0.3,
                max_tokens=200,
            )
            summary = response.get("message", {}).get("content", "")
            # M-17: validate LLM response quality before storing
            if summary and len(summary.strip()) >= 20 and not summary.strip().startswith("Error"):
                conv.summary = summary.strip()[:1000]
                self._db.commit()
                logger.info("Auto-summarized conversation %d (%d messages)", conversation_id, msg_count)
            else:
                logger.warning("LLM summary rejected for conversation %d (too short or invalid)", conversation_id)
        except Exception:
            logger.warning("Failed to auto-summarize conversation %d", conversation_id, exc_info=True)
