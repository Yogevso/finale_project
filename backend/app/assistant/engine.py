"""Core assistant engine — orchestrates Ollama ↔ tool-calling loop."""

from __future__ import annotations

import logging
import uuid
from typing import Any, AsyncGenerator

from sqlalchemy.orm import Session

from app.assistant.conversation import ConversationManager
from app.assistant.ollama_client import OllamaClient
from app.assistant.schemas import ToolCall, ToolResult
from app.assistant.tools.registry import ToolRegistry
from app.config import settings
from app.models import User, UserRole

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """\
You are a helpful AI assistant for the Documentation Platform.

Current user: {username} (role: {role})
Tenant: {tenant_info}

You can perform actions on the platform using the tools provided.
Always respect the user's permissions — do not attempt actions they aren't authorised for.
When you use a tool, explain what you did and summarise the result in natural language.
If a tool call fails, explain the error clearly and suggest alternatives.
Keep responses concise and professional.
"""


class AssistantEngine:
    """Orchestrates the LLM ↔ tool-call loop."""

    def __init__(
        self,
        ollama: OllamaClient,
        registry: ToolRegistry,
        conversation_mgr: ConversationManager,
    ) -> None:
        self._ollama = ollama
        self._registry = registry
        self._conv = conversation_mgr

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def chat(
        self,
        user: User,
        tenant_id: int | None,
        message: str,
        conversation_id: int | None,
        db: Session,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Main entry-point.  Yields SSE-style dicts:
          {"event": "conversation_id", "data": <id>}
          {"event": "token",           "data": "<text>"}
          {"event": "tool_call",       "data": {name, arguments}}
          {"event": "tool_result",     "data": {name, success, result}}
          {"event": "done",            "data": {}}
          {"event": "error",           "data": {message}}
        """
        # 1. Get or create conversation
        if conversation_id:
            conv = self._conv.get_conversation(conversation_id, user.id)
            if conv is None:
                yield {"event": "error", "data": {"message": "Conversation not found."}}
                return
        else:
            title = ConversationManager.generate_title_from_message(message)
            conv = self._conv.create_conversation(user.id, tenant_id, title)

        yield {"event": "conversation_id", "data": conv.id}

        # 2. Load history + build messages list
        history = self._conv.build_message_history(conv.id)

        system_prompt = self._build_system_prompt(user, tenant_id)
        messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})

        # Persist user message
        self._conv.add_message(conv.id, "user", message)

        # 3. Available tools for this user
        available_tools = self._registry.get_ollama_tools(user)

        # 4. Tool-calling loop
        max_iters = settings.ASSISTANT_MAX_TOOL_ITERATIONS
        for _iteration in range(max_iters):
            try:
                response = await self._ollama.chat(
                    messages=messages,
                    tools=available_tools or None,
                    temperature=settings.ASSISTANT_TEMPERATURE,
                    max_tokens=settings.ASSISTANT_MAX_TOKENS,
                )
            except Exception as exc:
                logger.exception("Ollama request failed")
                yield {"event": "error", "data": {"message": "AI service is temporarily unavailable."}}
                return

            resp_message = response.get("message", {})
            tool_calls_raw = resp_message.get("tool_calls")

            # ---- No tool calls → text response, done ----
            if not tool_calls_raw:
                text = resp_message.get("content", "")
                yield {"event": "token", "data": text}
                self._conv.add_message(conv.id, "assistant", text)
                break

            # ---- Tool calls → execute each, feed results back ----
            parsed_calls = self._parse_tool_calls(tool_calls_raw)

            # Save assistant message with tool_calls
            self._conv.add_message(
                conv.id,
                "assistant",
                resp_message.get("content"),
                tool_calls=[
                    {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                    for tc in parsed_calls
                ],
            )
            messages.append(resp_message)

            for tc in parsed_calls:
                yield {"event": "tool_call", "data": {"name": tc.name, "arguments": tc.arguments}}

                result = await self._registry.execute_tool(
                    tc.name, user, tenant_id, tc.arguments, db,
                )
                result.tool_call_id = tc.id

                yield {
                    "event": "tool_result",
                    "data": {
                        "name": tc.name,
                        "success": result.success,
                        "result": result.result,
                        "error": result.error,
                    },
                }

                # Append tool result to messages for next Ollama call
                tool_msg = {
                    "role": "tool",
                    "content": result.result if result.success else (result.error or "Tool failed."),
                }
                messages.append(tool_msg)
                self._conv.add_message(
                    conv.id,
                    "tool",
                    tool_msg["content"],
                    tool_call_id=tc.id,
                    tool_name=tc.name,
                )
        else:
            # Max iterations exhausted
            exhaust_msg = "I've reached the limit of operations I can perform in one response. Please send another message to continue."
            yield {"event": "token", "data": exhaust_msg}
            self._conv.add_message(conv.id, "assistant", exhaust_msg)

        yield {"event": "done", "data": {}}

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_system_prompt(self, user: User, tenant_id: int | None) -> str:
        tenant_info = f"ID {tenant_id}" if tenant_id else "global (no tenant)"
        return SYSTEM_PROMPT_TEMPLATE.format(
            username=user.username,
            role=user.role,
            tenant_info=tenant_info,
        )

    @staticmethod
    def _parse_tool_calls(raw: list[dict[str, Any]]) -> list[ToolCall]:
        """Convert Ollama tool_calls format to our ToolCall schema."""
        calls: list[ToolCall] = []
        for item in raw:
            fn = item.get("function", {})
            calls.append(
                ToolCall(
                    id=str(uuid.uuid4()),
                    name=fn.get("name", ""),
                    arguments=fn.get("arguments", {}),
                )
            )
        return calls
