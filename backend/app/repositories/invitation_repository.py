"""Repository for invitation aggregate access patterns."""

from __future__ import annotations

from app.models import Invitation, InvitationStatus
from app.repositories.base import BaseRepository


class InvitationRepository(BaseRepository):
    """Invitation persistence/query access."""

    def get_by_id(self, invitation_id: int) -> Invitation | None:
        return self.db.query(Invitation).filter(Invitation.id == invitation_id).first()

    def get_by_token(self, token: str) -> Invitation | None:
        return self.db.query(Invitation).filter(Invitation.token == token).first()

    def get_pending_by_email(self, email: str) -> Invitation | None:
        return (
            self.db.query(Invitation)
            .filter(Invitation.email == email, Invitation.status == InvitationStatus.PENDING)
            .first()
        )

    def list_paginated(
        self,
        *,
        tenant_id: int | None,
        is_system_admin: bool,
        status_filter: InvitationStatus | None,
        page: int,
        per_page: int,
    ) -> tuple[list[Invitation], int]:
        query = self.db.query(Invitation)
        if not is_system_admin:
            query = query.filter(Invitation.tenant_id == tenant_id)
        if status_filter:
            query = query.filter(Invitation.status == status_filter)
        total = query.count()
        items = (
            query.order_by(Invitation.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return items, total

