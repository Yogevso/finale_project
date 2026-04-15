"""Tests for Attachments API endpoints."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient

from app.config import settings
from app.models import (
    Attachment,
    AttachmentArtifact,
    Document,
    DocumentStatus,
    DocumentVisibility,
    Tenant,
    User,
    UserRole,
)
from app.security import get_password_hash
from app.services.attachment_service import AttachmentService
from app.services.malware_scan_service import MalwareDetectedError

DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "documents"


def _fixture_bytes(name: str = "wave_y_empty.docx") -> bytes:
    return (FIXTURE_DIR / name).read_bytes()


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


class TestAttachments:
    """Test attachment operations."""

    def test_list_attachments_empty(self, client: TestClient, auth_headers: dict, test_document):
        response = client.get(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_upload_attachment(self, client: TestClient, auth_headers: dict, test_document):
        response = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
            files={"file": ("test-file.docx", io.BytesIO(_fixture_bytes()), DOCX_MIME_TYPE)},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "test-file.docx"
        assert "id" in data
        assert "sha256" in data

    def test_upload_attachment_rejects_malware(
        self, client: TestClient, auth_headers: dict, test_document, monkeypatch
    ):
        monkeypatch.setattr(
            "app.services.attachment_service.upload.scan_upload_bytes",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                MalwareDetectedError("Upload blocked: malware detected in 'test-file.docx'.")
            ),
        )

        response = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
            files={"file": ("test-file.docx", io.BytesIO(_fixture_bytes()), DOCX_MIME_TYPE)},
        )
        assert response.status_code == 400
        assert "malware detected" in response.json()["detail"].lower()

    def test_accepts_pdf_upload(self, client: TestClient, auth_headers: dict, test_document):
        response = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
            files={"file": ("legacy.pdf", io.BytesIO(b"%PDF-1.4\n%EOF"), "application/pdf")},
        )
        assert response.status_code == 201

    def test_attachment_service_uses_shared_upload_limit(self):
        assert AttachmentService.MAX_FILE_SIZE == settings.MAX_UPLOAD_SIZE == 50 * 1024 * 1024

    @pytest.mark.anyio
    async def test_upload_attachment_passes_filename_and_content_type_to_magic_byte_validation(
        self,
        db,
        test_document,
        test_user,
        monkeypatch,
    ):
        captured: dict[str, str] = {}

        def _capture_validate(
            cls, content: bytes, original_filename: str, content_type: str
        ) -> None:
            captured["filename"] = original_filename
            captured["content_type"] = content_type
            assert content.startswith(b"%PDF")

        def _fake_create(cls, **kwargs):
            return None

        monkeypatch.setattr(
            AttachmentService,
            "_validate_magic_bytes",
            classmethod(_capture_validate),
        )
        monkeypatch.setattr(
            AttachmentService,
            "create_attachment_from_bytes",
            classmethod(_fake_create),
        )

        upload = UploadFile(
            filename="manual.pdf",
            file=io.BytesIO(b"%PDF-1.4\n%EOF"),
            headers={"content-type": "application/pdf"},
        )

        await AttachmentService.upload_attachment(
            db=db,
            document_id=test_document.id,
            file=upload,
            current_user=test_user,
        )

        assert captured == {
            "filename": "manual.pdf",
            "content_type": "application/pdf",
        }

    def test_original_download_preserves_bytes_and_sha256(
        self, client: TestClient, auth_headers: dict, test_document
    ):
        uploaded_bytes = _fixture_bytes("wave_y_rich.docx")
        expected_sha = hashlib.sha256(uploaded_bytes).hexdigest()

        upload_response = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
            files={"file": ("intel-original.docx", io.BytesIO(uploaded_bytes), DOCX_MIME_TYPE)},
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
        assert download_response.headers["content-type"].startswith(DOCX_MIME_TYPE)
        assert "attachment;" in download_response.headers["content-disposition"]
        assert "intel-original.docx" in download_response.headers["content-disposition"]
        assert download_response.headers["x-checksum-sha256"] == expected_sha
        assert int(download_response.headers["content-length"]) == len(uploaded_bytes)
        assert hashlib.sha256(download_response.content).hexdigest() == expected_sha

        legacy_download_response = client.get(
            f"/api/v1/documents/{test_document.id}/attachments/{attachment_id}/download",
            headers=auth_headers,
        )
        assert legacy_download_response.status_code == 200
        assert hashlib.sha256(legacy_download_response.content).hexdigest() == expected_sha

    def test_signed_download_ticket_allows_authenticated_url_download(
        self, client: TestClient, auth_headers: dict, test_document
    ):
        uploaded_bytes = _fixture_bytes("wave_y_rich.docx")

        upload_response = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
            files={"file": ("ticketed.docx", io.BytesIO(uploaded_bytes), DOCX_MIME_TYPE)},
        )
        assert upload_response.status_code == 201
        attachment_id = upload_response.json()["id"]

        ticket_response = client.post(
            "/api/v1/attachments/download-ticket",
            headers=auth_headers,
            json={"document_id": test_document.id, "attachment_id": attachment_id},
        )
        assert ticket_response.status_code == 200
        ticket = ticket_response.json()["ticket"]

        download_response = client.get(
            f"/api/v1/documents/{test_document.id}/attachments/{attachment_id}/download",
            params={"token": ticket},
        )
        assert download_response.status_code == 200
        assert (
            hashlib.sha256(download_response.content).hexdigest()
            == hashlib.sha256(uploaded_bytes).hexdigest()
        )

    def test_download_with_non_latin_filename_returns_200(
        self, client: TestClient, auth_headers: dict, test_document
    ):
        upload_response = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
            files={"file": ("מדריך-2026.docx", io.BytesIO(_fixture_bytes()), DOCX_MIME_TYPE)},
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
        upload_response = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
            files={"file": ("reader.docx", io.BytesIO(_fixture_bytes()), DOCX_MIME_TYPE)},
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

    def test_upload_attachment_to_nonexistent_document(
        self, client: TestClient, auth_headers: dict
    ):
        response = client.post(
            "/api/v1/documents/99999/attachments",
            headers=auth_headers,
            files={"file": ("test-file.docx", io.BytesIO(_fixture_bytes()), DOCX_MIME_TYPE)},
        )
        assert response.status_code == 404

    def test_list_attachments_after_upload(
        self, client: TestClient, auth_headers: dict, test_document
    ):
        client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
            files={"file": ("uploaded.docx", io.BytesIO(_fixture_bytes()), DOCX_MIME_TYPE)},
        )

        response = client.get(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
        )
        assert response.status_code == 200
        attachments = response.json()
        assert len(attachments) >= 1
        assert any(a["original_filename"] == "uploaded.docx" for a in attachments)

    def test_upload_reuses_existing_blob_for_duplicate_content(
        self,
        client: TestClient,
        auth_headers: dict,
        admin_headers: dict,
        test_document,
        db,
        monkeypatch,
    ):
        class _FakeStorageBackend:
            def __init__(self) -> None:
                self.files: dict[str, bytes] = {}
                self.upload_calls = 0
                self.delete_calls = 0

            def upload(self, file_data, filename: str, content_type: str) -> str:
                self.upload_calls += 1
                key = f"blob-{self.upload_calls}-{filename}"
                self.files[key] = file_data.read()
                return key

            def download(self, storage_key: str) -> bytes:
                return self.files[storage_key]

            def delete(self, storage_key: str) -> bool:
                self.delete_calls += 1
                self.files.pop(storage_key, None)
                return True

        fake_storage = _FakeStorageBackend()
        monkeypatch.setattr(
            "app.services.attachment_service.upload.get_storage_backend", lambda: fake_storage
        )
        monkeypatch.setattr(
            "app.services.attachment_service.streams.get_storage_backend", lambda: fake_storage
        )

        first_response = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
            files={"file": ("duplicate.docx", io.BytesIO(_fixture_bytes()), DOCX_MIME_TYPE)},
        )
        assert first_response.status_code == 201

        second_response = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
            files={"file": ("duplicate-copy.docx", io.BytesIO(_fixture_bytes()), DOCX_MIME_TYPE)},
        )
        assert second_response.status_code == 201
        assert fake_storage.upload_calls == 1

        attachments = (
            db.query(Attachment)
            .filter(Attachment.document_id == test_document.id)
            .order_by(Attachment.id.asc())
            .all()
        )
        duplicate_attachments = [
            attachment
            for attachment in attachments
            if attachment.original_filename in {"duplicate.docx", "duplicate-copy.docx"}
        ]
        assert len(duplicate_attachments) == 2
        assert duplicate_attachments[-1].id != duplicate_attachments[-2].id
        assert duplicate_attachments[-1].storage_key == duplicate_attachments[-2].storage_key

        delete_response = client.delete(
            f"/api/v1/documents/{test_document.id}/attachments/{duplicate_attachments[-2].id}",
            headers=admin_headers,
        )
        assert delete_response.status_code in [200, 204]

        download_response = client.get(
            f"/api/v1/documents/{test_document.id}/attachments/{duplicate_attachments[-1].id}/download",
            headers=auth_headers,
        )
        assert download_response.status_code == 200
        assert fake_storage.delete_calls == 0

    def test_list_attachments_hydrates_reader_artifact_fields_from_bulk_lookup(
        self, client: TestClient, auth_headers: dict, db, test_document, test_user
    ):
        attachment_one = Attachment(
            document_id=test_document.id,
            filename="artifact-one.docx",
            original_filename="artifact-one.docx",
            file_size=128,
            size_bytes=128,
            mime_type=DOCX_MIME_TYPE,
            storage_path="/tmp/artifact-one.docx",
            storage_key="/tmp/artifact-one.docx",
            uploaded_by=test_user.id,
        )
        attachment_two = Attachment(
            document_id=test_document.id,
            filename="artifact-two.docx",
            original_filename="artifact-two.docx",
            file_size=256,
            size_bytes=256,
            mime_type=DOCX_MIME_TYPE,
            storage_path="/tmp/artifact-two.docx",
            storage_key="/tmp/artifact-two.docx",
            uploaded_by=test_user.id,
        )
        db.add_all([attachment_one, attachment_two])
        db.commit()
        db.refresh(attachment_one)
        db.refresh(attachment_two)

        db.add_all(
            [
                AttachmentArtifact(
                    attachment_id=attachment_one.id,
                    kind="reader_html",
                    status="ready",
                    content_text="<p>Attachment one</p>",
                    source="headings",
                ),
                AttachmentArtifact(
                    attachment_id=attachment_two.id,
                    kind="reader_html",
                    status="processing",
                ),
            ]
        )
        db.commit()

        response = client.get(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=auth_headers,
        )
        assert response.status_code == 200
        items = {item["id"]: item for item in response.json()}

        assert items[attachment_one.id]["reader_html_status"] == "ready"
        assert items[attachment_one.id]["reader_toc_source"] == "headings"
        assert items[attachment_two.id]["reader_html_status"] == "processing"

    def test_delete_attachment(self, client: TestClient, admin_headers: dict, test_document):
        upload_response = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=admin_headers,
            files={"file": ("delete-me.docx", io.BytesIO(_fixture_bytes()), DOCX_MIME_TYPE)},
        )
        attachment_id = upload_response.json()["id"]

        response = client.delete(
            f"/api/v1/documents/{test_document.id}/attachments/{attachment_id}",
            headers=admin_headers,
        )
        assert response.status_code in [200, 204]

    def test_delete_nonexistent_attachment(
        self, client: TestClient, auth_headers: dict, test_document
    ):
        response = client.delete(
            f"/api/v1/documents/{test_document.id}/attachments/99999",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_viewer_cannot_upload(
        self, client: TestClient, viewer_auth_headers: dict, test_document
    ):
        response = client.post(
            f"/api/v1/documents/{test_document.id}/attachments",
            headers=viewer_auth_headers,
            files={"file": ("viewer-file.docx", io.BytesIO(_fixture_bytes()), DOCX_MIME_TYPE)},
        )
        assert response.status_code == 403

    def test_cross_tenant_user_cannot_read_attachment_metadata(
        self, client: TestClient, db, tmp_path
    ):
        tenant_a = Tenant(name="Tenant A", slug="tenant-a")
        tenant_b = Tenant(name="Tenant B", slug="tenant-b")
        db.add_all([tenant_a, tenant_b])
        db.commit()
        db.refresh(tenant_a)
        db.refresh(tenant_b)

        owner = User(
            email="owner-attachment@example.com",
            username="owner_attachment",
            full_name="Owner Attachment",
            hashed_password=get_password_hash("owner123"),
            role=UserRole.ADMIN,
            tenant_id=tenant_a.id,
            is_active=True,
            is_email_verified=True,
        )
        outsider = User(
            email="outsider-attachment@example.com",
            username="outsider_attachment",
            full_name="Outsider Attachment",
            hashed_password=get_password_hash("outsider123"),
            role=UserRole.EDITOR,
            tenant_id=tenant_b.id,
            is_active=True,
            is_email_verified=True,
        )
        db.add_all([owner, outsider])
        db.commit()
        db.refresh(owner)

        document = Document(
            title="Tenant scoped document",
            document_number="DOC-TEN-ATT-001",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.INTERNAL,
            tenant_id=tenant_a.id,
            created_by=owner.id,
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        file_bytes = _fixture_bytes()
        file_path = tmp_path / "tenant-scoped.docx"
        file_path.write_bytes(file_bytes)

        attachment = Attachment(
            document_id=document.id,
            filename="tenant-scoped.docx",
            original_filename="tenant-scoped.docx",
            file_size=len(file_bytes),
            size_bytes=len(file_bytes),
            mime_type=DOCX_MIME_TYPE,
            storage_path=str(file_path),
            storage_key=str(file_path),
            uploaded_by=owner.id,
        )
        db.add(attachment)
        db.commit()
        db.refresh(attachment)

        outsider_token = _login(client, "outsider_attachment", "outsider123")
        response = client.get(
            f"/api/v1/documents/{document.id}/attachments/{attachment.id}",
            headers={"Authorization": f"Bearer {outsider_token}"},
        )
        assert response.status_code == 403

    def test_cross_tenant_download_ticket_issuance_is_denied(
        self, client: TestClient, db, tmp_path
    ):
        tenant_a = Tenant(name="Tenant Download A", slug="tenant-download-a")
        tenant_b = Tenant(name="Tenant Download B", slug="tenant-download-b")
        db.add_all([tenant_a, tenant_b])
        db.commit()
        db.refresh(tenant_a)
        db.refresh(tenant_b)

        owner = User(
            email="owner-download@example.com",
            username="owner_download",
            full_name="Owner Download",
            hashed_password=get_password_hash("owner123"),
            role=UserRole.ADMIN,
            tenant_id=tenant_a.id,
            is_active=True,
            is_email_verified=True,
        )
        outsider = User(
            email="outsider-download@example.com",
            username="outsider_download",
            full_name="Outsider Download",
            hashed_password=get_password_hash("outsider123"),
            role=UserRole.EDITOR,
            tenant_id=tenant_b.id,
            is_active=True,
            is_email_verified=True,
        )
        db.add_all([owner, outsider])
        db.commit()
        db.refresh(owner)

        document = Document(
            title="Tenant scoped download document",
            document_number="DOC-TEN-ATT-002",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.INTERNAL,
            tenant_id=tenant_a.id,
            created_by=owner.id,
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        file_bytes = _fixture_bytes()
        file_path = tmp_path / "tenant-scoped-download.docx"
        file_path.write_bytes(file_bytes)

        attachment = Attachment(
            document_id=document.id,
            filename="tenant-scoped-download.docx",
            original_filename="tenant-scoped-download.docx",
            file_size=len(file_bytes),
            size_bytes=len(file_bytes),
            mime_type=DOCX_MIME_TYPE,
            storage_path=str(file_path),
            storage_key=str(file_path),
            uploaded_by=owner.id,
        )
        db.add(attachment)
        db.commit()
        db.refresh(attachment)

        outsider_token = _login(client, "outsider_download", "outsider123")
        response = client.post(
            "/api/v1/attachments/download-ticket",
            headers={"Authorization": f"Bearer {outsider_token}"},
            json={"document_id": document.id, "attachment_id": attachment.id},
        )
        assert response.status_code == 403

    def test_customer_cannot_access_management_attachment_routes(
        self,
        client: TestClient,
        admin_headers: dict,
        customer_headers: dict,
        public_document,
    ):
        upload_response = client.post(
            f"/api/v1/documents/{public_document.id}/attachments",
            headers=admin_headers,
            files={"file": ("public.docx", io.BytesIO(_fixture_bytes()), DOCX_MIME_TYPE)},
        )
        assert upload_response.status_code == 201
        attachment_id = upload_response.json()["id"]

        list_response = client.get(
            f"/api/v1/documents/{public_document.id}/attachments",
            headers=customer_headers,
        )
        assert list_response.status_code == 403

        ticket_response = client.post(
            "/api/v1/attachments/download-ticket",
            headers=customer_headers,
            json={"document_id": public_document.id, "attachment_id": attachment_id},
        )
        assert ticket_response.status_code == 403

        download_response = client.get(
            f"/api/v1/documents/{public_document.id}/attachments/{attachment_id}/download",
            headers=customer_headers,
        )
        assert download_response.status_code == 403
