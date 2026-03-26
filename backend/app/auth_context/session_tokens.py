"""Session token helpers for user-session persistence."""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta

from app.config import settings
from app.models import UserSession


def hash_session_identifier(session_identifier: str) -> str:
    """Return an HMAC-SHA256 hex digest for a raw session identifier.

    M-01: Uses the application SECRET_KEY so the hash is salted/keyed,
    preventing rainbow-table attacks if the DB is compromised.
    """
    if not session_identifier or not session_identifier.strip():
        raise ValueError("Session identifier must not be empty or whitespace")
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        session_identifier.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def revoke_session_if_inactive(
    user_session: UserSession,
    *,
    now: datetime | None = None,
) -> bool:
    """Mark a session revoked when it has exceeded the inactivity window."""
    if user_session.revoked_at is not None:
        return False

    current_time = now or datetime.utcnow()
    inactivity_cutoff = current_time - timedelta(days=settings.SESSION_INACTIVITY_DAYS)
    if user_session.last_active_at >= inactivity_cutoff:
        return False

    user_session.revoked_at = current_time
    return True
