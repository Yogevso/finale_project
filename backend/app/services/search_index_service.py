"""Service for keeping the FTS5 search index in sync with audience changes."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
FTS_EXPECTED_COLUMNS = (
    "title",
    "description",
    "category",
    "tags",
    "tenant_id",
    "visibility",
    "status",
)

FTS_TABLE_NAME = "documents_fts"
FTS_EXISTS_STATEMENT = text(
    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = :table_name LIMIT 1"
)
FTS_DROP_STATEMENT = text(f"DROP TABLE IF EXISTS {FTS_TABLE_NAME}")
FTS_CREATE_STATEMENT = text(
    f"""
    CREATE VIRTUAL TABLE IF NOT EXISTS {FTS_TABLE_NAME} USING fts5(
        title,
        description,
        category,
        tags,
        tenant_id UNINDEXED,
        visibility UNINDEXED,
        status UNINDEXED
    )
    """
)
FTS_CLEAR_STATEMENT = text(f"DELETE FROM {FTS_TABLE_NAME}")
FTS_POPULATE_STATEMENT = text(
    f"""
    INSERT INTO {FTS_TABLE_NAME}(rowid, title, description, category, tags, tenant_id, visibility, status)
    SELECT
        id,
        COALESCE(title, ''),
        COALESCE(description, ''),
        COALESCE(category, ''),
        COALESCE(tags, ''),
        COALESCE(CAST(tenant_id AS TEXT), ''),
        COALESCE(visibility, ''),
        COALESCE(status, '')
    FROM documents
    WHERE deleted_at IS NULL
    """
)
FTS_DELETE_ROW_STATEMENT = text(f"DELETE FROM {FTS_TABLE_NAME} WHERE rowid = :doc_id")
FTS_INSERT_ROW_STATEMENT = text(
    f"""
    INSERT INTO {FTS_TABLE_NAME}(rowid, title, description, category, tags, tenant_id, visibility, status)
    SELECT
        id,
        COALESCE(title, ''),
        COALESCE(description, ''),
        COALESCE(category, ''),
        COALESCE(tags, ''),
        COALESCE(CAST(tenant_id AS TEXT), ''),
        COALESCE(visibility, ''),
        COALESCE(status, '')
    FROM documents
    WHERE id = :doc_id
      AND deleted_at IS NULL
    """
)
FTS_INTEGRITY_CHECK_STATEMENT = text(
    f"INSERT INTO {FTS_TABLE_NAME}({FTS_TABLE_NAME}) VALUES('integrity-check')"
)


class SearchIndexSyncService:
    """Synchronises the ``documents_fts`` FTS5 virtual table with the
    canonical ``documents`` table.

    The index is managed explicitly so startup paths can recover cleanly
    even when the FTS table was never created.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def _rebuild_index_contents(self) -> None:
        self.db.execute(FTS_CLEAR_STATEMENT)
        self.db.execute(FTS_POPULATE_STATEMENT)

    def _get_index_columns(self) -> tuple[str, ...]:
        rows = self.db.execute(text(f"PRAGMA table_info({FTS_TABLE_NAME})")).fetchall()
        return tuple(str(row[1]) for row in rows)

    def _recreate_index(self) -> None:
        self.db.execute(FTS_DROP_STATEMENT)
        self.db.execute(FTS_CREATE_STATEMENT)
        self._rebuild_index_contents()

    def _ensure_index_exists(self) -> None:
        index_exists = self.db.execute(
            FTS_EXISTS_STATEMENT,
            {"table_name": FTS_TABLE_NAME},
        ).scalar()
        if index_exists:
            if self._get_index_columns() == FTS_EXPECTED_COLUMNS:
                return
            self._recreate_index()
            logger.info("Rebuilt FTS5 search index with updated schema")
            return

        self._recreate_index()
        logger.info("Initialized FTS5 search index")

    # ------------------------------------------------------------------
    # Single-document operations
    # ------------------------------------------------------------------

    def sync_document(self, document_id: int) -> None:
        """Refresh the FTS5 entry for a single document."""
        try:
            self._ensure_index_exists()
            self.db.execute(FTS_DELETE_ROW_STATEMENT, {"doc_id": document_id})
            self.db.execute(FTS_INSERT_ROW_STATEMENT, {"doc_id": document_id})
            logger.debug("FTS5 index synced for document %d", document_id)
        except OperationalError:
            logger.warning(
                "FTS5 sync failed for document %d; will be fixed on next rebuild",
                document_id,
                exc_info=True,
            )

    def remove_document(self, document_id: int) -> None:
        """Remove a single document from the FTS5 index (e.g. on delete)."""
        try:
            self._ensure_index_exists()
            self.db.execute(FTS_DELETE_ROW_STATEMENT, {"doc_id": document_id})
            logger.debug("FTS5 index entry removed for document %d", document_id)
        except OperationalError:
            logger.warning("FTS5 remove failed for document %d", document_id, exc_info=True)

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def rebuild_index(self) -> int:
        """Full rebuild of the FTS5 index from the ``documents`` table."""
        try:
            self._ensure_index_exists()
            self._rebuild_index_contents()
            count = (
                self.db.execute(
                    text("SELECT COUNT(*) FROM documents WHERE deleted_at IS NULL")
                ).scalar()
                or 0
            )
            logger.info("FTS5 search index rebuilt - %d documents indexed", count)
            return int(count)
        except OperationalError:
            logger.error("FTS5 full rebuild failed", exc_info=True)
            raise

    def integrity_check(self) -> bool:
        """Run the FTS5 integrity-check command. Returns True if healthy."""
        try:
            self._ensure_index_exists()
            self.db.execute(FTS_INTEGRITY_CHECK_STATEMENT)
            return True
        except OperationalError:
            logger.warning("FTS5 integrity check failed", exc_info=True)
            return False
