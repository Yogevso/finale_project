"""Document indexer — indexes document content into the vector store."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.assistant.rag.chunker import DocumentChunker
from app.assistant.rag.embeddings import OllamaEmbeddings
from app.assistant.rag.vector_store import VectorStore
from app.config import settings
from app.models import Document, DocumentStatus, Version

logger = logging.getLogger(__name__)


class DocumentIndexer:
    """Index document content into ChromaDB for RAG-powered search."""

    def __init__(
        self,
        embeddings: OllamaEmbeddings | None = None,
        vector_store: VectorStore | None = None,
        chunker: DocumentChunker | None = None,
    ) -> None:
        self._embeddings = embeddings or OllamaEmbeddings()
        self._store = vector_store or VectorStore()
        self._chunker = chunker or DocumentChunker()

    async def index_document(
        self,
        document_id: int,
        title: str,
        content: str,
        version_id: int | None = None,
    ) -> int:
        """Index a document's content into the vector store.

        Args:
            document_id: The document ID
            title: Document title (stored as metadata)
            content: HTML or plain text content
            version_id: Optional version ID for metadata

        Returns:
            Number of chunks indexed
        """
        if not content or not content.strip():
            logger.warning("No content to index for document %d", document_id)
            return 0

        # Remove old chunks first
        self._store.delete_document(document_id)

        # Chunk the content
        chunks = self._chunker.chunk_html(content)
        if not chunks:
            logger.warning("No chunks produced for document %d", document_id)
            return 0

        # Generate embeddings for all chunks in batch
        texts = [c.text for c in chunks]
        try:
            embeddings = await self._embeddings.embed_batch(texts)
        except Exception:
            logger.exception("Failed to generate embeddings for document %d", document_id)
            return 0

        if len(embeddings) != len(chunks):
            logger.error(
                "Embedding count mismatch for doc %d: %d chunks, %d embeddings",
                document_id, len(chunks), len(embeddings),
            )
            return 0

        # Store in vector store
        chunk_dicts = [
            {
                "text": c.text,
                "chunk_index": c.chunk_index,
                "section": c.section,
            }
            for c in chunks
        ]
        stored = self._store.add_chunks(document_id, title, chunk_dicts, embeddings)
        return stored

    async def remove_document(self, document_id: int) -> int:
        """Remove all indexed chunks for a document."""
        return self._store.delete_document(document_id)

    async def reindex_all(self, db: Session) -> dict[str, Any]:
        """Reindex all published documents. Returns stats."""
        # Get all documents with published versions
        documents = (
            db.query(Document)
            .filter(Document.status.in_([DocumentStatus.ACTIVE, DocumentStatus.DRAFT]))
            .all()
        )

        indexed = 0
        total_chunks = 0
        errors: list[str] = []

        for doc in documents:
            # Get the latest published version, or latest version
            version = (
                db.query(Version)
                .filter(
                    Version.document_id == doc.id,
                    Version.is_published == True,  # noqa: E712
                )
                .order_by(Version.version_number.desc())
                .first()
            )
            if not version:
                # Try latest version regardless of publish status
                version = (
                    db.query(Version)
                    .filter(Version.document_id == doc.id)
                    .order_by(Version.version_number.desc())
                    .first()
                )
            if not version or not version.content:
                continue

            try:
                count = await self.index_document(
                    doc.id, doc.title, version.content, version.id,
                )
                if count > 0:
                    indexed += 1
                    total_chunks += count
            except Exception as exc:
                logger.exception("Failed to index document %d", doc.id)
                errors.append(f"Document {doc.id} ({doc.title}): {exc}")

        stats = {
            "documents_indexed": indexed,
            "total_chunks": total_chunks,
            "documents_scanned": len(documents),
            "errors": errors,
        }
        logger.info("Reindex complete: %s", stats)
        return stats

    def get_status(self) -> dict[str, Any]:
        """Get current index status."""
        return self._store.get_stats()
