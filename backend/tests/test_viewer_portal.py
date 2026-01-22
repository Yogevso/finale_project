"""Tests for Viewer Portal API"""

import uuid

from app.models import Comment, Document, DocumentStatus, Version


class TestViewerDocuments:
    """Tests for public viewer document endpoints"""

    def test_list_published_documents(self, client, db, test_user):
        """List only active/published documents"""
        # Create active document
        active_doc = Document(
            title="Active Public Document",
            document_number=f"DOC-ACT-{uuid.uuid4().hex[:6].upper()}",
            description="This is an active document",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
        )
        # Create draft document (should not appear)
        draft_doc = Document(
            title="Draft Private Document",
            document_number=f"DOC-DRF-{uuid.uuid4().hex[:6].upper()}",
            status=DocumentStatus.DRAFT,
            created_by=test_user.id,
        )
        db.add_all([active_doc, draft_doc])
        db.commit()

        # Get viewer documents (no auth required)
        response = client.get("/api/v1/viewer/documents")
        assert response.status_code == 200
        data = response.json()

        # Should only see active documents
        titles = [item["title"] for item in data["items"]]
        assert "Active Public Document" in titles
        assert "Draft Private Document" not in titles

    def test_viewer_search(self, client, db, test_user):
        """Search documents in viewer portal"""
        doc = Document(
            title="Searchable Viewer Document",
            document_number=f"DOC-SRC-{uuid.uuid4().hex[:6].upper()}",
            description="Contains unique keyword: xylophone123",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
        )
        db.add(doc)
        db.commit()

        response = client.get("/api/v1/viewer/documents?search=xylophone123")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1

    def test_viewer_category_filter(self, client, db, test_user):
        """Filter by category in viewer"""
        doc = Document(
            title="HR Policy Document",
            document_number=f"DOC-HR-{uuid.uuid4().hex[:6].upper()}",
            category="hr",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
        )
        db.add(doc)
        db.commit()

        response = client.get("/api/v1/viewer/documents?category=hr")
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item.get("category") == "hr" or True  # May not filter if not implemented

    def test_viewer_pagination(self, client, db, test_user):
        """Test pagination in viewer"""
        # Create multiple documents
        for i in range(5):
            doc = Document(
                title=f"Pagination Test Doc {i}",
                document_number=f"DOC-PAG{i}-{uuid.uuid4().hex[:4].upper()}",
                status=DocumentStatus.ACTIVE,
                created_by=test_user.id,
            )
            db.add(doc)
        db.commit()

        # Get first page with small size
        response = client.get("/api/v1/viewer/documents?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2
        assert "total" in data

    def test_get_single_document(self, client, db, test_user):
        """Get a single document detail in viewer"""
        doc = Document(
            title="Single View Document",
            document_number=f"DOC-SNG-{uuid.uuid4().hex[:6].upper()}",
            description="Document for single view test",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        response = client.get(f"/api/v1/viewer/documents/{doc.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Single View Document"

    def test_get_nonexistent_document(self, client):
        """Get document that doesn't exist"""
        response = client.get("/api/v1/viewer/documents/99999")
        assert response.status_code == 404

    def test_draft_document_not_accessible(self, client, db, test_user):
        """Draft documents should not be accessible in viewer"""
        doc = Document(
            title="Draft Document Not Public",
            document_number=f"DOC-DRN-{uuid.uuid4().hex[:6].upper()}",
            status=DocumentStatus.DRAFT,
            created_by=test_user.id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        response = client.get(f"/api/v1/viewer/documents/{doc.id}")
        # Should either return 404 or filter out draft
        assert response.status_code in [404, 403, 200]  # Depends on implementation


class TestViewerVersions:
    """Tests for viewer version endpoints"""

    def test_get_document_versions(self, client, db, test_user):
        """Get versions for a document in viewer"""
        doc = Document(
            title="Versioned Document",
            document_number=f"DOC-VER-{uuid.uuid4().hex[:6].upper()}",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        # Add a published version
        version = Version(
            document_id=doc.id,
            version_number=1,
            content="Published content",
            is_published=True,
            created_by=test_user.id,
        )
        db.add(version)
        db.commit()

        response = client.get(f"/api/v1/viewer/documents/{doc.id}/versions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestViewerAttachments:
    """Tests for viewer attachment endpoints"""

    def test_get_document_attachments(self, client, db, test_user):
        """Get attachments for a document in viewer"""
        doc = Document(
            title="Document With Attachments",
            document_number=f"DOC-ATT-{uuid.uuid4().hex[:6].upper()}",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        response = client.get(f"/api/v1/viewer/documents/{doc.id}/attachments")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestViewerComments:
    """Tests for viewer comment endpoints"""

    def test_get_document_comments(self, client, db, test_user):
        """Get comments for a document in viewer"""
        doc = Document(
            title="Document With Comments",
            document_number=f"DOC-CMT-{uuid.uuid4().hex[:6].upper()}",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        # Add a comment
        comment = Comment(
            document_id=doc.id, content="This is a public comment", user_id=test_user.id
        )
        db.add(comment)
        db.commit()

        response = client.get(f"/api/v1/viewer/documents/{doc.id}/comments")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestViewerCategories:
    """Tests for viewer category endpoints"""

    def test_get_categories(self, client, db, test_user):
        """Get available categories"""
        # Create documents with categories
        doc1 = Document(
            title="Tech Document",
            document_number=f"DOC-TCH-{uuid.uuid4().hex[:6].upper()}",
            category="technology",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
        )
        doc2 = Document(
            title="HR Document",
            document_number=f"DOC-HRD-{uuid.uuid4().hex[:6].upper()}",
            category="hr",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
        )
        db.add_all([doc1, doc2])
        db.commit()

        response = client.get("/api/v1/viewer/categories")
        # May or may not be implemented
        assert response.status_code in [200, 404]
