"""ChromaDB vector store wrapper for document chunk storage and retrieval."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import chromadb

from app.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "document_chunks"


@dataclass
class SearchResult:
    """A single search result from the vector store."""
    document_id: int
    document_title: str
    chunk_text: str
    section: str | None
    score: float  # similarity score (0-1, higher is better)
    chunk_index: int


class VectorStore:
    """Manage ChromaDB collections for document embeddings."""

    def __init__(self, persist_dir: str | None = None) -> None:
        self._persist_dir = persist_dir or settings.ASSISTANT_CHROMA_PERSIST_DIR
        self._client: chromadb.ClientAPI | None = None

    def _get_client(self) -> chromadb.ClientAPI:
        if self._client is None:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self._client = chromadb.PersistentClient(
                path=self._persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        return self._client

    def _get_collection(self) -> chromadb.Collection:
        client = self._get_client()
        return client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(
        self,
        doc_id: int,
        doc_title: str,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> int:
        """Store document chunks with their embeddings.

        Args:
            doc_id: Document ID
            doc_title: Document title for metadata
            chunks: List of chunk dicts with keys: text, chunk_index, section
            embeddings: Corresponding embedding vectors

        Returns:
            Number of chunks stored
        """
        if not chunks or not embeddings:
            return 0

        collection = self._get_collection()

        ids = [f"doc_{doc_id}_chunk_{c['chunk_index']}" for c in chunks]
        documents = [c["text"] for c in chunks]
        metadatas = [
            {
                "document_id": doc_id,
                "document_title": doc_title,
                "chunk_index": c["chunk_index"],
                "section": c.get("section") or "",
            }
            for c in chunks
        ]

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info("Stored %d chunks for document %d (%s)", len(chunks), doc_id, doc_title)
        return len(chunks)

    def query(
        self,
        query_embedding: list[float],
        n_results: int | None = None,
        min_score: float | None = None,
        document_id: int | None = None,
    ) -> list[SearchResult]:
        """Query the vector store for similar chunks.

        Args:
            query_embedding: The query vector
            n_results: Max results to return
            min_score: Minimum similarity score (0-1)
            document_id: If set, only search within this document

        Returns:
            Ranked list of SearchResult
        """
        n = n_results or settings.ASSISTANT_RAG_TOP_K
        threshold = min_score if min_score is not None else settings.ASSISTANT_RAG_MIN_SCORE
        collection = self._get_collection()

        where_filter = None
        if document_id is not None:
            where_filter = {"document_id": document_id}

        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )
        except Exception:
            logger.exception("ChromaDB query failed")
            return []

        search_results: list[SearchResult] = []
        if not results or not results.get("ids") or not results["ids"][0]:
            return search_results

        ids = results["ids"][0]
        documents = results["documents"][0] if results.get("documents") else [""] * len(ids)
        metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(ids)
        distances = results["distances"][0] if results.get("distances") else [1.0] * len(ids)

        for doc_text, meta, distance in zip(documents, metadatas, distances):
            # ChromaDB cosine distance: 0 = identical, 2 = opposite. Convert to similarity.
            score = 1.0 - (distance / 2.0)
            if score < threshold:
                continue
            search_results.append(SearchResult(
                document_id=meta.get("document_id", 0),
                document_title=meta.get("document_title", ""),
                chunk_text=doc_text,
                section=meta.get("section") or None,
                score=round(score, 4),
                chunk_index=meta.get("chunk_index", 0),
            ))

        return search_results

    def delete_document(self, doc_id: int) -> int:
        """Remove all chunks for a document. Returns number of chunks removed."""
        collection = self._get_collection()
        try:
            # Get IDs matching this document
            existing = collection.get(
                where={"document_id": doc_id},
                include=[],
            )
            if existing and existing["ids"]:
                collection.delete(ids=existing["ids"])
                count = len(existing["ids"])
                logger.info("Removed %d chunks for document %d", count, doc_id)
                return count
        except Exception:
            logger.exception("Failed to delete chunks for document %d", doc_id)
        return 0

    def get_stats(self) -> dict[str, Any]:
        """Get vector store statistics."""
        try:
            collection = self._get_collection()
            count = collection.count()
            # Get unique document IDs
            if count > 0:
                result = collection.get(include=["metadatas"], limit=10000)
                doc_ids = {m.get("document_id") for m in (result.get("metadatas") or []) if m}
                return {
                    "total_chunks": count,
                    "total_documents": len(doc_ids),
                    "status": "ready",
                }
            return {"total_chunks": 0, "total_documents": 0, "status": "empty"}
        except Exception:
            logger.exception("Failed to get vector store stats")
            return {"total_chunks": 0, "total_documents": 0, "status": "error"}
