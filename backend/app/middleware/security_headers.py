"""Security headers middleware for defense-in-depth HTTP security."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all responses for defense-in-depth protection.
    
    Headers applied:
    - X-Content-Type-Options: nosniff (prevent MIME sniffing)
    - X-XSS-Protection: 0 (disable legacy XSS filter, rely on CSP instead)
    - Referrer-Policy: strict-origin-when-cross-origin (limit referrer leakage)
    - Permissions-Policy: restrict sensitive browser features
    - X-Frame-Options: DENY (default, may be overridden per-endpoint)
    - Strict-Transport-Security: HSTS in production
    - Content-Security-Policy: basic CSP for API responses
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Disable legacy XSS filter (modern CSP is preferred)
        response.headers["X-XSS-Protection"] = "0"
        
        # Control referrer information leakage
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Restrict browser features (geolocation, camera, etc.)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), camera=(), microphone=(), payment=(), usb=()"
        )
        
        # Default X-Frame-Options (endpoints can override for embed scenarios)
        if "X-Frame-Options" not in response.headers:
            response.headers["X-Frame-Options"] = "DENY"
        
        # HSTS - only in production with HTTPS
        if settings.APP_ENV.lower() == "production":
            # max-age=1 year, include subdomains, allow preload
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Basic CSP for API responses (prevents inline scripts if HTML is returned)
        # Note: Frontend sets its own CSP via meta tag or server config
        if "Content-Security-Policy" not in response.headers:
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'none'"
            )
        
        # Cache-Control for sensitive API responses
        if request.url.path.startswith("/api/") and "Cache-Control" not in response.headers:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        
        return response
