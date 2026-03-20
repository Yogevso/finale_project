"""Refresh token issuance, persistence, and invalidation service."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.auth_context.passwords import get_password_hash, verify_password
from app.models import PasswordReset

REFRESH_TOKEN_EXPIRE_DAYS = 7
TOKEN_PREFIX_LENGTH = 8  # Length of searchable prefix for indexed lookup


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
        session_identifier: str | None = None,
    ) -> tuple[str, datetime]:
        token = secrets.token_urlsafe(32)
        if session_identifier:
            token = f"{session_identifier}.{token}"
        expires_at = datetime.now(timezone.utc) + timedelta(days=refresh_token_expire_days)
        return token, expires_at

    @staticmethod
    def parse_session_identifier(refresh_token: str) -> str | None:
        if "." not in refresh_token:
            return None
        session_identifier, _ = refresh_token.split(".", 1)
        return session_identifier.strip() or None

    @staticmethod
    def extract_token_prefix(refresh_token: str) -> str:
        """Extract searchable prefix from raw token for indexed lookup."""
        return refresh_token[:TOKEN_PREFIX_LENGTH]

    def issue_refresh_token(
        self,
        user_id: int,
        *,
        session_identifier: str | None = None,
    ) -> tuple[str, datetime]:
        refresh_token, expires_at = self.build_refresh_token(
            refresh_token_expire_days=self.refresh_token_expire_days,
            session_identifier=session_identifier,
        )
        token_hash = get_password_hash(refresh_token)
        token_prefix = self.extract_token_prefix(refresh_token)
        refresh_record = PasswordReset(
            user_id=user_id,
            token_hash=token_hash,
            token_prefix=token_prefix,
            expires_at=expires_at,
        )
        self.db.add(refresh_record)
        self.db.commit()
        return refresh_token, expires_at

    def find_valid_record(self, refresh_token: str) -> PasswordReset | None:
        # Keep refresh-token and password-reset/email-verification token families isolated.
        if refresh_token.startswith("pr_") or refresh_token.startswith("ev_"):
            return None

        now = datetime.now(timezone.utc)
        token_prefix = self.extract_token_prefix(refresh_token)
        
        # Use indexed token_prefix for fast lookup instead of scanning all records.
        # Only records matching the prefix are candidates; then verify the full hash.
        refresh_records = (
            self.db.query(PasswordReset)
            .filter(
                PasswordReset.expires_at > now,
                PasswordReset.used_at.is_(None),
                PasswordReset.token_prefix == token_prefix,
            )
            .all()
        )
        for record in refresh_records:
            if verify_password(refresh_token, record.token_hash):
                return record
        
        # Fallback for legacy tokens without token_prefix (backwards compatibility)
        if not refresh_records:
            legacy_records = (
                self.db.query(PasswordReset)
                .filter(
                    PasswordReset.expires_at > now,
                    PasswordReset.used_at.is_(None),
                    PasswordReset.token_prefix.is_(None),
                )
                .all()
            )
            for record in legacy_records:
                if verify_password(refresh_token, record.token_hash):
                    return record
        
        return None

    def invalidate_user_tokens(self, user_id: int) -> None:
        now = datetime.now(timezone.utc)
        self.db.query(PasswordReset).filter(
            PasswordReset.user_id == user_id,
            PasswordReset.used_at.is_(None),
        ).update({"used_at": now})
        self.db.commit()
