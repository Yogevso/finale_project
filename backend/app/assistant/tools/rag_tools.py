"""RAG-powered tools — semantic search, document summarization, and Q&A."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.assistant.document_access import (
    assistant_can_view_document,
    resolve_assistant_visible_version,
)
from app.assistant.rag.chunker import DocumentChunker
from app.assistant.rag.embeddings import OllamaEmbeddings
from app.assistant.rag.vector_store import VectorStore
from app.assistant.tools.base import BaseTool
from app.config import settings
from app.models import Document, User, UserRole

logger = logging.getLogger(__name__)

# Shared instances (initialized once, reused)
_embeddings = OllamaEmbeddings()
_vector_store = VectorStore()
_chunker = DocumentChunker()


class SemanticSearchTool(BaseTool):
    name = "semantic_search"
    description = (
        "Search all document content semantically. Finds relevant passages "
        "even when exact keywords don't match. Use this when the user wants "
        "to find information across documents by meaning, not just title."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query — what you're looking for in document content.",
                "maxLength": 1000,
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return (default 5).",
            },
        },
        "required": ["query"],
    }
    # H-04: Block CUSTOMER role from internal semantic search
    required_role = "EDITOR"

    async def execute(
        self,
        user: User,
        tenant_id: int | None,
        params: dict[str, Any],
        db: Session,
    ) -> dict[str, Any]:
        query = params.get("query", "").strip()
        if not query:
            return {"success": False, "error": "Search query is required."}

        limit = params.get("limit", 5)
        if not isinstance(limit, int) or limit < 1:
            limit = 5

        try:
            query_embedding = await _embeddings.embed_text(query)
        except (
            Exception
        ):  # policy: BOUNDARY — semantic search failures become tool errors, not crashes
            logger.exception("Failed to embed search query")
            return {
                "success": False,
                "error": "Semantic search is temporarily unavailable (embedding service error).",
            }

        results = _vector_store.query(
            query_embedding=query_embedding,
            n_results=limit,
            tenant_id=tenant_id,
            is_system_admin=(user.role == UserRole.SYSTEM_ADMIN),
        )

        if not results:
            return {"success": True, "result": "No relevant content found for your query."}

        # Filter by user's accessible documents (tenant + visibility policy)
        results = [
            r
            for r in results
            if _user_can_access_document(user, r.document_id, db, tenant_id=tenant_id)
        ]

        if not results:
            return {
                "success": True,
                "result": "No relevant content found within your accessible documents.",
            }

        lines = [f"Found {len(results)} relevant passage(s):\n"]
        for i, r in enumerate(results, 1):
            section_info = f" (Section: {r.section})" if r.section else ""
            snippet = r.chunk_text[:300] + "…" if len(r.chunk_text) > 300 else r.chunk_text
            lines.append(
                f"**{i}. {r.document_title}**{section_info} — Score: {r.score:.2f}\n"
                f"   {snippet}\n"
            )
        return {"success": True, "result": "\n".join(lines)}


class SummarizeDocumentTool(BaseTool):
    name = "summarize_document"
    description = (
        "Generate a concise summary of a document's content. "
        "Use when a user asks for a summary, overview, or TL;DR of a document."
    )
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {
                "type": "integer",
                "description": "The ID of the document to summarize.",
            },
            "max_length": {
                "type": "string",
                "description": 'Summary length: "short" (2-3 sentences), "medium" (1 paragraph), or "long" (3-5 paragraphs). Default: medium.',
                "enum": ["short", "medium", "long"],
            },
        },
        "required": ["document_id"],
    }

    async def execute(
        self,
        user: User,
        tenant_id: int | None,
        params: dict[str, Any],
        db: Session,
    ) -> dict[str, Any]:
        doc_id = params.get("document_id")
        if not doc_id:
            return {"success": False, "error": "document_id is required."}

        max_length = params.get("max_length", "medium")

        # Fetch document
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return {"success": False, "error": f"Document {doc_id} not found."}

        # Check access via DocumentAccessPolicy (tenant + visibility + role)
        if not assistant_can_view_document(user, doc, tenant_id=tenant_id):
            return {"success": False, "error": "You don't have access to this document."}

        version = resolve_assistant_visible_version(
            db,
            user=user,
            document=doc,
            tenant_id=tenant_id,
        )
        if not version or not version.content:
            return {"success": False, "error": "This document has no content to summarize."}

        # Strip HTML and get plain text
        text = _chunker.strip_html(version.content)
        if not text.strip():
            return {"success": False, "error": "This document has no text content."}

        # Truncate to ~4000 chars to fit in context window
        max_chars = 4000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Content truncated for summarization]"

        length_instructions = {
            "short": "Provide a very brief summary in 2-3 sentences.",
            "medium": "Provide a summary in one clear paragraph.",
            "long": "Provide a detailed summary in 3-5 paragraphs covering all key topics.",
        }
        instruction = length_instructions.get(max_length, length_instructions["medium"])

        # Use Ollama to summarize
        from app.assistant.ollama_client import OllamaClient

        ollama = OllamaClient(settings.OLLAMA_BASE_URL, settings.ASSISTANT_MODEL)

        messages = [
            {
                "role": "system",
                "content": f"You are a document summarizer. {instruction} Be factual and concise. Only use information from the provided document text.",
            },
            {
                "role": "user",
                "content": f'Summarize this document titled "{doc.title}":\n\n{text}',
            },
        ]

        try:
            response = await ollama.chat(
                messages=messages,
                temperature=0.3,
                max_tokens=1024,
                num_ctx=8192,
            )
            summary = response.get("message", {}).get("content", "").strip()
            if not summary:
                return {"success": False, "error": "Failed to generate summary."}
            return {
                "success": True,
                "result": f'**Summary of "{doc.title}":**\n\n{summary}',
            }
        except (
            Exception
        ):  # policy: BOUNDARY — summarization failures become tool errors, not crashes
            logger.exception("Failed to generate document summary")
            return {"success": False, "error": "Summarization failed. The AI service may be busy."}


class AskAboutDocumentTool(BaseTool):
    name = "ask_about_document"
    description = (
        "Ask a question about a specific document's content and get an answer "
        "based on the actual document text. Use when a user asks about what a "
        "document says or wants specific information from a document."
    )
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {
                "type": "integer",
                "description": "The ID of the document to ask about.",
            },
            "question": {
                "type": "string",
                "description": "The question to ask about the document's content.",
                "maxLength": 1000,
            },
        },
        "required": ["document_id", "question"],
    }

    async def execute(
        self,
        user: User,
        tenant_id: int | None,
        params: dict[str, Any],
        db: Session,
    ) -> dict[str, Any]:
        doc_id = params.get("document_id")
        question = params.get("question", "").strip()
        if not doc_id or not question:
            return {"success": False, "error": "document_id and question are required."}

        # Fetch document
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return {"success": False, "error": f"Document {doc_id} not found."}

        # Check access via DocumentAccessPolicy (tenant + visibility + role)
        if not assistant_can_view_document(user, doc, tenant_id=tenant_id):
            return {"success": False, "error": "You don't have access to this document."}

        # Try RAG: embed question → retrieve relevant chunks from this doc
        version = resolve_assistant_visible_version(
            db,
            user=user,
            document=doc,
            tenant_id=tenant_id,
        )
        if not version or not version.content:
            return {"success": False, "error": "This document has no content."}
        context = _chunker.strip_html(version.content)[:4000]
        sources = []

        # Ask Ollama with context
        from app.assistant.ollama_client import OllamaClient

        ollama = OllamaClient(settings.OLLAMA_BASE_URL, settings.ASSISTANT_MODEL)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a document expert. Answer the user's question based ONLY on the "
                    "provided document context. If the answer isn't in the context, say so clearly. "
                    "Be specific and cite relevant sections when possible."
                ),
            },
            {
                "role": "user",
                "content": (
                    f'Document: "{doc.title}"\n\n'
                    f"Context from the document:\n{context}\n\n"
                    f"Question: {question}"
                ),
            },
        ]

        try:
            response = await ollama.chat(
                messages=messages,
                temperature=0.3,
                max_tokens=1024,
                num_ctx=8192,
            )
            answer = response.get("message", {}).get("content", "").strip()
            if not answer:
                return {"success": False, "error": "Failed to generate answer."}

            result = f'**Answer about "{doc.title}":**\n\n{answer}'
            if sources:
                result += f"\n\n*Sources: {', '.join(sources)}*"
            return {"success": True, "result": result}
        except Exception:  # policy: BOUNDARY — document QA failures become tool errors, not crashes
            logger.exception("Failed to answer question about document")
            return {"success": False, "error": "Q&A failed. The AI service may be busy."}


def _user_can_access_document(
    user: User,
    document_id: int,
    db: Session,
    *,
    tenant_id: int | None = None,
) -> bool:
    """Check if user can access a specific document via DocumentAccessPolicy."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        return False
    return assistant_can_view_document(user, doc, tenant_id=tenant_id)
