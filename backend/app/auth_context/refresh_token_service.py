"""Refresh token issuance, persistence, and invalidation service."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.auth_context.passwords import get_password_hash, verify_password
from app.models import PasswordReset

REFRESH_TOKEN_EXPIRE_DAYS = 7


class RefreshTokenService:
    """Manages refresh token records backed by the database."""

    def __init__(
        self,
        db: Session,
        *,
        refresh_token_expire_days: int = REFRESH_TOKEN_EXPIRE_DAYS,
    ) -> None:
        self.db = db
        self.refresh_token_expire_days = refresh_token_expire_days

    @staticmethod
    def build_refresh_token(
        *,
        refresh_token_expire_days: int = REFRESH_TOKEN_EXPIRE_DAYS,
    ) -> tuple[str, datetime]:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=refresh_token_expire_days)
        return token, expires_at

    def issue_refresh_token(self, user_id: int) -> tuple[str, datetime]:
        refresh_token, expires_at = self.build_refresh_token(
            refresh_token_expire_days=self.refresh_token_expire_days
        )
        token_hash = get_password_hash(refresh_token)
        refresh_record = PasswordReset(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(refresh_record)
        self.db.commit()
        return refresh_token, expires_at

    def find_valid_record(self, refresh_token: str) -> PasswordReset | None:
        # Keep refresh-token and password-reset/email-verification token families isolated.
        if refresh_token.startswith("pr_") or refresh_token.startswith("ev_"):
            return None

        now = datetime.utcnow()
        refresh_records = (
            self.db.query(PasswordReset)
            .filter(PasswordReset.expires_at > now, PasswordReset.used_at.is_(None))
            .all()
        )
        for record in refresh_records:
            if verify_password(refresh_token, record.token_hash):
                return record
        return None

    def invalidate_user_tokens(self, user_id: int) -> None:
        now = datetime.utcnow()
        self.db.query(PasswordReset).filter(
            PasswordReset.user_id == user_id,
            PasswordReset.used_at.is_(None),
        ).update({"used_at": now})
        self.db.commit()
