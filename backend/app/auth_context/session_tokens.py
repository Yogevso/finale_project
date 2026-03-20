"""Session token helpers for user-session persistence."""

from __future__ import annotations

import hashlib


def hash_session_identifier(session_identifier: str) -> str:
    """Return a deterministic SHA-256 hex digest for a raw session identifier."""
    if not session_identifier or not session_identifier.strip():
        raise ValueError("Session identifier must not be empty or whitespace")
    return hashlib.sha256(session_identifier.encode("utf-8")).hexdigest()
