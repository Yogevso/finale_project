"""Token payload contracts for authentication flows."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.models import UserRole

if TYPE_CHECKING:
    from app.models import User

ACCESS_TOKEN_TYPE = "access"
COLLABORATION_TOKEN_TYPE = "collaboration"


def _serialize_role(role: str | UserRole) -> str:
    if isinstance(role, UserRole):
        return role.value
    return str(role)


@dataclass(frozen=True)
class AccessTokenContract:
    """Canonical claims for API access tokens."""

    sub: str
    username: str
    role: str
    tenant_id: int | None
    sid: str | None = None

    @classmethod
    def from_user(cls, user: User, *, session_identifier: str | None = None) -> "AccessTokenContract":
        return cls(
            sub=str(user.id),
            username=user.username,
            role=_serialize_role(user.role),
            tenant_id=user.tenant_id,
            sid=session_identifier,
        )

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "sub": self.sub,
            "username": self.username,
            "role": self.role,
            "tenant_id": self.tenant_id,
        }
        if self.sid:
            payload["sid"] = self.sid
        return payload


@dataclass(frozen=True)
class CollaborationTokenContract:
    """Canonical claims for collaboration WebSocket tokens."""

    sub: str
    username: str
    email: str
    role: str
    document_id: str
    permissions: list[str]

    @classmethod
    def from_user(
        cls,
        user: User,
        *,
        document_id: int,
        permissions: list[str],
    ) -> "CollaborationTokenContract":
        return cls(
            sub=str(user.id),
            username=user.username,
            email=user.email,
            role=_serialize_role(user.role),
            document_id=str(document_id),
            permissions=list(permissions),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "sub": self.sub,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "document_id": self.document_id,
            "permissions": list(self.permissions),
        }
