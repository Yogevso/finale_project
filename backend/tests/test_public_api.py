"""Tests for the Public API endpoints (no authentication required)"""


class TestPublicDocumentsEndpoint:
    """Test /api/v1/public/documents endpoint"""

    def test_list_public_documents_no_auth(self, client, public_document):
        """Should return public documents without authentication"""
        response = client.get("/api/v1/public/documents")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        # Should find our public document
        titles = [doc["title"] for doc in data["items"]]
        assert "Public Document" in titles

    def test_list_public_documents_excludes_internal(
        self, client, public_document, internal_document
    ):
        """Should not include internal documents in public listing"""
        response = client.get("/api/v1/public/documents")
        assert response.status_code == 200
        data = response.json()
        titles = [doc["title"] for doc in data["items"]]
        assert "Internal Document" not in titles

    def test_list_public_documents_excludes_company(
        self, client, public_document, company_document
    ):
        """Should not include company-specific documents in public listing"""
        response = client.get("/api/v1/public/documents")
        assert response.status_code == 200
        data = response.json()
        titles = [doc["title"] for doc in data["items"]]
        assert "Company Document" not in titles

    def test_list_public_documents_excludes_drafts(self, client, test_document):
        """Should not include draft documents in public listing"""
        response = client.get("/api/v1/public/documents")
        assert response.status_code == 200
        data = response.json()
        titles = [doc["title"] for doc in data["items"]]
        assert "Test Document" not in titles

    def test_list_public_documents_with_pagination(self, client, public_document):
        """Should support pagination parameters"""
        response = client.get("/api/v1/public/documents?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert "page_size" in data
        assert "total_pages" in data
        assert data["page"] == 1
        assert data["page_size"] == 10


class TestPublicDocumentDetailEndpoint:
    """Test /api/v1/public/documents/{id} endpoint"""

    def test_get_public_document_detail(self, client, public_document):
        """Should return public document details without auth"""
        response = client.get(f"/api/v1/public/documents/{public_document.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Public Document"
        assert data["id"] == public_document.id

    def test_get_internal_document_fails(self, client, internal_document):
        """Should not return internal documents on public endpoint"""
        response = client.get(f"/api/v1/public/documents/{internal_document.id}")
        assert response.status_code == 404

    def test_get_company_document_fails(self, client, company_document):
        """Should not return company documents on public endpoint"""
        response = client.get(f"/api/v1/public/documents/{company_document.id}")
        assert response.status_code == 404

    def test_get_draft_document_fails(self, client, test_document):
        """Should not return draft documents on public endpoint"""
        response = client.get(f"/api/v1/public/documents/{test_document.id}")
        assert response.status_code == 404

    def test_get_nonexistent_document_fails(self, client):
        """Should return 404 for nonexistent document"""
        response = client.get("/api/v1/public/documents/99999")
        assert response.status_code == 404


class TestPublicSearchEndpoint:
    """Test /api/v1/public/search endpoint"""

    def test_search_public_documents(self, client, public_document):
        """Should search within public documents"""
        response = client.get("/api/v1/public/search?q=Public")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_search_does_not_find_internal(self, client, internal_document):
        """Should not find internal documents in public search"""
        response = client.get("/api/v1/public/search?q=Internal")
        assert response.status_code == 200
        data = response.json()
        titles = [doc["title"] for doc in data.get("items", [])]
        assert "Internal Document" not in titles

    def test_search_empty_query(self, client):
        """Should handle empty search query"""
        response = client.get("/api/v1/public/search?q=")
        # Should either return empty results or all public docs
        assert response.status_code in [200, 422]


class TestPublicCategoriesEndpoint:
    """Test /api/v1/public/categories endpoint"""

    def test_get_public_categories(self, client, public_document):
        """Should return categories with public document counts"""
        response = client.get("/api/v1/public/categories")
        assert response.status_code == 200
        data = response.json()
        # API returns {items: [...], total: X}
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)


class TestPublicStatsEndpoint:
    """Test /api/v1/public/stats endpoint"""

    def test_get_public_stats(self, client, public_document):
        """Should return public statistics"""
        response = client.get("/api/v1/public/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_documents" in data


class TestPublicEndpointsSecure:
    """Test that public endpoints don't leak sensitive data"""

    def test_public_document_no_internal_fields(self, client, public_document):
        """Public document response should not contain internal-only fields"""
        response = client.get(f"/api/v1/public/documents/{public_document.id}")
        assert response.status_code == 200
        data = response.json()
        # Should not expose certain internal fields
        assert "created_by" not in data or data.get("created_by") is None
        # Author name might be exposed, but not internal IDs

    def test_public_list_no_internal_fields(self, client, public_document):
        """Public document list should not contain internal-only fields"""
        response = client.get("/api/v1/public/documents")
        assert response.status_code == 200
        data = response.json()
        if data["items"]:
            doc = data["items"][0]
            # Check that sensitive fields are not exposed
            assert "assigned_companies" not in doc or doc.get("assigned_companies") == []
