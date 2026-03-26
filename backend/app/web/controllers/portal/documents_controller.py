"""Legacy portal controller wrapper."""

from __future__ import annotations

from app.application.contexts.portal.api import PortalContextAPI


class PortalDocumentsController(PortalContextAPI):
    """Legacy HTTP-facing adapter retained for compatibility."""
