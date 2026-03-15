"""RAG (Retrieval-Augmented Generation) module for the AI assistant."""

from app.assistant.rag.chunker import Chunk, DocumentChunker
from app.assistant.rag.embeddings import OllamaEmbeddings
from app.assistant.rag.indexer import DocumentIndexer
from app.assistant.rag.vector_store import VectorStore

__all__ = [
    "Chunk",
    "DocumentChunker",
    "DocumentIndexer",
    "OllamaEmbeddings",
    "VectorStore",
]
