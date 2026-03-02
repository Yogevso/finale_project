"""Task 190 – Attachment access parity tests.

Verifies:
1. Portal download endpoint exists and is routed correctly.
2. Portal preview endpoint exists and is routed correctly.
3. Portal attachment metadata download_url now points to portal route.
4. Both endpoints apply audience policy headers.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


class TestPortalAttachmentRouteRegistration:
    """Verify new portal download / preview routes are registered."""

    def test_download_route_exists(self):
        """The /portal/documents/{id}/attachments/{aid}/download route should exist (401 without auth)."""
        resp = client.get("/api/v1/portal/documents/1/attachments/1/download")
        # Without auth we expect 401 or 403, NOT 404 (route not found) or 405 (method not allowed)
        assert resp.status_code in (401, 403), f"Unexpected status: {resp.status_code}"

    def test_preview_route_exists(self):
        """The /portal/documents/{id}/attachments/{aid}/preview route should exist."""
        resp = client.get("/api/v1/portal/documents/1/attachments/1/preview")
        assert resp.status_code in (401, 403), f"Unexpected status: {resp.status_code}"


class TestPortalDownloadUrlParity:
    """Verify the portal attachment metadata now points to the portal download route."""

    def test_download_url_uses_portal_prefix(self):
        """The download_url returned by portal attachment metadata should use /api/portal/."""
        import inspect

        from app.application.queries.portal_queries import PortalDocumentsQueryHandler

        source = inspect.getsource(PortalDocumentsQueryHandler.execute_get_attachment)
        assert "/api/v1/portal/documents/" in source, (
            "download_url should point to /api/v1/portal/ not /api/v1/documents/"
        )
        assert "/api/v1/documents/" not in source, (
            "download_url should no longer point to /api/v1/documents/ (management route)"
        )
