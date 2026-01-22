"""Rate Limiting Middleware"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RateLimitInfo:
    """Rate limit tracking info per client"""

    count: int = 0
    window_start: float = 0.0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple sliding window rate limiter.

    Limits requests per IP address within a configurable time window.
    Excludes health check and docs endpoints from rate limiting.
    """

    # Endpoints excluded from rate limiting
    EXCLUDED_PATHS = {"/health", "/ready", "/docs", "/redoc", "/openapi.json"}

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clients: dict[str, RateLimitInfo] = defaultdict(RateLimitInfo)
        self._cleanup_counter = 0

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        # Check for forwarded header first (behind proxy)
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        # Check x-real-ip header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        # Fall back to direct client
        return request.client.host if request.client else "unknown"

    def _cleanup_old_entries(self):
        """Periodically clean up expired rate limit entries"""
        self._cleanup_counter += 1
        if self._cleanup_counter >= 100:  # Every 100 requests
            self._cleanup_counter = 0
            current_time = time.time()
            expired = [
                ip
                for ip, info in self.clients.items()
                if current_time - info.window_start > self.window_seconds
            ]
            for ip in expired:
                del self.clients[ip]

    def _is_rate_limited(self, client_ip: str) -> tuple[bool, int, int]:
        """
        Check if client is rate limited.

        Returns:
            (is_limited, remaining_requests, reset_time)
        """
        current_time = time.time()
        info = self.clients[client_ip]

        # Check if window has expired
        if current_time - info.window_start > self.window_seconds:
            # Reset window
            info.window_start = current_time
            info.count = 1
            return False, self.max_requests - 1, int(current_time + self.window_seconds)

        # Within window, check count
        if info.count >= self.max_requests:
            reset_time = int(info.window_start + self.window_seconds)
            return True, 0, reset_time

        # Increment count
        info.count += 1
        remaining = self.max_requests - info.count
        reset_time = int(info.window_start + self.window_seconds)
        return False, remaining, reset_time

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting"""
        # Skip if rate limiting is disabled
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Skip excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # Get client IP
        client_ip = self._get_client_ip(request)

        # Check rate limit
        is_limited, remaining, reset_time = self._is_rate_limited(client_ip)

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
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time - int(time.time())),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
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
