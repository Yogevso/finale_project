"""Collaboration token issuance and validation service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt.exceptions import PyJWTError

from app.auth_context.contracts import (
    COLLABORATION_TOKEN_TYPE,
    CollaborationTokenContract,
)
from app.config import settings
from app.models import User

COLLAB_TOKEN_EXPIRE_MINUTES = 60


class CollaborationAuthService:
    """Handles collaboration token lifecycle behavior."""

    def __init__(
        self,
        *,
        secret_key: str | None = None,
        algorithm: str | None = None,
        collab_token_expire_minutes: int = COLLAB_TOKEN_EXPIRE_MINUTES,
    ) -> None:
        self.secret_key = secret_key or settings.SECRET_KEY
        self.algorithm = algorithm or settings.ALGORITHM
        self.collab_token_expire_minutes = collab_token_expire_minutes

    def create_collab_token(
        self,
        *,
        user: User,
        document_id: int,
        permissions: list[str],
        expires_delta: timedelta | None = None,
    ) -> str:
        claims = CollaborationTokenContract.from_user(
            user,
            document_id=document_id,
            permissions=permissions,
        )
        payload = claims.to_payload()
        issued_at = datetime.now(timezone.utc)
        expires_at = issued_at + (
            expires_delta or timedelta(minutes=self.collab_token_expire_minutes)
        )
        payload.update(
            {
                "type": COLLABORATION_TOKEN_TYPE,
                "jti": str(uuid.uuid4()),
                "iat": issued_at,
                "exp": expires_at,
            }
        )
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_collab_token(self, token: str) -> dict[str, Any] | None:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            if payload.get("type") != COLLABORATION_TOKEN_TYPE:
                return None
            return payload
        except PyJWTError:
            return None
