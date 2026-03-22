"""CSRF protection middleware for state-changing requests.

With JWT-based authentication (tokens in Authorization header, not cookies),
traditional CSRF attacks are mitigated. However, this middleware adds
defense-in-depth by validating Origin/Referer headers.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings

logger = logging.getLogger(__name__)

# HTTP methods that change state and require CSRF validation
STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Paths exempt from CSRF validation (public endpoints, webhooks, etc.)
CSRF_EXEMPT_PATHS = {
    "/api/v1/health",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/v1/auth/verify-email",
    "/api/v1/webhooks/",  # Webhook endpoints use signature verification instead
}


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Validates Origin/Referer headers for state-changing requests.
    
    This provides defense-in-depth against CSRF attacks even though
    JWT authentication already mitigates the primary attack vector.
    """

    def __init__(self, app, allowed_origins: list[str] | None = None):
        super().__init__(app)
        # Build set of allowed origin domains
        self.allowed_origins = set()
        origins = allowed_origins or settings.CORS_ORIGINS
        for origin in origins:
            parsed = urlparse(origin)
            if parsed.netloc:
                self.allowed_origins.add(parsed.netloc.lower())
            elif origin:  # Handle bare hostnames
                self.allowed_origins.add(origin.lower())
        
        # Always allow same-origin requests
        base_parsed = urlparse(settings.BASE_URL)
        if base_parsed.netloc:
            self.allowed_origins.add(base_parsed.netloc.lower())

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip validation for safe methods
        if request.method not in STATE_CHANGING_METHODS:
            return await call_next(request)
        
        # Skip validation for exempt paths
        path = request.url.path
        if any(path.startswith(exempt) for exempt in CSRF_EXEMPT_PATHS):
            return await call_next(request)
        
        # Validate Origin or Referer header
        origin = request.headers.get("Origin")
        referer = request.headers.get("Referer")
        
        if not self._is_valid_origin(origin, referer):
            logger.warning(
                "CSRF validation failed: origin=%s, referer=%s, path=%s, method=%s",
                origin,
                referer,
                path,
                request.method,
            )
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "CSRF validation failed",
                    "error_code": "CSRF_VALIDATION_FAILED",
                },
            )
        
        return await call_next(request)

    def _is_valid_origin(self, origin: str | None, referer: str | None) -> bool:
        """Check if the request origin is trusted."""
        # If Origin header is present, validate it
        if origin:
            parsed = urlparse(origin)
            origin_host = parsed.netloc.lower() if parsed.netloc else origin.lower()
            return origin_host in self.allowed_origins
        
        # Fall back to Referer header
        if referer:
            parsed = urlparse(referer)
            referer_host = parsed.netloc.lower() if parsed.netloc else ""
            return referer_host in self.allowed_origins
        
        # No Origin or Referer — H-07: In production, reject requests
        # missing both headers as potential CSRF attempts.
        if settings.APP_ENV.lower() == "production":
            return False
        
        return True  # Allow in development/testing
