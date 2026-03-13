"""Tests for upload lifecycle and visibility default safety."""

import io
import uuid

from fastapi import HTTPException

from app.models import Document
from app.services.attachment_service import AttachmentService


DOCX_MIME_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def _docx_bytes() -> bytes:
    return b"PK\x03\x04minimal-docx-fixture"


def test_upload_rejects_pdf_documents(client, auth_headers):
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("legacy.pdf", io.BytesIO(b"%PDF-1.4\n%EOF"), "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "PDF uploads are not allowed"


def test_upload_defaults_to_draft_and_internal_visibility(client, auth_headers):
    """Upload without status/visibility should stay non-public draft by default."""
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("default-upload.docx", io.BytesIO(_docx_bytes()), DOCX_MIME_TYPE)},
    )

    assert response.status_code == 201, response.json()
    payload = response.json()
    assert payload["status"] == "draft"
    assert payload["visibility"] == "internal"


def test_editor_cannot_direct_publish_via_upload_override(client, auth_headers):
    """Editors cannot set direct-publish overrides on upload."""
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        data={"status": "active", "visibility": "public"},
        files={"file": ("editor-publish.docx", io.BytesIO(_docx_bytes()), DOCX_MIME_TYPE)},
    )

    assert response.status_code == 403


def test_manager_can_explicitly_publish_via_upload_override(client, manager_headers):
    """Managers and above may explicitly publish/upload as public."""
    response = client.post(
        "/api/v1/documents/upload",
        headers=manager_headers,
        data={"status": "active", "visibility": "public"},
        files={"file": ("manager-publish.docx", io.BytesIO(_docx_bytes()), DOCX_MIME_TYPE)},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "active"
    assert payload["visibility"] == "public"


def test_upload_company_visibility_requires_assignment(client, auth_headers):
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        data={"visibility": "company"},
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
        data={"visibility": "internal", "company_ids": [str(test_tenant.id)]},
        files={"file": ("company-upload.docx", io.BytesIO(_docx_bytes()), DOCX_MIME_TYPE)},
    )

    assert response.status_code == 400
    assert "Company assignments require company visibility" in response.json()["detail"]
    assert response.json()["error_code"] == "invalid_company_set"


def test_upload_rejects_invalid_company_ids_value(client, auth_headers):
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        data={"visibility": "company", "company_ids": ["abc"]},
        files={"file": ("company-upload.docx", io.BytesIO(_docx_bytes()), DOCX_MIME_TYPE)},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid company_ids value"
    assert response.json()["error_code"] == "invalid_company_set"


def test_upload_rejects_invalid_visibility_value(client, auth_headers):
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        data={"visibility": "external"},
        files={"file": ("invalid-visibility.docx", io.BytesIO(_docx_bytes()), DOCX_MIME_TYPE)},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid visibility value"
    assert response.json()["error_code"] == "invalid_visibility"


def test_upload_rejects_invalid_status_value(client, auth_headers):
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        data={"status": "ready"},
        files={"file": ("invalid-status.docx", io.BytesIO(_docx_bytes()), DOCX_MIME_TYPE)},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid status value"
    assert response.json()["error_code"] == "invalid_status"


def test_upload_company_visibility_with_assignment_succeeds(
    client, auth_headers, test_tenant
):
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        data={"visibility": "company", "company_ids": [str(test_tenant.id)]},
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
        data={"title": title},
        files={
            "file": ("main-upload.docx", io.BytesIO(_docx_bytes()), DOCX_MIME_TYPE),
            "release_notes": ("release-notes.docx", io.BytesIO(_docx_bytes()), DOCX_MIME_TYPE),
        },
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "release notes upload failed"
    assert db.query(Document).filter(Document.title.like(f"{title}%")).count() == 0
