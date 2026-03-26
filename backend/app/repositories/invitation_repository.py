"""Repository for invitation aggregate access patterns."""

from __future__ import annotations

from app.auth_context.invitation_tokens import (
    hash_invitation_token,
    looks_like_invitation_token_hash,
)
from app.models import Invitation, InvitationStatus
from app.repositories.base import BaseRepository


class InvitationRepository(BaseRepository):
    """Invitation persistence/query access."""

    def get_by_id(self, invitation_id: int) -> Invitation | None:
        return self.db.query(Invitation).filter(Invitation.id == invitation_id).first()

    def get_by_token(self, token: str) -> Invitation | None:
        return self._get_by_token_value(token, for_update=False)

    def get_by_token_for_update(self, token: str) -> Invitation | None:
        """
        Get an invitation with a row-level lock for acceptance.

        This serializes concurrent invitation acceptance on databases that support
        ``SELECT .. FOR UPDATE``. SQLite ignores the lock and relies on its
        transaction isolation in tests.
        """
        return self._get_by_token_value(token, for_update=True)

    def _get_by_token_value(self, token: str, *, for_update: bool) -> Invitation | None:
        try:
            hashed_token = hash_invitation_token(token)
        except ValueError:
            return None

        invitation = self._query_by_stored_token(hashed_token, for_update=for_update)
        if invitation is not None or looks_like_invitation_token_hash(token):
            return invitation
        return self._query_by_stored_token(token, for_update=for_update)

    def _query_by_stored_token(self, stored_token: str, *, for_update: bool) -> Invitation | None:
        dialect = self.db.bind.dialect.name if self.db.bind else "sqlite"
        query = self.db.query(Invitation).filter(Invitation.token == stored_token)
        if for_update and dialect != "sqlite":
            query = query.with_for_update()
        return query.first()

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
