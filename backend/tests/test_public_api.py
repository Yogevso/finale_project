"""Tests for the Public API endpoints (no authentication required)"""

from datetime import datetime

import pytest


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

    def test_list_public_documents_includes_visibility(self, client, public_document):
        """Public document list items should include visibility field for audience parity"""
        response = client.get("/api/v1/public/documents")
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert "visibility" in item
            assert item["visibility"] == "public"

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

    def test_get_public_document_includes_visibility(self, client, public_document):
        """Public document detail should include visibility field for audience parity"""
        response = client.get(f"/api/v1/public/documents/{public_document.id}")
        assert response.status_code == 200
        data = response.json()
        assert "visibility" in data
        assert data["visibility"] == "public"

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


class TestPublicTopicsEndpoint:
    """Test /api/v1/public/topics endpoints with topic normalization."""

    def test_list_public_topics_normalizes_legacy_topic_values(self, client, db, test_admin):
        from app.models import Document, DocumentStatus, DocumentVisibility, Topic

        db.add(Topic(name="SDKs & Tools", slug="sdk-tools", description="SDK and tooling docs"))
        db.flush()

        raw_topics = [
            "sdk-tools",
            "SDKs & Tools",
            "sdks-tools",
            " SDK-TOOLS ",
        ]
        for index, raw_topic in enumerate(raw_topics, start=1):
            db.add(
                Document(
                    title=f"Topic Legacy {index}",
                    document_number=f"DOC-TOPIC-{index:04d}",
                    status=DocumentStatus.ACTIVE,
                    visibility=DocumentVisibility.PUBLIC,
                    topic=raw_topic,
                    created_by=test_admin.id,
                    tenant_id=test_admin.tenant_id,
                )
            )
        db.commit()

        response = client.get("/api/v1/public/topics")
        assert response.status_code == 200
        payload = response.json()

        topic_row = next((item for item in payload["items"] if item["slug"] == "sdk-tools"), None)
        assert topic_row is not None
        assert topic_row["document_count"] == 4

    def test_get_public_topic_count_matches_normalized_topic_values(self, client, db, test_admin):
        from app.models import Document, DocumentStatus, DocumentVisibility, Topic

        db.add(Topic(name="Design Systems", slug="design-systems"))
        db.flush()

        db.add_all(
            [
                Document(
                    title="Design Canonical",
                    document_number="DOC-TOPIC-DES-0001",
                    status=DocumentStatus.ACTIVE,
                    visibility=DocumentVisibility.PUBLIC,
                    topic="design-systems",
                    created_by=test_admin.id,
                    tenant_id=test_admin.tenant_id,
                ),
                Document(
                    title="Design Name",
                    document_number="DOC-TOPIC-DES-0002",
                    status=DocumentStatus.ACTIVE,
                    visibility=DocumentVisibility.PUBLIC,
                    topic="Design Systems",
                    created_by=test_admin.id,
                    tenant_id=test_admin.tenant_id,
                ),
                Document(
                    title="Design Slugified Name",
                    document_number="DOC-TOPIC-DES-0003",
                    status=DocumentStatus.ACTIVE,
                    visibility=DocumentVisibility.PUBLIC,
                    topic="design-systems",
                    created_by=test_admin.id,
                    tenant_id=test_admin.tenant_id,
                ),
            ]
        )
        db.commit()

        response = client.get("/api/v1/public/topics/design-systems")
        assert response.status_code == 200
        payload = response.json()
        assert payload["slug"] == "design-systems"
        assert payload["document_count"] == 3

    def test_list_public_documents_topic_filter_accepts_topic_slug_aliases(
        self, client, db, test_admin
    ):
        from app.models import Document, DocumentStatus, DocumentVisibility, Topic

        db.add(Topic(name="SDKs & Tools", slug="sdk-tools"))
        db.flush()

        db.add_all(
            [
                Document(
                    title="Alias Match Slug",
                    document_number="DOC-TOPIC-FLT-0001",
                    status=DocumentStatus.ACTIVE,
                    visibility=DocumentVisibility.PUBLIC,
                    topic="sdk-tools",
                    created_by=test_admin.id,
                    tenant_id=test_admin.tenant_id,
                ),
                Document(
                    title="Alias Match Name",
                    document_number="DOC-TOPIC-FLT-0002",
                    status=DocumentStatus.ACTIVE,
                    visibility=DocumentVisibility.PUBLIC,
                    topic="SDKs & Tools",
                    created_by=test_admin.id,
                    tenant_id=test_admin.tenant_id,
                ),
                Document(
                    title="Alias Match Slugified Name",
                    document_number="DOC-TOPIC-FLT-0003",
                    status=DocumentStatus.ACTIVE,
                    visibility=DocumentVisibility.PUBLIC,
                    topic="sdks-tools",
                    created_by=test_admin.id,
                    tenant_id=test_admin.tenant_id,
                ),
                Document(
                    title="Other Topic",
                    document_number="DOC-TOPIC-FLT-0004",
                    status=DocumentStatus.ACTIVE,
                    visibility=DocumentVisibility.PUBLIC,
                    topic="platform",
                    created_by=test_admin.id,
                    tenant_id=test_admin.tenant_id,
                ),
            ]
        )
        db.commit()

        response = client.get("/api/v1/public/documents?topic=sdk-tools")
        assert response.status_code == 200
        payload = response.json()
        titles = {item["title"] for item in payload["items"]}

        assert payload["total"] == 3
        assert {
            "Alias Match Slug",
            "Alias Match Name",
            "Alias Match Slugified Name",
        }.issubset(titles)
        assert "Other Topic" not in titles


class TestPublicPlatformsEndpoints:
    """Test /api/v1/platforms endpoints"""

    def test_list_platform_overview(self, client, db, test_admin):
        """Should return platform summary rows with latest release metadata."""
        from app.models import (
            Document,
            DocumentStatus,
            DocumentVisibility,
            Platform,
            Version,
            VersionBumpType,
        )

        platform = Platform(name="Core Platform", slug="core-platform")
        db.add(platform)
        db.flush()

        doc = Document(
            title="Core Platform Guide",
            document_number="DOC-PLAT-001",
            description="Platform release doc",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.PUBLIC,
            category="Guides",
            platform=platform.name,
            platform_id=platform.id,
            created_by=test_admin.id,
            tenant_id=test_admin.tenant_id,
        )
        db.add(doc)
        db.flush()

        version = Version(
            document_id=doc.id,
            version_number=1,
            semantic_version="1.0.0",
            bump_type=VersionBumpType.MAJOR,
            content="test",
            changes_summary="initial",
            is_published=True,
            published_at=datetime.utcnow(),
            created_by=test_admin.id,
        )
        db.add(version)
        db.commit()

        response = client.get("/api/platforms")
        assert response.status_code == 200
        payload = response.json()
        assert "items" in payload
        assert len(payload["items"]) == 1
        assert payload["items"][0]["platform"] == "Core Platform"
        assert payload["items"][0]["doc_count"] == 1
        assert payload["items"][0]["latest_release"]["title"] == "Core Platform Guide"

    def test_get_platform_documents(self, client, db, test_admin):
        """Should return only documents linked to the requested platform ID."""
        from app.models import (
            Document,
            DocumentStatus,
            DocumentVisibility,
            Platform,
            Version,
            VersionBumpType,
        )

        platform_a = Platform(name="Developer Portal", slug="developer-portal")
        platform_b = Platform(name="Core Platform", slug="core-platform")
        db.add_all([platform_a, platform_b])
        db.flush()

        doc_a = Document(
            title="API Reference Index",
            document_number="DOC-PLAT-010",
            description="Platform A doc",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.PUBLIC,
            category="API",
            platform=platform_a.name,
            platform_id=platform_a.id,
            created_by=test_admin.id,
            tenant_id=test_admin.tenant_id,
        )
        doc_b = Document(
            title="Core Platform Guide",
            document_number="DOC-PLAT-020",
            description="Platform B doc",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.PUBLIC,
            category="Guide",
            platform=platform_b.name,
            platform_id=platform_b.id,
            created_by=test_admin.id,
            tenant_id=test_admin.tenant_id,
        )
        db.add_all([doc_a, doc_b])
        db.flush()

        db.add_all(
            [
                Version(
                    document_id=doc_a.id,
                    version_number=2,
                    semantic_version="2.0.0",
                    bump_type=VersionBumpType.MAJOR,
                    content="a",
                    changes_summary="major",
                    is_published=True,
                    published_at=datetime.utcnow(),
                    created_by=test_admin.id,
                ),
                Version(
                    document_id=doc_b.id,
                    version_number=1,
                    semantic_version="1.0.0",
                    bump_type=VersionBumpType.MAJOR,
                    content="b",
                    changes_summary="initial",
                    is_published=True,
                    published_at=datetime.utcnow(),
                    created_by=test_admin.id,
                ),
            ]
        )
        db.commit()

        response = client.get(f"/api/platforms/{platform_a.id}/documents")
        assert response.status_code == 200
        payload = response.json()
        assert payload["platform_id"] == platform_a.id
        assert payload["platform"] == "Developer Portal"
        assert payload["total"] == 1
        assert payload["items"][0]["title"] == "API Reference Index"
        assert payload["items"][0]["document_number"] == "DOC-PLAT-010"


class TestPublicRssFeed:
    """Test /api/v1/public/feed.xml endpoint"""

    def test_rss_feed_returns_xml(self, client, public_document):
        """RSS feed should return valid RSS 2.0 XML."""
        response = client.get("/api/v1/public/feed.xml")
        assert response.status_code == 200
        body = response.text
        assert '<?xml version="1.0"' in body
        assert "<rss" in body
        assert "<channel>" in body
        assert "<item>" in body
        assert "<title>" in body

    def test_rss_feed_excludes_internal_documents(self, client, public_document, internal_document):
        """RSS feed should not contain internal documents."""
        response = client.get("/api/v1/public/feed.xml")
        assert response.status_code == 200
        body = response.text
        assert "Public Document" in body
        assert "Internal Document" not in body

    def test_rss_feed_has_cache_headers(self, client, public_document):
        """RSS feed should set Cache-Control."""
        response = client.get("/api/v1/public/feed.xml")
        assert response.status_code == 200
        cc = response.headers.get("cache-control", "")
        assert "public" in cc

    def test_rss_feed_respects_limit(self, client, public_document):
        """RSS feed should respect the limit query parameter."""
        response = client.get("/api/v1/public/feed.xml?limit=1")
        assert response.status_code == 200
        body = response.text
        assert body.count("<item>") <= 1


class TestPublicSitemap:
    """Test /api/v1/public/sitemap.xml endpoint"""

    def test_sitemap_returns_xml(self, client, public_document):
        """Sitemap should return valid XML with public documents."""
        response = client.get("/api/v1/public/sitemap.xml")
        assert response.status_code == 200
        assert "application/xml" in response.headers.get("content-type", "")
        body = response.text
        assert '<?xml version="1.0"' in body
        assert "<urlset" in body
        assert "<url>" in body
        assert "<loc>" in body

    def test_sitemap_excludes_internal_documents(self, client, public_document, internal_document):
        """Sitemap should not contain internal documents."""
        response = client.get("/api/v1/public/sitemap.xml")
        assert response.status_code == 200
        body = response.text
        assert f"/doc/{internal_document.id}" not in body
        assert f"/doc/{public_document.id}" in body

    def test_sitemap_has_cache_headers(self, client, public_document):
        """Sitemap should set Cache-Control."""
        response = client.get("/api/v1/public/sitemap.xml")
        assert response.status_code == 200
        cc = response.headers.get("cache-control", "")
        assert "public" in cc

    def test_sitemap_escapes_base_url_xml_entities(self, client, public_document):
        """User-provided base_url must be XML-escaped inside <loc>."""
        response = client.get(
            "/api/v1/public/sitemap.xml",
            params={"base_url": "https://example.com/search?x=1&y=<tag>"},
        )

        assert response.status_code == 200
        body = response.text
        assert "https://example.com/search?x=1&amp;y=&lt;tag&gt;" in body
        assert "https://example.com/search?x=1&y=<tag>" not in body

    @pytest.mark.parametrize("path", ["/api/v1/public/feed.xml", "/api/v1/public/sitemap.xml"])
    def test_xml_endpoints_set_csp_headers(self, client, public_document, path):
        response = client.get(path)

        assert response.status_code == 200
        assert (
            response.headers.get("content-security-policy")
            == "default-src 'none'; frame-ancestors 'none'"
        )


class TestPublicCacheHeaders:
    """Test Cache-Control / ETag headers on public endpoints"""

    def test_list_documents_has_cache_control(self, client, public_document):
        """Public list should return Cache-Control header"""
        response = client.get("/api/v1/public/documents")
        assert response.status_code == 200
        cc = response.headers.get("cache-control", "")
        assert "public" in cc
        assert "max-age=" in cc

    def test_detail_document_has_cache_control_and_etag(self, client, public_document):
        """Public detail should return Cache-Control and ETag headers"""
        response = client.get(f"/api/v1/public/documents/{public_document.id}")
        assert response.status_code == 200
        cc = response.headers.get("cache-control", "")
        assert "public" in cc
        assert "max-age=" in cc
        # ETag should be present and non-empty
        etag = response.headers.get("etag")
        assert etag is not None and len(etag) > 0


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
