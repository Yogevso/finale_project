"""Tests for upload lifecycle and visibility default safety."""

import io
import uuid

from fastapi import HTTPException

from app.models import Attachment, Document, Version
from app.services.attachment_service import AttachmentService
from app.conversion.pdf_to_docx import PdfConversionResult
from app.conversion.pdf_to_pptx import PdfToPptxConversionResult


DOCX_MIME_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
DEFAULT_PLATFORM = "Core Platform"


def _docx_bytes() -> bytes:
    return b"PK\x03\x04minimal-docx-fixture"


def _pdf_bytes() -> bytes:
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


def _upload_data(**overrides):
    payload = {"platform": DEFAULT_PLATFORM}
    payload.update(overrides)
    return payload


class _HtmlWrapper:
    def convert_document_to_html(self, content, mime_type, filename=""):
        return "<p>Converted DOCX body</p>"


def test_upload_requires_conversion_target_for_pdf_documents(client, auth_headers):
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        data=_upload_data(),
        files={"file": ("legacy.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "PDF uploads require pdf_conversion_target of docx or pptx"


def test_upload_rejects_pdf_conversion_target_for_non_pdf_documents(client, auth_headers):
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        data=_upload_data(pdf_conversion_target="docx"),
        files={"file": ("default-upload.docx", io.BytesIO(_docx_bytes()), DOCX_MIME_TYPE)},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "pdf_conversion_target is only supported for PDF uploads"


def test_upload_pdf_preserves_original_and_generates_docx_working_file(
    client, auth_headers, db, monkeypatch
):
    wrapper_calls = {}

    class _FakeWrapper:
        def convert_document_to_html(self, content, mime_type, filename=""):
            wrapper_calls["content"] = content
            wrapper_calls["mime_type"] = mime_type
            wrapper_calls["filename"] = filename
            return "<p>Converted PDF body</p>"

    monkeypatch.setattr(
        "app.services.attachment_service.upload.get_document_converter_wrapper",
        lambda: _FakeWrapper(),
    )
    monkeypatch.setattr(
        "app.api.management.documents.convert_pdf_to_docx",
        lambda _content: PdfConversionResult(docx_bytes=_docx_bytes(), page_count=1),
    )

    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        data=_upload_data(pdf_conversion_target="docx"),
        files={"file": ("legacy.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
    )

    assert response.status_code == 201, response.json()
    document_id = response.json()["id"]
    attachments = (
        db.query(Attachment)
        .filter(Attachment.document_id == document_id)
        .order_by(Attachment.id.asc())
        .all()
    )

    assert [attachment.original_filename for attachment in attachments] == [
        "legacy.pdf",
        "legacy.docx",
    ]
    assert [attachment.mime_type for attachment in attachments] == [
        "application/pdf",
        DOCX_MIME_TYPE,
    ]
    versions = (
        db.query(Version)
        .filter(Version.document_id == document_id)
        .order_by(Version.version_number.asc())
        .all()
    )
    assert len(versions) == 2
    assert versions[-1].content == "<p>Converted PDF body</p>"
    assert wrapper_calls == {
        "content": _pdf_bytes(),
        "mime_type": "application/pdf",
        "filename": "legacy.pdf",
    }


def test_upload_pdf_preserves_original_and_generates_pptx_working_file(
    client, auth_headers, db, monkeypatch
):
    class _FakeWrapper:
        def convert_document_to_html(self, content, mime_type, filename=""):
            return "<p>Converted PDF body</p>"

    monkeypatch.setattr(
        "app.services.attachment_service.upload.get_document_converter_wrapper",
        lambda: _FakeWrapper(),
    )
    monkeypatch.setattr(
        "app.api.management.documents.convert_pdf_to_pptx",
        lambda _content: PdfToPptxConversionResult(
            pptx_bytes=b"PK\x03\x04generated-pptx",
            page_count=1,
        ),
    )

    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        data=_upload_data(pdf_conversion_target="pptx"),
        files={"file": ("deck.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
    )

    assert response.status_code == 201, response.json()
    document_id = response.json()["id"]
    attachments = (
        db.query(Attachment)
        .filter(Attachment.document_id == document_id)
        .order_by(Attachment.id.asc())
        .all()
    )

    assert [attachment.original_filename for attachment in attachments] == [
        "deck.pdf",
        "deck.pptx",
    ]
    assert [attachment.mime_type for attachment in attachments] == [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ]


def test_upload_requires_platform(client, auth_headers):
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("default-upload.docx", io.BytesIO(_docx_bytes()), DOCX_MIME_TYPE)},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Platform is required"


def test_upload_defaults_to_draft_and_internal_visibility(client, auth_headers, db, monkeypatch):
    """Upload with a platform but without status/visibility should stay non-public draft."""
    monkeypatch.setattr(
        "app.services.attachment_service.upload.get_document_converter_wrapper",
        lambda: _HtmlWrapper(),
    )
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        data=_upload_data(),
        files={"file": ("default-upload.docx", io.BytesIO(_docx_bytes()), DOCX_MIME_TYPE)},
    )

    assert response.status_code == 201, response.json()
    payload = response.json()
    assert payload["status"] == "draft"
    assert payload["visibility"] == "internal"
    versions = (
        db.query(Version)
        .filter(Version.document_id == payload["id"])
        .order_by(Version.version_number.asc())
        .all()
    )
    assert len(versions) == 2
    assert versions[-1].is_published is False


def test_editor_cannot_direct_publish_via_upload_override(client, auth_headers):
    """Editors cannot set direct-publish overrides on upload."""
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        data=_upload_data(status="active", visibility="public"),
        files={"file": ("editor-publish.docx", io.BytesIO(_docx_bytes()), DOCX_MIME_TYPE)},
    )

    assert response.status_code == 403


def test_manager_can_explicitly_publish_via_upload_override(client, manager_headers, db, monkeypatch):
    """Managers and above may explicitly publish/upload as public."""
    monkeypatch.setattr(
        "app.services.attachment_service.upload.get_document_converter_wrapper",
        lambda: _HtmlWrapper(),
    )
    response = client.post(
        "/api/v1/documents/upload",
        headers=manager_headers,
        data=_upload_data(status="active", visibility="public"),
        files={"file": ("manager-publish.docx", io.BytesIO(_docx_bytes()), DOCX_MIME_TYPE)},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "active"
    assert payload["visibility"] == "public"
    versions = (
        db.query(Version)
        .filter(Version.document_id == payload["id"])
        .order_by(Version.version_number.asc())
        .all()
    )
    assert len(versions) == 2
    assert versions[-1].is_published is True
    assert versions[-1].published_at is not None


def test_upload_company_visibility_requires_assignment(client, auth_headers):
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        data=_upload_data(visibility="company"),
        files={"file": ("company-upload.docx", io.BytesIO(_docx_bytes()), DOCX_MIME_TYPE)},
    )

    assert response.status_code == 400
    assert "at least one assigned company" in response.json()["detail"]
    assert response.json()["error_code"] == "missing_company_assignment"


def test_upload_non_company_visibility_rejects_company_assignments(
    client, auth_headers, test_tenant
):
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        data=_upload_data(visibility="internal", company_ids=[str(test_tenant.id)]),
        files={"file": ("company-upload.docx", io.BytesIO(_docx_bytes()), DOCX_MIME_TYPE)},
    )

    assert response.status_code == 400
    assert "Company assignments require company visibility" in response.json()["detail"]
    assert response.json()["error_code"] == "invalid_company_set"


def test_upload_rejects_invalid_company_ids_value(client, auth_headers):
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        data=_upload_data(visibility="company", company_ids=["abc"]),
        files={"file": ("company-upload.docx", io.BytesIO(_docx_bytes()), DOCX_MIME_TYPE)},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid company_ids value"
    assert response.json()["error_code"] == "invalid_company_set"


def test_upload_rejects_invalid_visibility_value(client, auth_headers):
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        data=_upload_data(visibility="external"),
        files={"file": ("invalid-visibility.docx", io.BytesIO(_docx_bytes()), DOCX_MIME_TYPE)},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid visibility value"
    assert response.json()["error_code"] == "invalid_visibility"


def test_upload_rejects_invalid_status_value(client, auth_headers):
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        data=_upload_data(status="ready"),
        files={"file": ("invalid-status.docx", io.BytesIO(_docx_bytes()), DOCX_MIME_TYPE)},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid status value"
    assert response.json()["error_code"] == "invalid_status"


def test_upload_company_visibility_with_assignment_succeeds(
    client, system_admin_headers, test_tenant
):
    response = client.post(
        "/api/v1/documents/upload",
        headers=system_admin_headers,
        data=_upload_data(visibility="company", company_ids=[str(test_tenant.id)]),
        files={"file": ("company-upload.docx", io.BytesIO(_docx_bytes()), DOCX_MIME_TYPE)},
    )

    assert response.status_code == 201, response.json()
    payload = response.json()
    assert payload["visibility"] == "company"
    assert sorted(company["id"] for company in payload["assigned_companies"]) == [test_tenant.id]


def test_release_notes_child_uses_same_default_lifecycle_policy(client, auth_headers, db):
    """Release-notes child inherits the same default draft/internal lifecycle policy."""
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        data=_upload_data(),
        files={
            "file": ("main-upload.docx", io.BytesIO(_docx_bytes()), DOCX_MIME_TYPE),
            "release_notes": ("release-notes.docx", io.BytesIO(_docx_bytes()), DOCX_MIME_TYPE),
        },
    )

    assert response.status_code == 201
    parent_id = response.json()["id"]
    children = db.query(Document).filter(Document.parent_id == parent_id).all()
    assert len(children) == 1

    child = children[0]
    assert child.status.value == "draft"
    assert child.visibility.value == "internal"
    assert child.platform == DEFAULT_PLATFORM


def test_release_notes_upload_failure_rolls_back_parent_and_child(
    client, auth_headers, db, monkeypatch
):
    """Failure during release-notes upload should not leave parent/child document rows behind."""
    call_counter = {"count": 0}

    async def fake_upload_attachment(*args, **kwargs):
        call_counter["count"] += 1
        if call_counter["count"] == 2:
            raise HTTPException(status_code=500, detail="release notes upload failed")
        return None

    monkeypatch.setattr(AttachmentService, "upload_attachment", fake_upload_attachment)

    marker = uuid.uuid4().hex[:8]
    title = f"Rollback Upload {marker}"
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        data=_upload_data(title=title),
        files={
            "file": ("main-upload.docx", io.BytesIO(_docx_bytes()), DOCX_MIME_TYPE),
            "release_notes": ("release-notes.docx", io.BytesIO(_docx_bytes()), DOCX_MIME_TYPE),
        },
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "release notes upload failed"
    assert db.query(Document).filter(Document.title.like(f"{title}%")).count() == 0
