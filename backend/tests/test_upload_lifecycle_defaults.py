"""Tests for upload lifecycle and visibility default safety."""

import io
import uuid

from fastapi import HTTPException

from app.models import Document
from app.services.attachment_service import AttachmentService


def _pdf_bytes() -> bytes:
    return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"


def test_upload_defaults_to_draft_and_internal_visibility(client, auth_headers):
    """Upload without status/visibility should stay non-public draft by default."""
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("default-upload.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "draft"
    assert payload["visibility"] == "internal"


def test_editor_cannot_direct_publish_via_upload_override(client, auth_headers):
    """Editors cannot set direct-publish overrides on upload."""
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        data={"status": "active", "visibility": "public"},
        files={"file": ("editor-publish.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
    )

    assert response.status_code == 403


def test_manager_can_explicitly_publish_via_upload_override(client, manager_headers):
    """Managers and above may explicitly publish/upload as public."""
    response = client.post(
        "/api/v1/documents/upload",
        headers=manager_headers,
        data={"status": "active", "visibility": "public"},
        files={"file": ("manager-publish.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "active"
    assert payload["visibility"] == "public"


def test_release_notes_child_uses_same_default_lifecycle_policy(client, auth_headers, db):
    """Release-notes child inherits the same default draft/internal lifecycle policy."""
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={
            "file": ("main-upload.pdf", io.BytesIO(_pdf_bytes()), "application/pdf"),
            "release_notes": ("release-notes.pdf", io.BytesIO(_pdf_bytes()), "application/pdf"),
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
            "file": ("main-upload.pdf", io.BytesIO(_pdf_bytes()), "application/pdf"),
            "release_notes": ("release-notes.pdf", io.BytesIO(_pdf_bytes()), "application/pdf"),
        },
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "release notes upload failed"
    assert db.query(Document).filter(Document.title.like(f"{title}%")).count() == 0
