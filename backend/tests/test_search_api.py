"""Tests for Search API"""

import uuid
from datetime import datetime, timedelta

from sqlalchemy.exc import OperationalError

from app.application.queries.search_queries import SearchQueryHandler
from app.config import settings
from app.models import Document, DocumentStatus, SearchAnalytics, Tenant


class TestSearch:
    """Tests for search endpoints"""

    def test_search_documents(self, client, auth_headers, db, test_user):
        """Test basic document search"""
        # Create documents with searchable content
        doc1 = Document(
            title="Python Programming Guide",
            document_number=f"DOC-PY-{uuid.uuid4().hex[:6].upper()}",
            description="A comprehensive guide to Python programming",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
            tenant_id=test_user.tenant_id,
        )
        doc2 = Document(
            title="Java Development Manual",
            document_number=f"DOC-JV-{uuid.uuid4().hex[:6].upper()}",
            description="Java development best practices",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
            tenant_id=test_user.tenant_id,
        )
        db.add_all([doc1, doc2])
        db.commit()

        # Search for Python
        response = client.get("/api/v1/search/?q=Python", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "query" in data
        assert data["query"] == "Python"

    def test_search_with_category_filter(self, client, auth_headers, db, test_user):
        """Test search with category filter"""
        doc = Document(
            title="Security Policy Document",
            document_number=f"DOC-SEC-{uuid.uuid4().hex[:6].upper()}",
            description="Company security policies",
            category="security",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
            tenant_id=test_user.tenant_id,
        )
        other_doc = Document(
            title="Engineering Policy Document",
            document_number=f"DOC-ENG-{uuid.uuid4().hex[:6].upper()}",
            description="Engineering policy notes",
            category="engineering",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
            tenant_id=test_user.tenant_id,
        )
        db.add_all([doc, other_doc])
        db.commit()

        response = client.get("/api/v1/search/?q=policy&category=security", headers=auth_headers)
        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) >= 1
        assert all(item["category"] == "security" for item in items)

    def test_search_with_date_filter(self, client, auth_headers, db, test_user):
        """Date filters should apply in both FTS and fallback search paths."""
        old_doc = Document(
            title="Date Filter Old Doc",
            document_number=f"DOC-OLD-{uuid.uuid4().hex[:6].upper()}",
            description="release-notes filter target",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
            tenant_id=test_user.tenant_id,
            created_at=datetime.utcnow() - timedelta(days=10),
        )
        recent_doc = Document(
            title="Date Filter Recent Doc",
            document_number=f"DOC-NEW-{uuid.uuid4().hex[:6].upper()}",
            description="release-notes filter target",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
            tenant_id=test_user.tenant_id,
            created_at=datetime.utcnow(),
        )
        db.add_all([old_doc, recent_doc])
        db.commit()

        date_from = (datetime.utcnow() - timedelta(days=1)).isoformat()
        response = client.get(
            f"/api/v1/search/?q=release-notes&date_from={date_from}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        titles = [item["title"] for item in response.json()["items"]]
        assert "Date Filter Recent Doc" in titles
        assert "Date Filter Old Doc" not in titles

    def test_search_is_tenant_scoped_for_non_system_admin(
        self, client, auth_headers, db, test_user
    ):
        """Non-system-admin search should not return cross-tenant documents."""
        tenant_one = Tenant(
            name="Tenant One",
            slug=f"tenant-one-{uuid.uuid4().hex[:6]}",
            is_active=True,
            company_type="customer",
        )
        tenant_two = Tenant(
            name="Tenant Two",
            slug=f"tenant-two-{uuid.uuid4().hex[:6]}",
            is_active=True,
            company_type="customer",
        )
        db.add_all([tenant_one, tenant_two])
        db.commit()
        db.refresh(tenant_one)
        db.refresh(tenant_two)

        test_user.tenant_id = tenant_one.id
        db.commit()

        visible_doc = Document(
            title="Scoped Search Visible",
            document_number=f"DOC-SVIS-{uuid.uuid4().hex[:6].upper()}",
            description="tenant-scope-keyword",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
            tenant_id=tenant_one.id,
        )
        hidden_doc = Document(
            title="Scoped Search Hidden",
            document_number=f"DOC-SHID-{uuid.uuid4().hex[:6].upper()}",
            description="tenant-scope-keyword",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
            tenant_id=tenant_two.id,
        )
        db.add_all([visible_doc, hidden_doc])
        db.commit()

        response = client.get("/api/v1/search/?q=tenant-scope-keyword", headers=auth_headers)
        assert response.status_code == 200
        titles = [item["title"] for item in response.json()["items"]]
        assert "Scoped Search Visible" in titles
        assert "Scoped Search Hidden" not in titles

    def test_search_pagination(self, client, auth_headers, db, test_user):
        """Test search with pagination"""
        # Create multiple documents
        for i in range(5):
            doc = Document(
                title=f"Test Document {i}",
                document_number=f"DOC-TST{i}-{uuid.uuid4().hex[:4].upper()}",
                description="Searchable test content",
                status=DocumentStatus.ACTIVE,
                created_by=test_user.id,
                tenant_id=test_user.tenant_id,
            )
            db.add(doc)
        db.commit()

        # Get first page with small page size
        response = client.get("/api/v1/search/?q=test&page=1&page_size=2", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2

    def test_search_empty_query_rejected(self, client, auth_headers):
        """Empty search query should be rejected"""
        response = client.get("/api/v1/search/?q=", headers=auth_headers)
        # Empty query should fail validation
        assert response.status_code == 422

    def test_search_no_results(self, client, auth_headers):
        """Search with no matching results"""
        response = client.get("/api/v1/search/?q=xyznonexistent123", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0

    def test_search_ignores_advanced_fts_operator_syntax(self, client, auth_headers, db, test_user):
        matching_doc = Document(
            title="Operator Safe Guide",
            document_number=f"DOC-OPS-{uuid.uuid4().hex[:6].upper()}",
            description="operator safe search coverage",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
            tenant_id=test_user.tenant_id,
        )
        unrelated_doc = Document(
            title="Totally Unrelated",
            document_number=f"DOC-OPS-{uuid.uuid4().hex[:6].upper()}",
            description="nothing to do with the query",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
            tenant_id=test_user.tenant_id,
        )
        db.add_all([matching_doc, unrelated_doc])
        db.commit()

        response = client.get(
            "/api/v1/search/?q=operator-safe OR *",
            headers=auth_headers,
        )
        assert response.status_code == 200
        titles = [item["title"] for item in response.json()["items"]]
        assert "Operator Safe Guide" in titles
        assert "Totally Unrelated" not in titles

    def test_search_fallback_is_visible_in_health_metrics(
        self,
        client,
        auth_headers,
        db,
        test_user,
        monkeypatch,
    ):
        doc = Document(
            title="Fallback Search Visible",
            document_number=f"DOC-FBK-{uuid.uuid4().hex[:6].upper()}",
            description="fallback-search-health",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
            tenant_id=test_user.tenant_id,
        )
        db.add(doc)
        db.commit()

        monkeypatch.setattr(settings, "SEARCH_BACKEND_MODE", "sqlite_fts5")

        def fail_fts(*_args, **_kwargs):
            raise OperationalError("SELECT", {}, RuntimeError("fts unavailable"))

        monkeypatch.setattr(SearchQueryHandler, "_execute_sqlite_fts_search", fail_fts)

        response = client.get("/api/v1/search/?q=fallback-search-health", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["total"] >= 1

        health_response = client.get("/health/detailed")
        assert health_response.status_code == 200
        search_runtime = health_response.json()["runtime"]["search"]
        assert search_runtime["configured_mode"] == "sqlite_fts5"
        assert search_runtime["effective_mode"] == "sqlite_fts5"
        assert search_runtime["degraded_fallbacks"] == 1
        assert search_runtime["last_requested_mode"] == "sqlite_fts5"
        assert search_runtime["last_fallback_mode"] == "portable_like"
        assert search_runtime["last_error_type"] == "OperationalError"

        degradation = health_response.json()["runtime"]["degradation"]
        assert degradation["by_key"]["compensating:search.documents"] == 1


class TestSavedSearches:
    """Tests for saved search functionality"""

    def test_create_saved_search(self, client, auth_headers):
        """Create a saved search"""
        response = client.post(
            "/api/v1/search/saved",
            headers=auth_headers,
            json={"name": "My Python Search", "query": "Python"},
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == "My Python Search"
        assert data["query"] == "Python"

    def test_list_saved_searches(self, client, auth_headers):
        """List user's saved searches"""
        # Create a saved search first
        client.post(
            "/api/v1/search/saved",
            headers=auth_headers,
            json={"name": "Test Search", "query": "test"},
        )

        # List saved searches
        response = client.get("/api/v1/search/saved", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_delete_saved_search(self, client, auth_headers):
        """Delete a saved search"""
        # Create saved search
        create_resp = client.post(
            "/api/v1/search/saved",
            headers=auth_headers,
            json={"name": "To Delete", "query": "delete"},
        )
        search_id = create_resp.json()["id"]

        # Delete it
        response = client.delete(f"/api/v1/search/saved/{search_id}", headers=auth_headers)
        assert response.status_code in [200, 204]

    def test_execute_saved_search(self, client, auth_headers, db, test_user):
        """Test using a saved search's query"""
        # Create document
        doc = Document(
            title="Saved Search Test Doc",
            document_number=f"DOC-SST-{uuid.uuid4().hex[:6].upper()}",
            description="Document for saved search testing",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
            tenant_id=test_user.tenant_id,
        )
        db.add(doc)
        db.commit()

        # Create saved search
        create_resp = client.post(
            "/api/v1/search/saved",
            headers=auth_headers,
            json={"name": "Run Test", "query": "saved"},
        )
        data = create_resp.json()

        # Execute the saved query directly
        response = client.get(f"/api/v1/search/?q={data['query']}", headers=auth_headers)
        assert response.status_code == 200


class TestSearchSuggestions:
    """Tests for search suggestions"""

    def test_get_suggestions(self, client, auth_headers, db, test_user):
        """Get search suggestions"""
        # Create documents to generate suggestions
        doc = Document(
            title="Suggestion Test Document",
            document_number=f"DOC-SUG-{uuid.uuid4().hex[:6].upper()}",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
            tenant_id=test_user.tenant_id,
        )
        db.add(doc)
        db.commit()

        response = client.get("/api/v1/search/suggestions?q=sug", headers=auth_headers)
        # May return 200 or 404 if not implemented
        assert response.status_code in [200, 404]


class TestSearchAnalytics:
    def test_search_analytics_redacts_cross_tenant_queries_for_system_admin(
        self,
        client,
        db,
        system_admin_headers,
        test_user,
        test_customer_2,
    ):
        db.add_all(
            [
                SearchAnalytics(
                    query="tenant-one-secret",
                    user_id=test_user.id,
                    tenant_id=test_user.tenant_id,
                    results_count=1,
                ),
                SearchAnalytics(
                    query="tenant-two-secret",
                    user_id=test_customer_2.id,
                    tenant_id=test_customer_2.tenant_id,
                    results_count=0,
                ),
            ]
        )
        db.commit()

        response = client.get("/api/v1/search/analytics", headers=system_admin_headers)
        assert response.status_code == 200
        payload = response.json()
        top_queries = [item["query"] for item in payload["top_queries"]]
        zero_queries = [item["query"] for item in payload["zero_result_queries"]]

        assert "tenant-one-secret" not in top_queries
        assert "tenant-two-secret" not in top_queries
        assert "tenant-two-secret" not in zero_queries
        assert all(query.startswith("[redacted-query:") for query in top_queries)

    def test_search_analytics_keeps_raw_queries_within_tenant_scope(
        self,
        client,
        db,
        admin_headers,
        test_admin,
        test_customer_2,
    ):
        db.add_all(
            [
                SearchAnalytics(
                    query="tenant-admin-visible",
                    user_id=test_admin.id,
                    tenant_id=test_admin.tenant_id,
                    results_count=2,
                ),
                SearchAnalytics(
                    query="other-tenant-hidden",
                    user_id=test_customer_2.id,
                    tenant_id=test_customer_2.tenant_id,
                    results_count=0,
                ),
            ]
        )
        db.commit()

        response = client.get("/api/v1/search/analytics", headers=admin_headers)
        assert response.status_code == 200
        payload = response.json()
        top_queries = [item["query"] for item in payload["top_queries"]]

        assert "tenant-admin-visible" in top_queries
        assert "other-tenant-hidden" not in top_queries
