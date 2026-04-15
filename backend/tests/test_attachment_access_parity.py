"""Attachment access parity tests."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


class TestPortalAttachmentRouteRegistration:
    """Verify portal download routes are registered."""

    def test_download_route_exists(self):
        resp = client.get("/api/v1/portal/documents/1/attachments/1/download")
        assert resp.status_code in (401, 403), f"Unexpected status: {resp.status_code}"


class TestPortalDownloadUrlParity:
    """Verify portal attachment metadata points to the portal download route."""

    def test_download_url_uses_portal_prefix(self):
        import inspect

        from app.application.queries.portal_queries import PortalDocumentsQueryHandler

        source = inspect.getsource(PortalDocumentsQueryHandler.execute_get_attachment)
        assert (
            "/api/v1/portal/documents/" in source
        ), "download_url should point to /api/v1/portal/ not /api/v1/documents/"
        assert (
            "/api/v1/documents/" not in source
        ), "download_url should no longer point to /api/v1/documents/ (management route)"
