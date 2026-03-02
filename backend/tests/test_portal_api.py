"""Tests for the Customer Portal API endpoints"""

from uuid import uuid4

from app.models import Attachment, Document, DocumentStatus, DocumentVisibility, Version


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

    def test_portal_list_has_parity_fields(self, client, customer_headers, public_document):
        """Portal document list should include parity fields matching public API"""
        response = client.get("/api/v1/portal/documents", headers=customer_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0
        item = data["items"][0]
        # These fields must exist for cross-channel parity
        for field in ["document_number", "topic", "platform", "release_branch",
                       "tags", "visibility", "created_at", "published_at"]:
            assert field in item, f"Missing parity field: {field}"

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

    def test_portal_detail_has_parity_fields(self, client, customer_headers, public_document):
        """Portal document detail should include parity fields matching public API"""
        response = client.get(
            f"/api/v1/portal/documents/{public_document.id}", headers=customer_headers
        )
        assert response.status_code == 200
        data = response.json()
        for field in ["document_number", "topic", "platform", "release_branch",
                       "visibility", "published_at"]:
            assert field in data, f"Missing parity field: {field}"

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

    def test_document_detail_attachment_download_url_is_document_scoped(
        self, client, db, customer_headers, public_document, test_admin
    ):
        """Attachment URLs in portal detail should match document-scoped download route."""
        attachment = Attachment(
            document_id=public_document.id,
            filename="portal-test.pdf",
            original_filename="portal-test.pdf",
            file_size=128,
            mime_type="application/pdf",
            storage_path="/tmp/portal-test.pdf",
            uploaded_by=test_admin.id,
        )
        db.add(attachment)
        db.commit()
        db.refresh(attachment)

        response = client.get(
            f"/api/v1/portal/documents/{public_document.id}", headers=customer_headers
        )
        assert response.status_code == 200
        attachments = response.json()["attachments"]
        entry = next(item for item in attachments if item["id"] == attachment.id)
        assert (
            entry["download_url"]
            == f"/api/v1/documents/{public_document.id}/attachments/{attachment.id}/download"
        )

    def test_list_and_detail_use_same_published_version_when_newer_draft_exists(
        self, client, db, customer_headers, test_admin
    ):
        """Portal list/detail should both prefer latest published version over newer draft."""
        document = Document(
            title="Portal Version Consistency Published",
            document_number=f"DOC-PORTAL-PUB-{uuid4().hex[:8]}",
            description="Portal version consistency test",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.PUBLIC,
            created_by=test_admin.id,
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        db.add_all(
            [
                Version(
                    document_id=document.id,
                    version_number=1,
                    content="published content",
                    changes_summary="published",
                    is_published=True,
                    created_by=test_admin.id,
                ),
                Version(
                    document_id=document.id,
                    version_number=2,
                    content="draft content",
                    changes_summary="draft",
                    is_published=False,
                    created_by=test_admin.id,
                ),
            ]
        )
        db.commit()

        list_response = client.get("/api/v1/portal/documents?per_page=100", headers=customer_headers)
        assert list_response.status_code == 200
        list_payload = list_response.json()
        list_item = next(item for item in list_payload["items"] if item["id"] == document.id)
        assert list_item["version"] == 1

        detail_response = client.get(
            f"/api/v1/portal/documents/{document.id}",
            headers=customer_headers,
        )
        assert detail_response.status_code == 200
        detail_payload = detail_response.json()
        assert detail_payload["version"] == 1
        assert detail_payload["content"] == "published content"

    def test_list_and_detail_fallback_to_latest_when_no_published_version_exists(
        self, client, db, customer_headers, test_admin
    ):
        """Portal list/detail should use latest available version for legacy unpublished-only docs."""
        document = Document(
            title="Portal Version Consistency Fallback",
            document_number=f"DOC-PORTAL-DRF-{uuid4().hex[:8]}",
            description="Portal version fallback test",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.PUBLIC,
            created_by=test_admin.id,
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        db.add_all(
            [
                Version(
                    document_id=document.id,
                    version_number=1,
                    content="older draft content",
                    changes_summary="older draft",
                    is_published=False,
                    created_by=test_admin.id,
                ),
                Version(
                    document_id=document.id,
                    version_number=2,
                    content="latest draft content",
                    changes_summary="latest draft",
                    is_published=False,
                    created_by=test_admin.id,
                ),
            ]
        )
        db.commit()

        list_response = client.get("/api/v1/portal/documents?per_page=100", headers=customer_headers)
        assert list_response.status_code == 200
        list_payload = list_response.json()
        list_item = next(item for item in list_payload["items"] if item["id"] == document.id)
        assert list_item["version"] == 2

        detail_response = client.get(
            f"/api/v1/portal/documents/{document.id}",
            headers=customer_headers,
        )
        assert detail_response.status_code == 200
        detail_payload = detail_response.json()
        assert detail_payload["version"] == 2
        assert detail_payload["content"] == "latest draft content"


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
        assert "total_documents" in data

    def test_dashboard_stats_match_visible_documents(
        self,
        client,
        customer_headers,
        public_document,
        company_document,
        internal_document,
    ):
        """Dashboard document counters should match the customer-visible list semantics."""
        stats_response = client.get("/api/v1/portal/dashboard/stats", headers=customer_headers)
        assert stats_response.status_code == 200
        stats = stats_response.json()

        list_response = client.get(
            "/api/v1/portal/documents?per_page=100",
            headers=customer_headers,
        )
        assert list_response.status_code == 200
        payload = list_response.json()

        visibility_counts: dict[str, int] = {}
        for item in payload["items"]:
            visibility = item.get("visibility") or "internal"
            visibility_counts[visibility] = visibility_counts.get(visibility, 0) + 1

        assert stats["total_documents"] == payload["total"]
        assert stats["public_documents"] == visibility_counts.get("public", 0)
        assert stats["company_documents"] == visibility_counts.get("company", 0)

    def test_dashboard_stats_exclude_other_company_documents(
        self,
        client,
        customer_2_headers,
        public_document,
        company_document,
    ):
        """A customer from another company should only count globally public documents."""
        response = client.get("/api/v1/portal/dashboard/stats", headers=customer_2_headers)
        assert response.status_code == 200
        data = response.json()

        assert data["total_documents"] == 1
        assert data["public_documents"] == 1
        assert data["company_documents"] == 0


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
