"""Logging Middleware for structured request logging"""
import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app.requests")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests with structured data.

    Logs include:
    - Request ID (generated UUID)
    - HTTP method and path
    - Client IP
    - Response status code
    - Request duration in ms
    - User agent
    """

    # Paths to exclude from detailed logging
    QUIET_PATHS = {"/health", "/ready"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with logging"""
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]

        # Store in request state for use in handlers
        request.state.request_id = request_id

        # Get client info
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")[:100]

        # Start timer
        start_time = time.time()

        # Process request
        try:
            response = await call_next(request)
        except Exception as exc:
            # Log exception
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": client_ip,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(exc),
                },
            )
            raise

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        # Log request (skip quiet paths for info level)
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "client_ip": client_ip,
            "duration_ms": round(duration_ms, 2),
            "user_agent": user_agent,
        }

        if request.url.path in self.QUIET_PATHS:
            logger.debug(
                f"{request.method} {request.url.path} - {response.status_code}",
                extra=log_data,
            )
        elif response.status_code >= 500:
            logger.error(
                f"{request.method} {request.url.path} - {response.status_code}",
                extra=log_data,
            )
        elif response.status_code >= 400:
            logger.warning(
                f"{request.method} {request.url.path} - {response.status_code}",
                extra=log_data,
            )
        else:
            logger.info(
                f"{request.method} {request.url.path} - {response.status_code}",
                extra=log_data,
            )

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        return request.client.host if request.client else "unknown"
