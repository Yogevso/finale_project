"""Invitation-domain factories for onboarding workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.models import Invitation, InvitationStatus, UserRole


class InvitationFactory:
    """Factory methods for invitation initialization paths."""

    @staticmethod
    def create_invitation(
        *,
        email: str,
        token: str,
        role: UserRole,
        invited_by: int,
        expires_at: datetime,
        tenant_id: Optional[int] = None,
        message: Optional[str] = None,
        status: InvitationStatus = InvitationStatus.PENDING,
    ) -> Invitation:
        return Invitation(
            email=email,
            token=token,
            role=role,
            tenant_id=tenant_id,
            invited_by=invited_by,
            message=message,
            expires_at=expires_at,
            status=status,
        )

