"""Access token issuance and validation service."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

import jwt
from jwt.exceptions import InvalidSignatureError, PyJWTError

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
        legacy_secret_key: str | None = None,
        algorithm: str | None = None,
        access_token_expire_minutes: int | None = None,
    ) -> None:
        self.secret_key = secret_key or settings.SECRET_KEY
        configured_legacy_secret = legacy_secret_key or settings.SECRET_KEY_OLD
        self.legacy_secret_keys = tuple(
            candidate
            for candidate in (configured_legacy_secret,)
            if candidate and candidate != self.secret_key
        )
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
        expires_at = datetime.now(timezone.utc) + (
            expires_delta or timedelta(minutes=self.access_token_expire_minutes)
        )
        payload.update({"exp": expires_at, "type": ACCESS_TOKEN_TYPE, "jti": str(uuid.uuid4())})
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

    def verify_token(
        self,
        token: str,
        *,
        expected_type: str = ACCESS_TOKEN_TYPE,
    ) -> dict[str, Any] | None:
        verification_keys = (self.secret_key, *self.legacy_secret_keys)
        for index, signing_key in enumerate(verification_keys):
            try:
                payload = jwt.decode(token, signing_key, algorithms=[self.algorithm])
                token_type = payload.get("type")
                if token_type != expected_type:
                    logger.info(
                        "JWT verification rejected token type %r (expected %r)",
                        token_type,
                        expected_type,
                    )
                    return None
                return payload
            except InvalidSignatureError:
                if index < len(verification_keys) - 1:
                    continue
                logger.info("JWT verification failed: InvalidSignatureError")
                return None
            except PyJWTError as err:
                logger.info("JWT verification failed: %s", type(err).__name__)
                return None
        return None
