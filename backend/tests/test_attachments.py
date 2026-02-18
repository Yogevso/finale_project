"""Tests for Attachments API endpoints."""

import hashlib
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
        assert "sha256" in data

    def test_original_download_preserves_bytes_and_sha256(
        self, client: TestClient, auth_headers: dict, test_document
    ):
        """Uploaded bytes must match downloaded bytes exactly."""
        uploaded_bytes = (
            b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
            b"2 0 obj\n<< /Length 5 >>\nstream\nhello\nendstream\nendobj\n%%EOF"
        )
        expected_sha = hashlib.sha256(uploaded_bytes).hexdigest()

        upload_response = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
            files={"file": ("intel-original.pdf", io.BytesIO(uploaded_bytes), "application/pdf")},
        )
        assert upload_response.status_code == 201
        payload = upload_response.json()
        attachment_id = payload["id"]
        assert payload["sha256"] == expected_sha

        metadata_response = client.get(
            f"/api/v1/documents/{test_document.id}/attachments/{attachment_id}",
            headers=auth_headers,
        )
        assert metadata_response.status_code == 200
        metadata = metadata_response.json()
        assert metadata["sha256"] == expected_sha
        assert metadata["size_bytes"] == len(uploaded_bytes)

        download_response = client.get(
            f"/api/v1/documents/{test_document.id}/attachments/{attachment_id}/download-original",
            headers=auth_headers,
        )
        assert download_response.status_code == 200
        assert download_response.headers["content-type"].startswith("application/pdf")
        assert "attachment;" in download_response.headers["content-disposition"]
        assert "intel-original.pdf" in download_response.headers["content-disposition"]
        assert download_response.headers["x-checksum-sha256"] == expected_sha
        assert int(download_response.headers["content-length"]) == len(uploaded_bytes)
        assert hashlib.sha256(download_response.content).hexdigest() == expected_sha

        legacy_download_response = client.get(
            f"/api/v1/documents/{test_document.id}/attachments/{attachment_id}/download",
            headers=auth_headers,
        )
        assert legacy_download_response.status_code == 200
        assert hashlib.sha256(legacy_download_response.content).hexdigest() == expected_sha

        preview_response = client.get(
            f"/api/v1/documents/{test_document.id}/attachments/{attachment_id}/preview",
            headers=auth_headers,
        )
        assert preview_response.status_code == 200
        assert "inline;" in preview_response.headers["content-disposition"]
        assert hashlib.sha256(preview_response.content).hexdigest() == expected_sha

        query_token = auth_headers["Authorization"].split(" ", 1)[1]
        preview_via_query_response = client.get(
            f"/api/v1/documents/{test_document.id}/attachments/{attachment_id}/preview?token={query_token}"
        )
        assert preview_via_query_response.status_code == 200
        assert hashlib.sha256(preview_via_query_response.content).hexdigest() == expected_sha

    def test_download_with_non_latin_filename_returns_200(
        self, client: TestClient, auth_headers: dict, test_document
    ):
        """Non-latin filenames should not break Content-Disposition encoding."""
        uploaded_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"
        upload_response = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
            files={"file": ("מדריך-2026.pdf", io.BytesIO(uploaded_bytes), "application/pdf")},
        )
        assert upload_response.status_code == 201
        attachment_id = upload_response.json()["id"]

        response = client.get(
            f"/api/v1/documents/{test_document.id}/attachments/{attachment_id}/download",
            headers=auth_headers,
        )
        assert response.status_code == 200
        content_disposition = response.headers["content-disposition"]
        assert "filename*=" in content_disposition
        assert "UTF-8''" in content_disposition

    def test_reader_view_endpoint_returns_status(
        self, client: TestClient, auth_headers: dict, test_document
    ):
        """Reader-view endpoint should always return artifact status for PDF attachments."""
        uploaded_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"
        upload_response = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
            files={"file": ("reader.pdf", io.BytesIO(uploaded_bytes), "application/pdf")},
        )
        assert upload_response.status_code == 201
        attachment_id = upload_response.json()["id"]

        response = client.get(
            f"/api/v1/documents/{test_document.id}/attachments/{attachment_id}/reader-view",
            headers=auth_headers,
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["attachment_id"] == attachment_id
        assert payload["status"] in {"pending", "processing", "ready", "failed"}

    def test_outline_endpoint_returns_payload(
        self, client: TestClient, auth_headers: dict, test_document
    ):
        """Outline endpoint should return a valid payload for PDF attachments."""
        uploaded_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"
        upload_response = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
            files={"file": ("outline.pdf", io.BytesIO(uploaded_bytes), "application/pdf")},
        )
        assert upload_response.status_code == 201
        attachment_id = upload_response.json()["id"]

        response = client.get(
            f"/api/v1/documents/{test_document.id}/attachments/{attachment_id}/outline",
            headers=auth_headers,
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["attachment_id"] == attachment_id
        assert "has_outline" in payload
        assert isinstance(payload.get("items"), list)

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
