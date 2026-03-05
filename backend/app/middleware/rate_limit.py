"""Rate Limiting Middleware"""

import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings
from app.utils.request_ip import get_client_ip

logger = logging.getLogger(__name__)


@dataclass
class RateLimitInfo:
    """Rate limit tracking info per client"""

    count: int = 0
    window_start: float = 0.0
    window_seconds: int = 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple sliding window rate limiter.

    Limits requests per IP address within a configurable time window.
    Excludes health check and docs endpoints from rate limiting.
    """

    # Endpoints excluded from rate limiting
    EXCLUDED_PATHS = {
        "/health",
        "/ready",
        "/docs",
        "/redoc",
        "/openapi.json",
        f"{settings.API_PREFIX}/docs",
        f"{settings.API_PREFIX}/redoc",
        f"{settings.API_PREFIX}/openapi.json",
        f"{settings.API_PREFIX}/auth/login",
        f"{settings.API_PREFIX}/auth/forgot-password",
    }
    ASSIGNMENT_PATH_PATTERNS = (
        re.compile(rf"^{settings.API_PREFIX}/documents/\d+/assign-companies$"),
        re.compile(rf"^{settings.API_PREFIX}/documents/\d+/assign-companies/\d+$"),
        re.compile(rf"^{settings.API_PREFIX}/documents/\d+/companies/bulk$"),
    )

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clients: dict[str, RateLimitInfo] = defaultdict(RateLimitInfo)
        self._cleanup_counter = 0

    def _get_client_ip(self, request: Request) -> str:
        """Compatibility shim for tests and internal callers."""
        return get_client_ip(request)

    def _cleanup_old_entries(self):
        """Periodically clean up expired rate limit entries"""
        self._cleanup_counter += 1
        if self._cleanup_counter >= 100:  # Every 100 requests
            self._cleanup_counter = 0
            current_time = time.time()
            expired = [
                client_key
                for client_key, info in self.clients.items()
                if current_time - info.window_start > max(1, int(info.window_seconds or self.window_seconds))
            ]
            for client_key in expired:
                del self.clients[client_key]

    def _resolve_limit_profile(self, *, request_path: str, method: str) -> tuple[int, int, str]:
        """Resolve path-specific rate-limit profile."""
        if method in {"POST", "PUT", "PATCH", "DELETE"} and any(
            pattern.match(request_path) for pattern in self.ASSIGNMENT_PATH_PATTERNS
        ):
            return (
                int(settings.ASSIGNMENT_RATE_LIMIT_REQUESTS),
                int(settings.ASSIGNMENT_RATE_LIMIT_WINDOW),
                "assignment",
            )
        return self.max_requests, self.window_seconds, "default"

    def _is_rate_limited(
        self,
        client_ip: str,
        *,
        max_requests: int | None = None,
        window_seconds: int | None = None,
        scope: str = "default",
    ) -> tuple[bool, int, int]:
        """
        Check if client is rate limited.

        Returns:
            (is_limited, remaining_requests, reset_time)
        """
        resolved_limit = max(1, int(max_requests if max_requests is not None else self.max_requests))
        resolved_window = max(1, int(window_seconds if window_seconds is not None else self.window_seconds))
        current_time = time.time()
        bucket_key = f"{scope}:{client_ip}"
        info = self.clients[bucket_key]

        # Check if window has expired
        if (
            info.window_start == 0.0
            or info.window_seconds != resolved_window
            or current_time - info.window_start > resolved_window
        ):
            # Reset window
            info.window_start = current_time
            info.window_seconds = resolved_window
            info.count = 1
            return False, resolved_limit - 1, int(current_time + resolved_window)

        # Within window, check count
        if info.count >= resolved_limit:
            reset_time = int(info.window_start + resolved_window)
            return True, 0, reset_time

        # Increment count
        info.count += 1
        remaining = resolved_limit - info.count
        reset_time = int(info.window_start + resolved_window)
        return False, remaining, reset_time

    @staticmethod
    def _is_e2e_bypass_request(request: Request) -> bool:
        """Allow bypassing limits for explicit E2E traffic in non-production envs."""
        if settings.APP_ENV.lower() == "production":
            return False
        return request.headers.get("x-e2e-test", "").strip() == "1"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting"""
        # Skip if rate limiting is disabled
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Skip explicit E2E traffic outside production.
        if self._is_e2e_bypass_request(request):
            return await call_next(request)

        # Skip excluded paths
        request_path = request.url.path.rstrip("/") or "/"
        method = request.method.upper()
        if request_path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # Get client IP
        client_ip = get_client_ip(request)
        limit, window, scope = self._resolve_limit_profile(
            request_path=request_path,
            method=method,
        )

        # Check rate limit
        is_limited, remaining, reset_time = self._is_rate_limited(
            client_ip,
            max_requests=limit,
            window_seconds=window,
            scope=scope,
        )

        # Periodic cleanup
        self._cleanup_old_entries()

        if is_limited:
            logger.warning(f"Rate limit exceeded for {client_ip} on {request.url.path}")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": reset_time - int(time.time()),
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time - int(time.time())),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response


def create_rate_limit_middleware(app):
    """Factory function to create rate limit middleware"""
    return RateLimitMiddleware(
        app,
        max_requests=settings.RATE_LIMIT_REQUESTS,
        window_seconds=settings.RATE_LIMIT_WINDOW,
    )
