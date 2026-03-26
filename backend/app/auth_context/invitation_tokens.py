"""Invitation token helpers for secure at-rest storage."""

from __future__ import annotations

import hashlib
import hmac
import re

from app.config import settings

_INVITATION_TOKEN_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def hash_invitation_token(invitation_token: str) -> str:
    """Return a keyed HMAC-SHA256 hex digest for a raw invitation token."""
    if not invitation_token or not invitation_token.strip():
        raise ValueError("Invitation token must not be empty or whitespace")
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        invitation_token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def looks_like_invitation_token_hash(value: str | None) -> bool:
    """Best-effort check for already-hashed invitation tokens."""
    return bool(value and _INVITATION_TOKEN_HASH_RE.fullmatch(value))
