"""Tests for Viewer Portal (Public Document Access)"""

import uuid
from datetime import datetime, timedelta

from app.models import (
    Attachment,
    AttachmentArtifact,
    Comment,
    Document,
    DocumentStatus,
    DocumentVisibility,
    Version,
)


class TestViewerDocuments:
    """Tests for public viewer document endpoints"""

    def test_list_published_documents(self, client, db, test_user):
        """List published documents (no auth required)"""
        # Create active document
        doc = Document(
            title="Public Document",
            document_number=f"DOC-PUB-{uuid.uuid4().hex[:6].upper()}",
            description="A publicly viewable document",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.PUBLIC,
            created_by=test_user.id,
        )
        db.add(doc)
        db.commit()

        # Access without auth
        response = client.get("/api/v1/viewer/documents")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_list_documents_excludes_draft(self, client, db, test_user):
        """Draft documents should not appear in viewer"""
        # Create draft document
        doc = Document(
            title="Draft Document",
            document_number=f"DOC-DRF-{uuid.uuid4().hex[:6].upper()}",
            status=DocumentStatus.DRAFT,
            created_by=test_user.id,
        )
        db.add(doc)
        db.commit()

        response = client.get("/api/v1/viewer/documents")
        assert response.status_code == 200
        data = response.json()
        # Draft should not appear
        titles = [item["title"] for item in data["items"]]
        assert "Draft Document" not in titles

    def test_list_documents_with_search(self, client, db, test_user):
        """Search published documents"""
        doc = Document(
            title="Searchable Public Doc",
            document_number=f"DOC-SRC-{uuid.uuid4().hex[:6].upper()}",
            description="Contains unique searchterm123",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.PUBLIC,
            created_by=test_user.id,
        )
        db.add(doc)
        db.commit()

        response = client.get("/api/v1/viewer/documents?search=searchterm123")
        assert response.status_code == 200

    def test_list_documents_with_category(self, client, db, test_user):
        """Filter by category"""
        doc = Document(
            title="Categorized Doc",
            document_number=f"DOC-CAT-{uuid.uuid4().hex[:6].upper()}",
            category="policies",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.PUBLIC,
            created_by=test_user.id,
        )
        db.add(doc)
        db.commit()

        response = client.get("/api/v1/viewer/documents?category=policies")
        assert response.status_code == 200

    def test_list_documents_pagination(self, client, db, test_user):
        """Test pagination"""
        # Create multiple documents
        for i in range(5):
            doc = Document(
                title=f"Pagination Test Doc {i}",
                document_number=f"DOC-PAG{i}-{uuid.uuid4().hex[:4].upper()}",
                status=DocumentStatus.ACTIVE,
                visibility=DocumentVisibility.PUBLIC,
                created_by=test_user.id,
            )
            db.add(doc)
        db.commit()

        response = client.get("/api/v1/viewer/documents?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2

    def test_get_document_detail(self, client, db, test_user):
        """Get single document details"""
        doc = Document(
            title="Detail Test Doc",
            document_number=f"DOC-DTL-{uuid.uuid4().hex[:6].upper()}",
            description="Document for detail testing",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.PUBLIC,
            created_by=test_user.id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        response = client.get(f"/api/v1/viewer/documents/{doc.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Detail Test Doc"

    def test_get_draft_document_returns_404(self, client, db, test_user):
        """Draft documents are not accessible via viewer"""
        doc = Document(
            title="Hidden Draft",
            document_number=f"DOC-HID-{uuid.uuid4().hex[:6].upper()}",
            status=DocumentStatus.DRAFT,
            created_by=test_user.id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        response = client.get(f"/api/v1/viewer/documents/{doc.id}")
        assert response.status_code == 404

    def test_get_nonexistent_document(self, client):
        """Get document that doesn't exist"""
        response = client.get("/api/v1/viewer/documents/99999")
        assert response.status_code == 404

    def test_list_documents_excludes_internal_visibility(self, client, db, test_user):
        """Active non-public documents should not appear in public viewer."""
        internal_doc = Document(
            title="Internal Active Doc",
            document_number=f"DOC-INT-{uuid.uuid4().hex[:6].upper()}",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.INTERNAL,
            created_by=test_user.id,
        )
        db.add(internal_doc)
        db.commit()

        response = client.get("/api/v1/viewer/documents")
        assert response.status_code == 200
        titles = [item["title"] for item in response.json()["items"]]
        assert "Internal Active Doc" not in titles

    def test_get_internal_active_document_returns_404(self, client, db, test_user):
        """Active internal documents should not be fetchable through public viewer detail."""
        internal_doc = Document(
            title="Internal Detail Doc",
            document_number=f"DOC-INTD-{uuid.uuid4().hex[:6].upper()}",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.INTERNAL,
            created_by=test_user.id,
        )
        db.add(internal_doc)
        db.commit()
        db.refresh(internal_doc)

        response = client.get(f"/api/v1/viewer/documents/{internal_doc.id}")
        assert response.status_code == 404


class TestViewerVersions:
    """Tests for viewer version endpoints"""

    def test_list_document_versions(self, client, db, test_user):
        """List versions for a published document"""
        doc = Document(
            title="Version Test Doc",
            document_number=f"DOC-VER-{uuid.uuid4().hex[:6].upper()}",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.PUBLIC,
            created_by=test_user.id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        # Create a published version with correct fields
        version = Version(
            document_id=doc.id,
            version_number=1,
            changes_summary="Initial version",
            is_published=True,
            created_by=test_user.id,
        )
        db.add(version)
        db.commit()

        response = client.get(f"/api/v1/viewer/documents/{doc.id}/versions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_versions_excludes_unpublished(self, client, db, test_user):
        """Unpublished versions should not appear in viewer"""
        doc = Document(
            title="Unpub Version Test",
            document_number=f"DOC-UVT-{uuid.uuid4().hex[:6].upper()}",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.PUBLIC,
            created_by=test_user.id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        # Create an unpublished version
        version = Version(
            document_id=doc.id,
            version_number=1,
            changes_summary="Draft version",
            is_published=False,
            created_by=test_user.id,
        )
        db.add(version)
        db.commit()

        response = client.get(f"/api/v1/viewer/documents/{doc.id}/versions")
        assert response.status_code == 200
        # Unpublished version should not appear
        data = response.json()
        assert len(data) == 0


class TestViewerComments:
    """Tests for viewer comment endpoints"""

    def test_list_document_comments(self, client, db, test_user):
        """List comments on a document"""
        doc = Document(
            title="Comment Test Doc",
            document_number=f"DOC-CMT-{uuid.uuid4().hex[:6].upper()}",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.PUBLIC,
            created_by=test_user.id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        # Add comment
        comment = Comment(
            document_id=doc.id, content="This is a test comment", user_id=test_user.id
        )
        db.add(comment)
        db.commit()

        response = client.get(f"/api/v1/viewer/documents/{doc.id}/comments")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_private_comments_are_not_exposed(self, client, db, test_user):
        """Viewer comments should exclude private/internal comments."""
        doc = Document(
            title="Public Comment Privacy Doc",
            document_number=f"DOC-PCP-{uuid.uuid4().hex[:6].upper()}",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.PUBLIC,
            created_by=test_user.id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        public_comment = Comment(
            document_id=doc.id,
            content="Public comment",
            user_id=test_user.id,
            is_private=False,
        )
        private_comment = Comment(
            document_id=doc.id,
            content="Private comment",
            user_id=test_user.id,
            is_private=True,
        )
        db.add_all([public_comment, private_comment])
        db.commit()

        response = client.get(f"/api/v1/viewer/documents/{doc.id}/comments")
        assert response.status_code == 200
        payload = response.json()
        contents = {item["content"] for item in payload}
        assert "Public comment" in contents
        assert "Private comment" not in contents


class TestViewerAttachments:
    """Tests for viewer attachment endpoints"""

    def test_list_document_attachments(self, client, db, test_user):
        """List attachments for a document"""
        doc = Document(
            title="Attachment Test Doc",
            document_number=f"DOC-ATT-{uuid.uuid4().hex[:6].upper()}",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.PUBLIC,
            created_by=test_user.id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        # Add attachment with correct field names
        attachment = Attachment(
            document_id=doc.id,
            filename="test.pdf",
            original_filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_path="/uploads/test.pdf",
            uploaded_by=test_user.id,
        )
        db.add(attachment)
        db.commit()

        response = client.get(f"/api/v1/viewer/documents/{doc.id}/attachments")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_version_attachments(self, client, db, test_user):
        """List attachments resolved for a selected published version."""
        doc = Document(
            title="Version Attachment Scope",
            document_number=f"DOC-VAS-{uuid.uuid4().hex[:6].upper()}",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.PUBLIC,
            created_by=test_user.id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        now = datetime.utcnow()
        v1_time = now - timedelta(days=2)
        v2_time = now - timedelta(days=1)

        version_one = Version(
            document_id=doc.id,
            version_number=1,
            is_published=True,
            created_by=test_user.id,
            created_at=v1_time,
            published_at=v1_time,
        )
        version_two = Version(
            document_id=doc.id,
            version_number=2,
            is_published=True,
            created_by=test_user.id,
            created_at=v2_time,
            published_at=v2_time,
        )
        db.add_all([version_one, version_two])
        db.commit()
        db.refresh(version_one)
        db.refresh(version_two)

        attachment_one = Attachment(
            document_id=doc.id,
            filename="v1.pdf",
            original_filename="v1.pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_path="/uploads/v1.pdf",
            uploaded_by=test_user.id,
            uploaded_at=v1_time - timedelta(minutes=5),
        )
        attachment_two = Attachment(
            document_id=doc.id,
            filename="v2.pdf",
            original_filename="v2.pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_path="/uploads/v2.pdf",
            uploaded_by=test_user.id,
            uploaded_at=v2_time - timedelta(minutes=5),
        )
        db.add_all([attachment_one, attachment_two])
        db.commit()

        first_response = client.get(
            f"/api/v1/viewer/documents/{doc.id}/versions/{version_one.id}/attachments"
        )
        assert first_response.status_code == 200
        first_ids = {item["id"] for item in first_response.json()}
        assert attachment_one.id in first_ids
        assert attachment_two.id not in first_ids

        second_response = client.get(
            f"/api/v1/viewer/documents/{doc.id}/versions/{version_two.id}/attachments"
        )
        assert second_response.status_code == 200
        second_ids = {item["id"] for item in second_response.json()}
        assert attachment_one.id in second_ids
        assert attachment_two.id in second_ids

    def test_public_attachment_download_and_preview(self, client, db, test_user, tmp_path):
        """Public viewer should stream attachment bytes without auth."""
        doc = Document(
            title="Viewer Stream Doc",
            document_number=f"DOC-VSD-{uuid.uuid4().hex[:6].upper()}",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.PUBLIC,
            created_by=test_user.id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        file_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"
        file_path = tmp_path / "viewer-stream.pdf"
        file_path.write_bytes(file_bytes)

        attachment = Attachment(
            document_id=doc.id,
            filename="viewer-stream.pdf",
            original_filename="viewer-stream.pdf",
            file_size=len(file_bytes),
            size_bytes=len(file_bytes),
            mime_type="application/pdf",
            storage_path=str(file_path),
            storage_key=str(file_path),
            uploaded_by=test_user.id,
        )
        db.add(attachment)
        db.commit()
        db.refresh(attachment)

        preview_response = client.get(
            f"/api/v1/viewer/documents/{doc.id}/attachments/{attachment.id}/preview"
        )
        assert preview_response.status_code == 200
        assert "inline;" in preview_response.headers["content-disposition"]
        assert preview_response.content == file_bytes

        download_response = client.get(
            f"/api/v1/viewer/documents/{doc.id}/attachments/{attachment.id}/download"
        )
        assert download_response.status_code == 200
        assert "attachment;" in download_response.headers["content-disposition"]
        assert download_response.content == file_bytes

    def test_public_attachment_outline(self, client, db, test_user, tmp_path):
        """Public viewer should expose outline payload for PDF attachments."""
        doc = Document(
            title="Viewer Outline Doc",
            document_number=f"DOC-VOD-{uuid.uuid4().hex[:6].upper()}",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.PUBLIC,
            created_by=test_user.id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        file_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"
        file_path = tmp_path / "viewer-outline.pdf"
        file_path.write_bytes(file_bytes)

        attachment = Attachment(
            document_id=doc.id,
            filename="viewer-outline.pdf",
            original_filename="viewer-outline.pdf",
            file_size=len(file_bytes),
            size_bytes=len(file_bytes),
            mime_type="application/pdf",
            storage_path=str(file_path),
            storage_key=str(file_path),
            uploaded_by=test_user.id,
        )
        db.add(attachment)
        db.commit()
        db.refresh(attachment)

        response = client.get(
            f"/api/v1/viewer/documents/{doc.id}/attachments/{attachment.id}/outline"
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["attachment_id"] == attachment.id
        assert "items" in payload

    def test_preview_stream_prefers_preview_artifact_over_original(
        self, client, db, test_user, tmp_path
    ):
        """Public preview endpoint should stream preview PDF artifact bytes."""
        doc = Document(
            title="Preview Artifact Preference",
            document_number=f"DOC-PAP-{uuid.uuid4().hex[:6].upper()}",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.PUBLIC,
            created_by=test_user.id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        original_bytes = b"ORIGINAL-DOCX-BYTES"
        preview_bytes = b"%PDF-1.4\nPREVIEW\n%%EOF"

        original_path = tmp_path / "source.docx"
        preview_path = tmp_path / "source.preview.pdf"
        original_path.write_bytes(original_bytes)
        preview_path.write_bytes(preview_bytes)

        attachment = Attachment(
            document_id=doc.id,
            filename="source.docx",
            original_filename="source.docx",
            file_size=len(original_bytes),
            size_bytes=len(original_bytes),
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            storage_path=str(original_path),
            storage_key=str(original_path),
            uploaded_by=test_user.id,
            preview_pdf_status="ready",
            preview_pdf_storage_key=str(preview_path),
            preview_pdf_size_bytes=len(preview_bytes),
            preview_pdf_mime_type="application/pdf",
        )
        db.add(attachment)
        db.commit()
        db.refresh(attachment)

        preview_artifact = AttachmentArtifact(
            attachment_id=attachment.id,
            kind="preview_pdf",
            status="ready",
            storage_key=str(preview_path),
            mime_type="application/pdf",
            size_bytes=len(preview_bytes),
        )
        db.add(preview_artifact)
        db.commit()

        preview_response = client.get(
            f"/api/v1/viewer/documents/{doc.id}/attachments/{attachment.id}/preview"
        )
        assert preview_response.status_code == 200
        assert preview_response.content == preview_bytes

        download_response = client.get(
            f"/api/v1/viewer/documents/{doc.id}/attachments/{attachment.id}/download"
        )
        assert download_response.status_code == 200
        assert download_response.content == original_bytes

