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
        tenant_id: int | None = None,
    ) -> int:
        """Index a document's content into the vector store.

        Args:
            document_id: The document ID
            title: Document title (stored as metadata)
            content: HTML or plain text content
            version_id: Optional version ID for metadata
            tenant_id: Tenant ID for access scoping

        Returns:
            Number of chunks indexed
        """
        if not content or not content.strip():
            logger.warning("No content to index for document %d", document_id)
            return 0

        if tenant_id is None:
            raise ValueError(f"tenant_id is required when indexing document {document_id}")

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
        except Exception:  # policy: DEGRADED — indexing errors should surface as warnings without crashing callers
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
        stored = self._store.add_chunks(document_id, title, chunk_dicts, embeddings, tenant_id=tenant_id)
        return stored

    async def ensure_ready(self) -> None:
        """Fail fast when the embedding backend is unavailable."""
        if not await self._embeddings.ensure_model():
            raise RuntimeError(
                "Assistant embedding backend is unavailable. "
                "Start Ollama and ensure the embedding model is installed, then retry."
            )

    async def remove_document(self, document_id: int) -> int:
        """Remove all indexed chunks for a document."""
        return self._store.delete_document(document_id)

    async def reindex_all(self, db: Session) -> dict[str, Any]:
        """Reindex all assistant-searchable documents. Returns stats."""
        documents = (
            db.query(Document.id, Document.title, Document.tenant_id)
            .filter(Document.status.in_([DocumentStatus.ACTIVE, DocumentStatus.DRAFT]))
            .all()
        )

        indexed = 0
        total_chunks = 0
        errors: list[str] = []

        for document_id, title, tenant_id in documents:
            # Semantic search is internal-only, so index the latest version to match
            # the assistant's document-read behavior for internal users.
            version = (
                db.query(Version)
                .filter(Version.document_id == document_id)
                .order_by(Version.version_number.desc())
                .first()
            )
            if not version or not version.content:
                continue

            try:
                count = await self.index_document(
                    document_id,
                    title,
                    version.content,
                    version.id,
                    tenant_id=tenant_id,
                )
                if count > 0:
                    indexed += 1
                    total_chunks += count
            except Exception as exc:  # policy: LOSSY — per-document indexing failure should not abort the batch
                logger.exception("Failed to index document %d", document_id)
                errors.append(f"Document {document_id} ({title}): {exc}")

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
