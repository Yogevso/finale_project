"""Central registry for AI assistant tools."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.assistant.schemas import ToolResult
from app.assistant.tools.base import BaseTool
from app.models import User

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Singleton-style registry that holds all available assistant tools."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, tool: BaseTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Duplicate tool registration: {tool.name}")
        self._tools[tool.name] = tool
        logger.debug("Registered assistant tool: %s", tool.name)

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_all(self) -> list[BaseTool]:
        return list(self._tools.values())

    def get_tools_for_user(self, user: User) -> list[BaseTool]:
        """Return only the tools *user* is allowed to invoke."""
        return [t for t in self._tools.values() if t.user_can_execute(user)]

    def get_ollama_tools(self, user: User) -> list[dict[str, Any]]:
        """Ollama-formatted tool definitions filtered by the user's permissions."""
        return [t.to_ollama_tool() for t in self.get_tools_for_user(user)]

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute_tool(
        self,
        name: str,
        user: User,
        tenant_id: int | None,
        params: dict[str, Any],
        db: Session,
    ) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            return ToolResult(
                tool_call_id="",
                name=name,
                success=False,
                result="",
                error=f"Unknown tool: {name}",
            )

        if not tool.user_can_execute(user):
            return ToolResult(
                tool_call_id="",
                name=name,
                success=False,
                result="",
                error="You do not have permission to use this tool.",
            )

        try:
            result = await tool.execute(user, tenant_id, params, db)
            return ToolResult(
                tool_call_id="",
                name=name,
                success=result.get("success", True),
                result=result.get("result", ""),
                error=result.get("error"),
            )
        except Exception as exc:
            logger.exception("Tool %s raised an exception", name)
            return ToolResult(
                tool_call_id="",
                name=name,
                success=False,
                result="",
                error=f"Tool execution error: {exc}",
            )


# Module-level singleton
registry = ToolRegistry()
