"""Tests for Viewer Portal (Public Document Access)"""
import pytest
import uuid
from app.models import Document, DocumentStatus, Version, Attachment, Comment


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
            created_by=test_user.id
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
            created_by=test_user.id
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
            created_by=test_user.id
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
            created_by=test_user.id
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
                created_by=test_user.id
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
            created_by=test_user.id
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
            created_by=test_user.id
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


class TestViewerVersions:
    """Tests for viewer version endpoints"""
    
    def test_list_document_versions(self, client, db, test_user):
        """List versions for a published document"""
        doc = Document(
            title="Version Test Doc",
            document_number=f"DOC-VER-{uuid.uuid4().hex[:6].upper()}",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id
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
            created_by=test_user.id
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
            created_by=test_user.id
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
            created_by=test_user.id
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
            created_by=test_user.id
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        # Add comment
        comment = Comment(
            document_id=doc.id,
            content="This is a test comment",
            user_id=test_user.id
        )
        db.add(comment)
        db.commit()
        
        response = client.get(f"/api/v1/viewer/documents/{doc.id}/comments")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestViewerAttachments:
    """Tests for viewer attachment endpoints"""
    
    def test_list_document_attachments(self, client, db, test_user):
        """List attachments for a document"""
        doc = Document(
            title="Attachment Test Doc",
            document_number=f"DOC-ATT-{uuid.uuid4().hex[:6].upper()}",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id
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
            uploaded_by=test_user.id
        )
        db.add(attachment)
        db.commit()
        
        response = client.get(f"/api/v1/viewer/documents/{doc.id}/attachments")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
