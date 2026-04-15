"""Immutable DTO primitives for application command/query boundaries."""

from __future__ import annotations

from dataclasses import dataclass

from app.application.policies.access_policies import safe_user_role
from app.models import User, UserRole


@dataclass(frozen=True, slots=True)
class ActorContext:
    """Immutable user snapshot consumed by application command/query handlers."""

    id: int
    role: UserRole
    tenant_id: int | None
    is_active: bool

    @classmethod
    def from_user(cls, user: User) -> ActorContext:
        role = safe_user_role(user)
        if role is None:
            raise ValueError(f"User {user.id} has invalid role: {user.role!r}")
        return cls(
            id=user.id,
            role=role,
            tenant_id=user.tenant_id,
            is_active=bool(user.is_active),
        )
