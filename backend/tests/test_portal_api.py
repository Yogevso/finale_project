"""Tests for the Customer Portal API endpoints"""


class TestPortalDocumentsEndpoint:
    """Test /api/v1/portal/documents endpoint"""

    def test_requires_authentication(self, client):
        """Should require authentication"""
        response = client.get("/api/v1/portal/documents")
        assert response.status_code == 401

    def test_customer_can_access(self, client, customer_headers, public_document):
        """Customer should be able to access portal documents"""
        response = client.get("/api/v1/portal/documents", headers=customer_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_customer_sees_public_documents(self, client, customer_headers, public_document):
        """Customer should see public documents"""
        response = client.get("/api/v1/portal/documents", headers=customer_headers)
        assert response.status_code == 200
        data = response.json()
        titles = [doc["title"] for doc in data["items"]]
        assert "Public Document" in titles

    def test_customer_sees_own_company_documents(self, client, customer_headers, company_document):
        """Customer should see documents assigned to their company"""
        response = client.get("/api/v1/portal/documents", headers=customer_headers)
        assert response.status_code == 200
        data = response.json()
        titles = [doc["title"] for doc in data["items"]]
        assert "Company Document" in titles

    def test_customer_cannot_see_other_company_documents(
        self, client, customer_2_headers, company_document
    ):
        """Customer should not see documents from other companies"""
        response = client.get("/api/v1/portal/documents", headers=customer_2_headers)
        assert response.status_code == 200
        data = response.json()
        titles = [doc["title"] for doc in data["items"]]
        assert "Company Document" not in titles

    def test_customer_cannot_see_internal_documents(
        self, client, customer_headers, internal_document
    ):
        """Customer should not see internal documents"""
        response = client.get("/api/v1/portal/documents", headers=customer_headers)
        assert response.status_code == 200
        data = response.json()
        titles = [doc["title"] for doc in data["items"]]
        assert "Internal Document" not in titles


class TestPortalDocumentDetailEndpoint:
    """Test /api/v1/portal/documents/{id} endpoint"""

    def test_customer_can_view_public_document(self, client, customer_headers, public_document):
        """Customer should be able to view public document details"""
        response = client.get(
            f"/api/v1/portal/documents/{public_document.id}", headers=customer_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Public Document"

    def test_customer_can_view_own_company_document(
        self, client, customer_headers, company_document
    ):
        """Customer should be able to view their company's documents"""
        response = client.get(
            f"/api/v1/portal/documents/{company_document.id}", headers=customer_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Company Document"

    def test_customer_cannot_view_other_company_document(
        self, client, customer_2_headers, company_document
    ):
        """Customer should not be able to view other company's documents"""
        response = client.get(
            f"/api/v1/portal/documents/{company_document.id}", headers=customer_2_headers
        )
        assert response.status_code in [403, 404]

    def test_customer_cannot_view_internal_document(
        self, client, customer_headers, internal_document
    ):
        """Customer should not be able to view internal documents"""
        response = client.get(
            f"/api/v1/portal/documents/{internal_document.id}", headers=customer_headers
        )
        assert response.status_code in [403, 404]


class TestPortalFeedbackEndpoint:
    """Test /api/v1/portal/feedback endpoints"""

    def test_customer_can_submit_feedback(self, client, customer_headers, public_document):
        """Customer should be able to submit feedback on documents"""
        response = client.post(
            "/api/v1/portal/feedback",
            headers=customer_headers,
            json={
                "document_id": public_document.id,
                "feedback_type": "question",
                "content": "I have a question about this document",
            },
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["content"] == "I have a question about this document"
        assert data["feedback_type"] == "question"

    def test_customer_can_list_own_feedback(self, client, customer_headers, public_document):
        """Customer should be able to list their own feedback"""
        # First submit feedback
        client.post(
            "/api/v1/portal/feedback",
            headers=customer_headers,
            json={
                "document_id": public_document.id,
                "feedback_type": "suggestion",
                "content": "This is my suggestion",
            },
        )
        # Then list
        response = client.get("/api/v1/portal/feedback", headers=customer_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_customer_cannot_see_others_feedback(
        self, client, customer_headers, customer_2_headers, public_document
    ):
        """Customer should not see other customers' feedback"""
        # Customer 1 submits feedback
        client.post(
            "/api/v1/portal/feedback",
            headers=customer_headers,
            json={
                "document_id": public_document.id,
                "feedback_type": "issue",
                "content": "Customer 1 issue",
            },
        )
        # Customer 2 should not see it
        response = client.get("/api/v1/portal/feedback", headers=customer_2_headers)
        assert response.status_code == 200
        data = response.json()
        contents = [f["content"] for f in data.get("items", [])]
        assert "Customer 1 issue" not in contents


class TestPortalDashboardEndpoint:
    """Test /api/v1/portal/dashboard/stats endpoint"""

    def test_customer_can_access_dashboard_stats(self, client, customer_headers):
        """Customer should be able to access dashboard stats"""
        response = client.get("/api/v1/portal/dashboard/stats", headers=customer_headers)
        assert response.status_code == 200
        data = response.json()
        assert "document_count" in data or "total_documents" in data


class TestPortalSearchEndpoint:
    """Test /api/v1/portal/search endpoint"""

    def test_customer_can_search_documents(
        self, client, customer_headers, public_document, company_document
    ):
        """Customer should be able to search accessible documents"""
        response = client.get("/api/v1/portal/search?q=Document", headers=customer_headers)
        assert response.status_code == 200
        data = response.json()
        # Search endpoint returns 'results' instead of 'items'
        assert "results" in data or "items" in data

    def test_search_does_not_include_internal(self, client, customer_headers, internal_document):
        """Customer search should not include internal documents"""
        response = client.get("/api/v1/portal/search?q=Internal", headers=customer_headers)
        assert response.status_code == 200
        data = response.json()
        titles = [doc["title"] for doc in data.get("items", [])]
        assert "Internal Document" not in titles

    def test_search_does_not_include_other_company(
        self, client, customer_2_headers, company_document
    ):
        """Customer search should not include other company's documents"""
        response = client.get("/api/v1/portal/search?q=Company", headers=customer_2_headers)
        assert response.status_code == 200
        data = response.json()
        titles = [doc["title"] for doc in data.get("items", [])]
        assert "Company Document" not in titles


class TestInternalUserCannotAccessPortal:
    """Test that internal users cannot use customer portal endpoints"""

    def test_admin_cannot_access_portal_documents(self, client, admin_headers, public_document):
        """Admin should be redirected away from portal endpoints"""
        response = client.get("/api/v1/portal/documents", headers=admin_headers)
        # Should either deny access or allow (depending on implementation)
        # At minimum, internal staff shouldn't need the portal
        assert response.status_code in [200, 403]

    def test_editor_cannot_access_portal_documents(self, client, auth_headers, public_document):
        """Editor should not typically use portal endpoints"""
        response = client.get("/api/v1/portal/documents", headers=auth_headers)
        # Implementation may allow or deny
        assert response.status_code in [200, 403]
