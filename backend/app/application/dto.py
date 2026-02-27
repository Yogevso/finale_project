"""Immutable DTO primitives for application command/query boundaries."""

from __future__ import annotations

from dataclasses import dataclass

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
        role = user.role if isinstance(user.role, UserRole) else UserRole(user.role)
        return cls(
            id=user.id,
            role=role,
            tenant_id=user.tenant_id,
            is_active=bool(user.is_active),
        )
