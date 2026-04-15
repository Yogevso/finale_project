"""Tests for search index audience synchronization (Task 184)."""

import uuid

from sqlalchemy import text

from app.domain.specifications.queries import VisibilitySpec


def _ensure_fts_table(db):
    """Create a standalone FTS5 virtual table in the test database.

    We use a *standalone* (non-content-sync) FTS table so that ``rebuild``
    does not try to read rows from the backing ``documents`` table where
    the column layout may differ between the production ``init_db.py``
    schema and the SQLAlchemy-only test schema.
    """
    db.execute(
        text(
            "CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5("
            "title, description, category, tags, tenant_id UNINDEXED, visibility UNINDEXED, status UNINDEXED)"
        )
    )
    db.commit()


class TestVisibilitySpecSqlClauses:
    """VisibilitySpec.sql_clauses produces correct raw-SQL fragments."""

    def test_public_only_returns_public_visibility_and_active_status(self):
        spec = VisibilitySpec.public_only()
        clauses, params = spec.sql_clauses()
        assert any("vis_status" in c for c in clauses), "Should filter by status"
        assert params["vis_status"] == "active"
        assert any("vis_public" in c for c in clauses), "Should filter by public visibility"
        assert params["vis_public"] == "public"

    def test_management_returns_all_visibility_types(self):
        spec = VisibilitySpec.management()
        clauses, params = spec.sql_clauses()
        assert params.get("vis_public") == "public"
        assert params.get("vis_internal") == "internal"
        assert params.get("vis_company") is None  # no company_tenant_id → no company clause

    def test_customer_portal_returns_public_and_company(self):
        spec = VisibilitySpec.customer_portal(customer_tenant_id=42)
        clauses, params = spec.sql_clauses()
        assert params.get("vis_public") == "public"
        assert params.get("vis_company") == "company"
        assert params.get("vis_company_tid") == 42
        assert "document_company_assignments" in " ".join(clauses)

    def test_empty_visibilities_produces_false_clause(self):
        spec = VisibilitySpec(allowed_visibilities=frozenset())
        clauses, params = spec.sql_clauses()
        assert "1 = 0" in clauses


class TestSearchIndexSyncService:
    """SearchIndexSyncService keeps FTS5 in sync with audience changes."""

    def test_sync_document_creates_missing_fts_table(self, db, test_user):
        """sync_document should self-heal when the FTS table is missing."""
        from app.models import Document, DocumentStatus
        from app.services.search_index_service import SearchIndexSyncService

        doc = Document(
            title="FTS bootstrap document",
            document_number=f"DOC-FTS-{uuid.uuid4().hex[:6].upper()}",
            description="Search index bootstrap",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
            tenant_id=test_user.tenant_id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        svc = SearchIndexSyncService(db)
        svc.sync_document(doc.id)

        table_exists = db.execute(
            text("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'documents_fts'")
        ).scalar()
        indexed_row = db.execute(
            text("SELECT rowid FROM documents_fts WHERE rowid = :doc_id"),
            {"doc_id": doc.id},
        ).scalar()

        assert table_exists == 1
        assert indexed_row == doc.id

    def test_sync_document_stores_tenant_partition_columns(self, db, test_user):
        from app.models import Document, DocumentStatus, DocumentVisibility
        from app.services.search_index_service import SearchIndexSyncService

        doc = Document(
            title="FTS tenant scope document",
            document_number=f"DOC-FTS-PART-{uuid.uuid4().hex[:6].upper()}",
            description="Search index partition data",
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.INTERNAL,
            created_by=test_user.id,
            tenant_id=test_user.tenant_id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        SearchIndexSyncService(db).sync_document(doc.id)

        row = db.execute(
            text("SELECT tenant_id, visibility, status FROM documents_fts WHERE rowid = :doc_id"),
            {"doc_id": doc.id},
        ).fetchone()

        assert row is not None
        assert str(row[0]) == str(test_user.tenant_id)
        assert str(row[1]).lower() == "internal"
        assert str(row[2]).lower() == "active"

    def test_sync_document_executes_delete_and_insert(self, db):
        """sync_document should run two SQL statements without error."""
        from app.services.search_index_service import SearchIndexSyncService

        _ensure_fts_table(db)
        svc = SearchIndexSyncService(db)
        # Should not raise even for a non-existent document
        svc.sync_document(99999)

    def test_rebuild_index_returns_count(self, db):
        """rebuild_index should return the total document count."""
        from app.services.search_index_service import SearchIndexSyncService

        _ensure_fts_table(db)
        svc = SearchIndexSyncService(db)
        count = svc.rebuild_index()
        assert isinstance(count, int)
        assert count >= 0

    def test_integrity_check_passes_on_empty_index(self, db):
        """integrity_check should return True on a freshly built index."""
        from app.services.search_index_service import SearchIndexSyncService

        _ensure_fts_table(db)
        svc = SearchIndexSyncService(db)
        svc.rebuild_index()
        assert svc.integrity_check() is True


class TestSearchAudienceCacheInvalidation:
    """Verify that audience changes invalidate search projection cache."""

    def test_invalidate_search_audience_cache_clears_search_scope(self):
        from app.projections.runtime import (
            invalidate_search_audience_cache,
            reset_projection_cache,
        )

        reset_projection_cache()
        # Should return 0 when nothing is cached
        cleared = invalidate_search_audience_cache()
        assert cleared == 0

    def test_search_scope_in_document_invalidation_map(self):
        """Document changes should invalidate both 'search' and 'public' scopes."""
        from app.models import Document
        from app.projections.invalidation import _MODEL_SCOPES

        doc_scopes = None
        for model, scopes in _MODEL_SCOPES:
            if model is Document:
                doc_scopes = scopes
                break
        assert doc_scopes is not None
        assert "search" in doc_scopes
        assert "public" in doc_scopes
        assert "portal" in doc_scopes
