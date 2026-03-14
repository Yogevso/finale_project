"""Wave Y.2 integration tests — Y2-021, Y2-022, Y2-023."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from app.models import (
    BrokenLinkReport,
    Document,
    DocumentStatus,
    DocumentVisibility,
    Version,
)
from tests.factories import create_document, create_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _login_headers(client, username: str, password: str = "testpass123") -> dict:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _ensure_fts_table(db):
    """Create the FTS5 virtual table if it doesn't exist yet in the test DB."""
    existing = db.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='documents_fts'")
    ).fetchone()
    if not existing:
        db.execute(text(
            "CREATE VIRTUAL TABLE documents_fts USING fts5(title, description, category, tags)"
        ))
        db.commit()


def _sync_fts(db, doc: Document):
    """Insert/replace a document row into the FTS5 index."""
    _ensure_fts_table(db)
    db.execute(text("DELETE FROM documents_fts WHERE rowid = :rid"), {"rid": doc.id})
    db.execute(
        text(
            "INSERT INTO documents_fts(rowid, title, description, category, tags) "
            "VALUES (:rid, :title, :desc, :cat, :tags)"
        ),
        {
            "rid": doc.id,
            "title": doc.title or "",
            "desc": doc.description or "",
            "cat": doc.category or "",
            "tags": doc.tags or "",
        },
    )
    db.commit()


# ---------------------------------------------------------------------------
# Y2-021: Search ranking integration test
# ---------------------------------------------------------------------------

class TestSearchRanking:
    """Create documents with specific titles/tags, search, verify result order."""

    def test_title_match_ranks_higher_than_tag_match(self, client, db, test_user):
        headers = _login_headers(client, test_user.username)

        # Doc A: "Kubernetes" in title (weight=3.0)
        doc_a = create_document(
            db,
            created_by=test_user.id,
            title="Kubernetes Deployment Guide",
            description="How to deploy apps",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.INTERNAL,
            category="DevOps",
            tags="containers,docker",
        )

        # Doc B: "Kubernetes" only in tags (weight=2.0)
        doc_b = create_document(
            db,
            created_by=test_user.id,
            title="Docker Containers Overview",
            description="Container basics",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.INTERNAL,
            category="DevOps",
            tags="kubernetes,orchestration",
        )

        _sync_fts(db, doc_a)
        _sync_fts(db, doc_b)

        resp = client.get("/api/v1/search/", params={"q": "Kubernetes"}, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2

        ids = [item["id"] for item in data["items"]]
        assert ids.index(doc_a.id) < ids.index(doc_b.id), (
            "Document with title match should rank above tag-only match"
        )

    def test_search_returns_only_matching_documents(self, client, db, test_user):
        headers = _login_headers(client, test_user.username)

        doc_match = create_document(
            db,
            created_by=test_user.id,
            title="GraphQL API Reference",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.INTERNAL,
        )
        doc_no_match = create_document(
            db,
            created_by=test_user.id,
            title="REST Endpoints List",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.INTERNAL,
        )
        _sync_fts(db, doc_match)
        _sync_fts(db, doc_no_match)

        resp = client.get("/api/v1/search/", params={"q": "GraphQL"}, headers=headers)
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()["items"]]
        assert doc_match.id in ids
        assert doc_no_match.id not in ids


# ---------------------------------------------------------------------------
# Y2-022: Sitemap generation integration test
# ---------------------------------------------------------------------------

class TestSitemapGeneration:
    """Publish a document, request /sitemap.xml, verify URL present; unpublish, verify removed."""

    def test_published_public_doc_appears_in_sitemap(self, client, db, test_user):
        doc = create_document(
            db,
            created_by=test_user.id,
            title="Public Sitemap Doc",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.PUBLIC,
        )

        resp = client.get("/api/v1/public/sitemap.xml")
        assert resp.status_code == 200
        assert "application/xml" in resp.headers.get("content-type", "")
        body = resp.text
        assert f"<loc>/doc/{doc.id}</loc>" in body

    def test_draft_doc_not_in_sitemap(self, client, db, test_user):
        doc = create_document(
            db,
            created_by=test_user.id,
            title="Draft Sitemap Doc",
            status=DocumentStatus.DRAFT,
            visibility=DocumentVisibility.PUBLIC,
        )

        resp = client.get("/api/v1/public/sitemap.xml")
        assert resp.status_code == 200
        assert f"<loc>/doc/{doc.id}</loc>" not in resp.text

    def test_internal_doc_not_in_sitemap(self, client, db, test_user):
        doc = create_document(
            db,
            created_by=test_user.id,
            title="Internal Only Doc",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.INTERNAL,
        )

        resp = client.get("/api/v1/public/sitemap.xml")
        assert resp.status_code == 200
        assert f"<loc>/doc/{doc.id}</loc>" not in resp.text

    def test_unpublished_doc_disappears_from_sitemap(self, client, db, test_user):
        doc = create_document(
            db,
            created_by=test_user.id,
            title="Unpublish Test",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.PUBLIC,
        )

        # Appears
        resp = client.get("/api/v1/public/sitemap.xml")
        assert f"<loc>/doc/{doc.id}</loc>" in resp.text

        # Unpublish
        doc.status = DocumentStatus.DRAFT
        db.commit()

        resp = client.get("/api/v1/public/sitemap.xml")
        assert f"<loc>/doc/{doc.id}</loc>" not in resp.text


# ---------------------------------------------------------------------------
# Y2-023: Broken link detection integration test
# ---------------------------------------------------------------------------

class TestBrokenLinkDetection:
    """Create document with broken internal link, run scan, verify report generated."""

    def test_broken_link_detected(self, client, db, test_user, test_admin):
        admin_headers = _login_headers(client, test_admin.username)

        # Create a document with a link to a non-existent document
        doc = create_document(
            db,
            created_by=test_user.id,
            title="Page With Broken Link",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.INTERNAL,
        )
        # Create a published version with broken link HTML
        version = Version(
            document_id=doc.id,
            version_number=1,
            content='<p>See <a href="/portal/documents/99999">missing doc</a></p>',
            is_published=True,
            published_at=datetime.utcnow(),
            created_by=test_user.id,
        )
        db.add(version)
        db.commit()

        # Trigger manual scan
        resp = client.post("/api/v1/broken-links/scan", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["broken_links_found"] >= 1

        # Verify report exists for our document
        reports = db.query(BrokenLinkReport).filter(
            BrokenLinkReport.document_id == doc.id
        ).all()
        assert len(reports) >= 1
        report = reports[0]
        assert report.reason == "target_not_found"
        assert "99999" in report.broken_url

    def test_valid_internal_link_not_flagged(self, client, db, test_user, test_admin):
        admin_headers = _login_headers(client, test_admin.username)

        # Create target doc
        target = create_document(
            db,
            created_by=test_user.id,
            title="Valid Target",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.INTERNAL,
        )

        # Create source doc linking to valid target
        source = create_document(
            db,
            created_by=test_user.id,
            title="Page With Valid Link",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.INTERNAL,
        )
        version = Version(
            document_id=source.id,
            version_number=1,
            content=f'<p>See <a href="/portal/documents/{target.id}">target doc</a></p>',
            is_published=True,
            published_at=datetime.utcnow(),
            created_by=test_user.id,
        )
        db.add(version)
        db.commit()

        # Trigger scan
        client.post("/api/v1/broken-links/scan", headers=admin_headers)

        # Verify no broken report for source doc linking to the valid target
        reports = db.query(BrokenLinkReport).filter(
            BrokenLinkReport.document_id == source.id
        ).all()
        broken_urls = [r.broken_url for r in reports]
        assert not any(str(target.id) in url for url in broken_urls)

    def test_broken_link_summary_endpoint(self, client, db, test_user, test_admin):
        admin_headers = _login_headers(client, test_admin.username)

        doc = create_document(
            db,
            created_by=test_user.id,
            title="Doc With Two Broken Links",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.INTERNAL,
        )
        version = Version(
            document_id=doc.id,
            version_number=1,
            content=(
                '<p><a href="/portal/documents/88888">gone</a> '
                'and <a href="/portal/documents/77777">also gone</a></p>'
            ),
            is_published=True,
            published_at=datetime.utcnow(),
            created_by=test_user.id,
        )
        db.add(version)
        db.commit()

        client.post("/api/v1/broken-links/scan", headers=admin_headers)

        resp = client.get("/api/v1/broken-links/summary", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_broken_links"] >= 2
