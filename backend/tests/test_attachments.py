"""Tests for Attachments API endpoints."""

import io

from fastapi.testclient import TestClient


class TestAttachments:
    """Test attachment operations."""

    def test_list_attachments_empty(self, client: TestClient, auth_headers: dict, test_document):
        """Test listing attachments for a document with no attachments."""
        response = client.get(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_upload_attachment(self, client: TestClient, auth_headers: dict, test_document):
        """Test uploading a file attachment."""
        file_content = b"Test file content for attachment"
        files = {"file": ("test_file.txt", io.BytesIO(file_content), "text/plain")}
        response = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
            files=files,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "test_file.txt"
        assert "id" in data

    def test_upload_attachment_to_nonexistent_document(
        self, client: TestClient, auth_headers: dict
    ):
        """Test uploading to a document that doesn't exist."""
        file_content = b"Test content"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        response = client.post(
            "/api/v1/documents/99999/attachments",
            headers=auth_headers,
            files=files,
        )
        assert response.status_code == 404

    def test_list_attachments_after_upload(
        self, client: TestClient, auth_headers: dict, test_document
    ):
        """Test listing attachments after uploading one."""
        # Upload a file first
        file_content = b"Test content"
        files = {"file": ("uploaded.txt", io.BytesIO(file_content), "text/plain")}
        client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
            files=files,
        )

        # List attachments
        response = client.get(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
        )
        assert response.status_code == 200
        attachments = response.json()
        assert len(attachments) >= 1
        # API returns original_filename, not filename
        assert any(a["original_filename"] == "uploaded.txt" for a in attachments)

    def test_delete_attachment(self, client: TestClient, admin_headers: dict, test_document):
        """Test deleting an attachment (requires admin)."""
        # Upload a file first with admin
        file_content = b"To be deleted"
        files = {"file": ("delete_me.txt", io.BytesIO(file_content), "text/plain")}
        upload_response = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=admin_headers,
            files=files,
        )
        attachment_id = upload_response.json()["id"]

        # Delete it with admin
        response = client.delete(
            f"/api/v1/documents/{test_document.id}/attachments/{attachment_id}",
            headers=admin_headers,
        )
        assert response.status_code in [200, 204]  # Either is acceptable

    def test_delete_nonexistent_attachment(
        self, client: TestClient, auth_headers: dict, test_document
    ):
        """Test deleting an attachment that doesn't exist."""
        response = client.delete(
            f"/api/v1/documents/{test_document.id}/attachments/99999",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_viewer_cannot_upload(
        self, client: TestClient, viewer_auth_headers: dict, test_document
    ):
        """Test that viewers cannot upload attachments."""
        file_content = b"Viewer trying to upload"
        files = {"file": ("viewer_file.txt", io.BytesIO(file_content), "text/plain")}
        response = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=viewer_auth_headers,
            files=files,
        )
        assert response.status_code == 403
