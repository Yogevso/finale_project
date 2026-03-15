"""Base class and registry for AI assistant tools."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.orm import Session

from app.models import User, UserRole
from app.services.permissions import Permission, has_permission

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Abstract base for every tool the AI assistant can invoke."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema
    required_permission: Permission | None = None
    required_role: UserRole | None = None
    confirm_before_execute: bool = False

    # Role hierarchy (higher index = more privileged)
    _ROLE_HIERARCHY = [
        UserRole.CUSTOMER,
        UserRole.VIEWER,
        UserRole.EDITOR,
        UserRole.MANAGER,
        UserRole.ADMIN,
        UserRole.SYSTEM_ADMIN,
    ]

    def user_can_execute(self, user: User) -> bool:
        """Return True if *user* is allowed to call this tool."""
        if self.required_permission is not None:
            if not has_permission(user, self.required_permission):
                return False
        if self.required_role is not None:
            try:
                # Normalise required_role: accept both UserRole enum and plain
                # strings (e.g. "VIEWER", "viewer", "SYSTEM_ADMIN").
                role = self.required_role
                if not isinstance(role, UserRole):
                    role = UserRole(str(role).lower())
                required_idx = self._ROLE_HIERARCHY.index(role)
                user_idx = self._ROLE_HIERARCHY.index(UserRole(user.role))
            except ValueError:
                return False
            if user_idx < required_idx:
                return False
        return True

    @abstractmethod
    async def execute(
        self,
        user: User,
        tenant_id: int | None,
        params: dict[str, Any],
        db: Session,
    ) -> dict[str, Any]:
        """Run the tool and return ``{"success": bool, "result": str, ...}``."""

    def to_ollama_tool(self) -> dict[str, Any]:
        """Convert to the Ollama function-calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
