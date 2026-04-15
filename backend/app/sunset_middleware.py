"""
AA-015 / AA-016: API Deprecation Sunset Middleware

Adds ``Sunset`` and ``Deprecation`` headers to deprecated endpoints.
Reads from a configuration list of deprecated paths with their sunset dates.

Usage in app_factory.py:
    from app.sunset_middleware import SunsetMiddleware
    app.add_middleware(SunsetMiddleware)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Deprecation registry path — same file parsed by CI checks
_DEPRECATION_REGISTRY = Path(__file__).resolve().parents[2] / "docs" / "deprecations.json"


def _load_deprecations() -> list[dict[str, Any]]:
    """Load the machine-readable deprecation registry (JSON)."""
    if not _DEPRECATION_REGISTRY.exists():
        return []
    try:
        with _DEPRECATION_REGISTRY.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        logger.warning("Failed to load deprecation registry at %s", _DEPRECATION_REGISTRY)
        return []


class SunsetMiddleware(BaseHTTPMiddleware):
    """Attach Sunset / Deprecation headers for deprecated API endpoints.

    Reads ``docs/deprecations.json`` once at startup. Each entry looks like::

        {
            "id": "DEP-001",
            "path_prefix": "/api/v1/old-endpoint",
            "sunset_date": "2025-09-01",
            "replacement": "/api/v2/new-endpoint",
            "stage": "warned",
            "link": "https://docs.example.com/migration/DEP-001"
        }

    Response headers added:
    - ``Sunset: <HTTP-date>``  — RFC 7231 date when endpoint will be removed
    - ``Deprecation: true``    — signals the endpoint is deprecated
    - ``Link: <url>; rel="sunset"`` — link to migration docs
    """

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self._deprecations = _load_deprecations()
        if self._deprecations:
            logger.info("SunsetMiddleware loaded %d deprecation(s)", len(self._deprecations))

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        path = request.url.path

        for dep in self._deprecations:
            prefix = dep.get("path_prefix", "")
            stage = dep.get("stage", "")
            if not prefix or stage == "removed":
                continue

            if path.startswith(prefix):
                # Set Sunset header (RFC 8594)
                sunset_date = dep.get("sunset_date")
                if sunset_date:
                    try:
                        dt = datetime.strptime(sunset_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                        response.headers["Sunset"] = dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
                    except ValueError:
                        pass

                # Set Deprecation header
                response.headers["Deprecation"] = "true"

                # Set Link header for migration docs
                link = dep.get("link")
                if link:
                    response.headers["Link"] = f'<{link}>; rel="sunset"'

                break  # first match wins

        return response
