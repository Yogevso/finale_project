"""Service for keeping the FTS5 search index in sync with audience changes."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SearchIndexSyncService:
    """Synchronises the ``documents_fts`` FTS5 virtual table with the
    canonical ``documents`` content table.

    SQLite FTS5 *content-sync* tables (``content='documents'``) do **not**
    auto-update when the backing rows change.  This service provides helpers
    to keep the index consistent after audience-relevant mutations (visibility,
    status, company-assignment changes) as well as content edits.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Single-document operations
    # ------------------------------------------------------------------

    def sync_document(self, document_id: int) -> None:
        """Refresh the FTS5 entry for a single document.

        This deletes the old FTS row (if any) and re-inserts it from the
        current ``documents`` row.  Safe to call even if the document was
        just created.
        """
        try:
            # Remove stale FTS row (using the FTS5 delete command)
            self.db.execute(
                text(
                    "INSERT INTO documents_fts(documents_fts, rowid, title, description, content, category) "
                    "SELECT 'delete', id, title, description, '', category "
                    "FROM documents WHERE id = :doc_id"
                ),
                {"doc_id": document_id},
            )
            # Re-insert from canonical source
            self.db.execute(
                text(
                    "INSERT INTO documents_fts(rowid, title, description, content, category) "
                    "SELECT id, title, description, '', category "
                    "FROM documents WHERE id = :doc_id"
                ),
                {"doc_id": document_id},
            )
            logger.debug("FTS5 index synced for document %d", document_id)
        except Exception:
            logger.warning("FTS5 sync failed for document %d – will be fixed on next rebuild", document_id, exc_info=True)

    def remove_document(self, document_id: int) -> None:
        """Remove a single document from the FTS5 index (e.g. on delete)."""
        try:
            self.db.execute(
                text(
                    "INSERT INTO documents_fts(documents_fts, rowid, title, description, content, category) "
                    "SELECT 'delete', id, title, description, '', category "
                    "FROM documents WHERE id = :doc_id"
                ),
                {"doc_id": document_id},
            )
            logger.debug("FTS5 index entry removed for document %d", document_id)
        except Exception:
            logger.warning("FTS5 remove failed for document %d", document_id, exc_info=True)

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def rebuild_index(self) -> int:
        """Full rebuild of the FTS5 index from the ``documents`` table.

        Returns the number of rows indexed.
        """
        try:
            self.db.execute(text("INSERT INTO documents_fts(documents_fts) VALUES('rebuild')"))
            count = self.db.execute(text("SELECT COUNT(*) FROM documents")).scalar() or 0
            logger.info("FTS5 search index rebuilt – %d documents indexed", count)
            return int(count)
        except Exception:
            logger.error("FTS5 full rebuild failed", exc_info=True)
            raise

    def integrity_check(self) -> bool:
        """Run the FTS5 integrity-check command.  Returns True if healthy."""
        try:
            self.db.execute(text("INSERT INTO documents_fts(documents_fts) VALUES('integrity-check')"))
            return True
        except Exception:
            logger.warning("FTS5 integrity check failed", exc_info=True)
            return False
