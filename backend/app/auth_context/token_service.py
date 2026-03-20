"""Access token issuance and validation service."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Mapping

import jwt
from jwt.exceptions import PyJWTError

from app.auth_context.contracts import ACCESS_TOKEN_TYPE, AccessTokenContract
from app.config import settings
from app.models import User

logger = logging.getLogger(__name__)


class TokenService:
    """Handles JWT access-token lifecycle behavior."""

    def __init__(
        self,
        *,
        secret_key: str | None = None,
        algorithm: str | None = None,
        access_token_expire_minutes: int | None = None,
    ) -> None:
        self.secret_key = secret_key or settings.SECRET_KEY
        self.algorithm = algorithm or settings.ALGORITHM
        self.access_token_expire_minutes = (
            access_token_expire_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    def create_access_token(
        self,
        data: Mapping[str, Any],
        expires_delta: timedelta | None = None,
    ) -> str:
        payload: dict[str, Any] = dict(data)
        expires_at = datetime.utcnow() + (
            expires_delta or timedelta(minutes=self.access_token_expire_minutes)
        )
        payload.update({"exp": expires_at, "type": ACCESS_TOKEN_TYPE})
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_access_token_for_user(
        self,
        user: User,
        *,
        expires_delta: timedelta | None = None,
        session_identifier: str | None = None,
    ) -> str:
        claims = AccessTokenContract.from_user(user, session_identifier=session_identifier)
        return self.create_access_token(claims.to_payload(), expires_delta=expires_delta)

    def verify_token(self, token: str) -> dict[str, Any] | None:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except PyJWTError as err:
            logger.info("JWT verification failed: %s", type(err).__name__)
            return None
