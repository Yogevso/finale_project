"""Wave AF — Publication Integrity & API Cleanup tests.

AF-014: Public endpoint returns 404 when no published version exists.
AF-015: Public/portal response includes only attachments from published snapshot.
AF-016: Portal reading-progress excludes documents user lost access to.
AF-017: Public changelog route is not in management router namespace.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models import (
    Attachment,
    ChangelogEntry,
    Document,
    DocumentStatus,
    DocumentVisibility,
    ReadingProgress,
    Tenant,
    User,
    UserRole,
    Version,
    VersionBumpType,
)
from tests.factories.domain import create_document, create_tenant, create_user, persist


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_published_doc(
    db: Session,
    *,
    created_by: int,
    visibility: DocumentVisibility = DocumentVisibility.PUBLIC,
    tenant_id: int | None = None,
) -> tuple[Document, Version]:
    """Create a PUBLIC/ACTIVE document with one published version."""
    doc = create_document(
        db,
        created_by=created_by,
        status=DocumentStatus.PUBLISHED,
        visibility=visibility,
        tenant_id=tenant_id,
    )
    v = Version(
        document_id=doc.id,
        version_number=1,
        semantic_version="1.0.0",
        bump_type=VersionBumpType.PATCH,
        content="<p>Published content</p>",
        changes_summary="Initial publish",
        is_published=True,
        published_at=datetime.utcnow() - timedelta(hours=1),
        published_by=created_by,
        created_by=created_by,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return doc, v


def _make_draft_only_doc(
    db: Session,
    *,
    created_by: int,
    visibility: DocumentVisibility = DocumentVisibility.PUBLIC,
) -> tuple[Document, Version]:
    """Create a PUBLIC/ACTIVE document with NO published version (only draft)."""
    doc = create_document(
        db,
        created_by=created_by,
        status=DocumentStatus.PUBLISHED,
        visibility=visibility,
    )
    v = Version(
        document_id=doc.id,
        version_number=1,
        semantic_version="0.1.0",
        bump_type=VersionBumpType.PATCH,
        content="<p>Draft content - should never be public</p>",
        changes_summary="Draft",
        is_published=False,
        created_by=created_by,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return doc, v


# ===========================================================================
# AF-014: Public document endpoint returns 404 when no published version
# ===========================================================================
class TestAF014NoDraftFallback:
    """Public document endpoint must return 404 when no published version exists."""

    def test_public_detail_404_when_no_published_version(self, client, db):
        """AF-014: GET /public/documents/{id} returns 404 for draft-only doc."""
        user = create_user(db, role=UserRole.EDITOR)
        doc, _ = _make_draft_only_doc(db, created_by=user.id)

        resp = client.get(f"/api/v1/public/documents/{doc.id}")
        assert resp.status_code == 404
        assert "no published version" in resp.json()["detail"].lower()

    def test_public_detail_200_when_published_version_exists(self, client, db):
        """Sanity check: published doc returns 200 with published content."""
        user = create_user(db, role=UserRole.EDITOR)
        doc, version = _make_published_doc(db, created_by=user.id)

        resp = client.get(f"/api/v1/public/documents/{doc.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["content"] == "<p>Published content</p>"
        assert body["version_number"] == 1


# ===========================================================================
# AF-015: Attachments scoped to published snapshot
# ===========================================================================
class TestAF015AttachmentSnapshot:
    """Public/viewer responses must only include attachments from the published snapshot."""

    def test_public_attachments_exclude_post_publish_uploads(self, client, db):
        """AF-015: Attachments uploaded after publish are excluded from public response."""
        user = create_user(db, role=UserRole.EDITOR)
        doc, version = _make_published_doc(db, created_by=user.id)

        publish_time = version.published_at

        # Attachment uploaded BEFORE publish — should be included
        old_att = Attachment(
            document_id=doc.id,
            filename="before.pdf",
            original_filename="before.pdf",
            file_size=100,
            size_bytes=100,
            mime_type="application/pdf",
            storage_path="/tmp/before.pdf",
            storage_key="/tmp/before.pdf",
            uploaded_by=user.id,
            uploaded_at=publish_time - timedelta(hours=2),
        )
        db.add(old_att)
        db.commit()

        # Attachment uploaded AFTER publish — should be excluded
        new_att = Attachment(
            document_id=doc.id,
            filename="after.pdf",
            original_filename="after.pdf",
            file_size=200,
            size_bytes=200,
            mime_type="application/pdf",
            storage_path="/tmp/after.pdf",
            storage_key="/tmp/after.pdf",
            uploaded_by=user.id,
            uploaded_at=publish_time + timedelta(hours=2),
        )
        db.add(new_att)
        db.commit()

        resp = client.get(f"/api/v1/public/documents/{doc.id}")
        assert resp.status_code == 200
        body = resp.json()

        attachment_filenames = [a["filename"] for a in body["attachments"]]
        assert "before.pdf" in attachment_filenames
        assert "after.pdf" not in attachment_filenames

    def test_viewer_attachments_exclude_post_publish_uploads(self, client, db):
        """AF-015: Viewer attachment listing scoped to latest publish time."""
        user = create_user(db, role=UserRole.EDITOR)
        doc, version = _make_published_doc(db, created_by=user.id)
        publish_time = version.published_at

        old_att = Attachment(
            document_id=doc.id,
            filename="included.pdf",
            original_filename="included.pdf",
            file_size=100,
            size_bytes=100,
            mime_type="application/pdf",
            storage_path="/tmp/included.pdf",
            storage_key="/tmp/included.pdf",
            uploaded_by=user.id,
            uploaded_at=publish_time - timedelta(hours=1),
        )
        new_att = Attachment(
            document_id=doc.id,
            filename="excluded.pdf",
            original_filename="excluded.pdf",
            file_size=200,
            size_bytes=200,
            mime_type="application/pdf",
            storage_path="/tmp/excluded.pdf",
            storage_key="/tmp/excluded.pdf",
            uploaded_by=user.id,
            uploaded_at=publish_time + timedelta(hours=1),
        )
        db.add_all([old_att, new_att])
        db.commit()

        resp = client.get(f"/api/v1/viewer/documents/{doc.id}/attachments")
        assert resp.status_code == 200
        filenames = [a["filename"] for a in resp.json()]
        assert "included.pdf" in filenames
        assert "excluded.pdf" not in filenames


# ===========================================================================
# AF-016: Portal reading-progress re-checks access
# ===========================================================================
class TestAF016ReadingProgressAccessCheck:
    """Portal reading-progress endpoints must exclude documents user can no longer access."""

    def _auth_header(self, client, db, user, password="Test1234!"):
        """Get auth token for a customer user."""
        from app.security import create_access_token

        token = create_access_token(data={"sub": str(user.id)})
        return {"Authorization": f"Bearer {token}"}

    def test_reading_progress_excludes_archived_document(self, client, db):
        """AF-016: Archived document should not appear in reading progress."""
        tenant = create_tenant(db)
        customer = create_user(
            db, role=UserRole.CUSTOMER, tenant_id=tenant.id
        )
        editor = create_user(db, role=UserRole.EDITOR, tenant_id=tenant.id)

        # Create a document that was accessible, create reading progress
        doc = create_document(
            db,
            created_by=editor.id,
            status=DocumentStatus.PUBLISHED,
            visibility=DocumentVisibility.PUBLIC,
            tenant_id=tenant.id,
        )

        rp = ReadingProgress(
            user_id=customer.id,
            document_id=doc.id,
            progress_percent=50,
            last_read_at=datetime.utcnow(),
        )
        db.add(rp)
        db.commit()

        headers = self._auth_header(client, db, customer)

        # First, verify it appears
        resp = client.get("/api/v1/portal/reading-progress/recent", headers=headers)
        assert resp.status_code == 200
        ids = [r["document_id"] for r in resp.json()]
        assert doc.id in ids

        # Now archive the document — access should be revoked
        doc.status = DocumentStatus.ARCHIVED
        db.commit()

        resp = client.get("/api/v1/portal/reading-progress/recent", headers=headers)
        assert resp.status_code == 200
        ids = [r["document_id"] for r in resp.json()]
        assert doc.id not in ids

    def test_continue_reading_excludes_internal_document(self, client, db):
        """AF-016: Internal document should not appear in customer's continue reading."""
        tenant = create_tenant(db)
        customer = create_user(
            db, role=UserRole.CUSTOMER, tenant_id=tenant.id
        )
        editor = create_user(db, role=UserRole.EDITOR, tenant_id=tenant.id)

        doc = create_document(
            db,
            created_by=editor.id,
            status=DocumentStatus.PUBLISHED,
            visibility=DocumentVisibility.PUBLIC,
            tenant_id=tenant.id,
        )

        rp = ReadingProgress(
            user_id=customer.id,
            document_id=doc.id,
            progress_percent=30,
            last_read_at=datetime.utcnow(),
        )
        db.add(rp)
        db.commit()

        headers = self._auth_header(client, db, customer)

        # Appears while public
        resp = client.get("/api/v1/portal/reading-progress/continue", headers=headers)
        assert resp.status_code == 200
        ids = [r["document_id"] for r in resp.json()]
        assert doc.id in ids

        # Change to internal — customer should lose access
        doc.visibility = DocumentVisibility.INTERNAL
        db.commit()

        resp = client.get("/api/v1/portal/reading-progress/continue", headers=headers)
        assert resp.status_code == 200
        ids = [r["document_id"] for r in resp.json()]
        assert doc.id not in ids

    def test_portal_reading_progress_list_returns_customer_progress(self, client, db):
        tenant = create_tenant(db)
        customer = create_user(db, role=UserRole.CUSTOMER, tenant_id=tenant.id)
        editor = create_user(db, role=UserRole.EDITOR, tenant_id=tenant.id)

        doc = create_document(
            db,
            created_by=editor.id,
            status=DocumentStatus.PUBLISHED,
            visibility=DocumentVisibility.PUBLIC,
            tenant_id=tenant.id,
        )
        db.add(
            ReadingProgress(
                user_id=customer.id,
                document_id=doc.id,
                progress_percent=45,
                last_read_at=datetime.utcnow(),
            )
        )
        db.commit()

        headers = self._auth_header(client, db, customer)
        resp = client.get("/api/v1/portal/reading-progress", headers=headers)

        assert resp.status_code == 200
        payload = resp.json()
        assert len(payload) == 1
        assert payload[0]["document_id"] == doc.id
        assert payload[0]["progress_percent"] == 45

    def test_portal_reading_progress_get_and_update(self, client, db):
        tenant = create_tenant(db)
        customer = create_user(db, role=UserRole.CUSTOMER, tenant_id=tenant.id)
        editor = create_user(db, role=UserRole.EDITOR, tenant_id=tenant.id)

        doc = create_document(
            db,
            created_by=editor.id,
            status=DocumentStatus.PUBLISHED,
            visibility=DocumentVisibility.PUBLIC,
            tenant_id=tenant.id,
        )

        headers = self._auth_header(client, db, customer)

        initial = client.get(f"/api/v1/portal/reading-progress/{doc.id}", headers=headers)
        assert initial.status_code == 200
        assert initial.json()["has_progress"] is False

        update = client.put(
            f"/api/v1/portal/reading-progress/{doc.id}",
            headers=headers,
            json={"progress_percent": 60},
        )
        assert update.status_code == 200
        assert update.json()["document_id"] == doc.id
        assert update.json()["progress_percent"] == 60

        fetched = client.get(f"/api/v1/portal/reading-progress/{doc.id}", headers=headers)
        assert fetched.status_code == 200
        assert fetched.json()["has_progress"] is True
        assert fetched.json()["progress_percent"] == 60


# ===========================================================================
# AF-017: Public changelog is NOT in management router namespace
# ===========================================================================
class TestAF017PublicChangelogRoute:
    """Public changelog must be served from the public API namespace, not management."""

    def test_public_changelog_accessible_without_auth(self, client, db):
        """AF-017: GET /public/changelog returns published entries without auth."""
        user = create_user(db, role=UserRole.MANAGER)
        entry = ChangelogEntry(
            title="v2.0 Release",
            content="Major improvements",
            published=True,
            created_by=user.id,
        )
        db.add(entry)
        db.commit()

        resp = client.get("/api/v1/public/changelog")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        titles = [item["title"] for item in body["items"]]
        assert "v2.0 Release" in titles

    def test_management_changelog_requires_auth(self, client, db):
        """AF-017: GET /changelog (management) requires manager auth."""
        resp = client.get("/api/v1/changelog")
        # Should be 401 or 403 without auth
        assert resp.status_code in (401, 403)

    def test_public_changelog_excludes_unpublished(self, client, db):
        """AF-017: Public changelog only returns published entries."""
        user = create_user(db, role=UserRole.MANAGER)
        published = ChangelogEntry(
            title="Public Entry",
            content="Visible",
            published=True,
            created_by=user.id,
        )
        draft = ChangelogEntry(
            title="Draft Entry",
            content="Hidden",
            published=False,
            created_by=user.id,
        )
        db.add_all([published, draft])
        db.commit()

        resp = client.get("/api/v1/public/changelog")
        assert resp.status_code == 200
        titles = [item["title"] for item in resp.json()["items"]]
        assert "Public Entry" in titles
        assert "Draft Entry" not in titles
