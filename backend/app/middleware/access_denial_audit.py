"""Middleware that writes SecurityEvent entries for access denials (401/403).

This creates a forensic trail for suspicious access attempts, enabling
detection of brute-force resource enumeration and unauthorized access patterns.
"""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Paths that commonly return 401 during normal operation (token refresh, etc.)
_QUIET_PATHS = frozenset({"/health", "/ready", "/api/v1/auth/me"})


class AccessDenialAuditMiddleware(BaseHTTPMiddleware):
    """Log 401/403 responses as SecurityEvent entries for forensic analysis."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        if response.status_code not in (401, 403):
            return response

        # Skip noisy paths that produce 401s in normal flow
        if request.url.path in _QUIET_PATHS:
            return response

        user_id = getattr(request.state, "user_id", None)
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")[:512]
        event_type = (
            "access_denied_403" if response.status_code == 403 else "auth_failed_401"
        )

        try:
            from app.services.audit_helper import write_security_event

            write_security_event(
                user_id=user_id or 0,
                event_type=event_type,
                ip_address=client_ip,
                user_agent=user_agent,
            )
        except Exception:
            logger.debug("Failed to write access denial security event", exc_info=True)

        return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        return request.client.host if request.client else "unknown"
