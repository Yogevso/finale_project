"""Document-related assistant tools."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.assistant.tools.base import BaseTool
from app.models import Document, DocumentStatus, DocumentVisibility, Topic, User
from app.services.permissions import Permission

from datetime import datetime, timedelta


class SearchDocumentsTool(BaseTool):
    name = "search_documents"
    description = "Search documents by title or content. Returns matching documents with their ID, title, status, and topic."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query text"},
            "status": {
                "type": "string",
                "description": "Filter by status",
                "enum": ["draft", "pending_review", "approved", "active", "archived"],
            },
            "topic": {"type": "string", "description": "Filter by topic slug"},
            "limit": {"type": "integer", "description": "Max results (default 10)"},
        },
        "required": ["query"],
    }
    required_permission = Permission.VIEW_INTERNAL_DOCS

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        q = params["query"]
        limit = min(params.get("limit", 10), 50)

        query = db.query(Document).filter(Document.title.ilike(f"%{q}%"))
        if tenant_id is not None:
            query = query.filter(Document.tenant_id == tenant_id)
        if params.get("status"):
            query = query.filter(Document.status == params["status"])
        if params.get("topic"):
            query = query.filter(Document.topic == params["topic"])

        docs = query.order_by(Document.updated_at.desc()).limit(limit).all()
        if not docs:
            return {"success": True, "result": f"No documents found matching '{q}'."}

        lines = [f"Found {len(docs)} document(s):"]
        for d in docs:
            lines.append(f"- [{d.id}] {d.title} (status: {d.status}, topic: {d.topic or 'none'})")
        return {"success": True, "result": "\n".join(lines)}


class GetDocumentTool(BaseTool):
    name = "get_document"
    description = "Get details of a single document by its ID, including title, status, author, dates, and a content preview."
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {"type": "integer", "description": "The document ID"},
        },
        "required": ["document_id"],
    }
    required_permission = Permission.VIEW_INTERNAL_DOCS

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        doc = db.query(Document).filter(Document.id == params["document_id"]).first()
        if doc is None:
            return {"success": False, "result": "", "error": "Document not found."}
        if tenant_id is not None and doc.tenant_id != tenant_id:
            return {"success": False, "result": "", "error": "Document not found."}

        info = (
            f"Title: {doc.title}\n"
            f"ID: {doc.id}\n"
            f"Document Number: {doc.document_number}\n"
            f"Status: {doc.status}\n"
            f"Visibility: {doc.visibility}\n"
            f"Topic: {doc.topic or 'none'}\n"
            f"Created: {doc.created_at}\n"
            f"Updated: {doc.updated_at}"
        )

        # Include content preview from latest version
        from app.models import Version
        version = (
            db.query(Version)
            .filter(Version.document_id == doc.id)
            .order_by(Version.version_number.desc())
            .first()
        )
        if version and version.content:
            from app.assistant.rag.chunker import DocumentChunker
            text = DocumentChunker.strip_html(version.content).strip()
            if text:
                preview = text[:2000]
                if len(text) > 2000:
                    preview += "\n... (content truncated)"
                info += f"\n\nContent:\n{preview}"
            else:
                info += "\n\nContent: (empty)"
        else:
            info += "\n\nContent: (no version content available)"

        return {"success": True, "result": info}


class CreateDocumentTool(BaseTool):
    name = "create_document"
    description = "Create a new document with a title and optional topic. Returns the new document's ID."
    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Document title"},
            "topic": {"type": "string", "description": "Topic slug (optional)"},
            "visibility": {
                "type": "string",
                "description": "Visibility level (default: internal)",
                "enum": ["public", "internal", "company"],
            },
        },
        "required": ["title"],
    }
    required_permission = Permission.CREATE_DOCUMENT

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        from datetime import datetime
        import uuid

        # Use UUID suffix to avoid race conditions from count()-based numbering
        unique_suffix = uuid.uuid4().hex[:8].upper()
        doc = Document(
            title=params["title"],
            topic=params.get("topic"),
            visibility=params.get("visibility", DocumentVisibility.INTERNAL),
            status=DocumentStatus.DRAFT,
            created_by=user.id,
            tenant_id=tenant_id,
            document_number=f"DOC-{datetime.utcnow().strftime('%Y%m%d')}-{unique_suffix}",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return {"success": True, "result": f"Document created — ID: {doc.id}, title: '{doc.title}'."}


class EditDocumentTool(BaseTool):
    name = "edit_document"
    description = "Update a document's title, status, or topic."
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {"type": "integer", "description": "The document ID to edit"},
            "title": {"type": "string", "description": "New title (optional)"},
            "status": {
                "type": "string",
                "description": "New status (optional)",
                "enum": ["draft", "pending_review", "approved", "active", "archived"],
            },
            "topic": {"type": "string", "description": "New topic slug (optional)"},
        },
        "required": ["document_id"],
    }
    required_permission = Permission.EDIT_DOCUMENT

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        doc = db.query(Document).filter(Document.id == params["document_id"]).first()
        if doc is None:
            return {"success": False, "result": "", "error": "Document not found."}
        if tenant_id is not None and doc.tenant_id != tenant_id:
            return {"success": False, "result": "", "error": "Document not found."}

        changes: list[str] = []
        if "title" in params:
            doc.title = params["title"]
            changes.append(f"title → '{params['title']}'")
        if "status" in params:
            doc.status = params["status"]
            changes.append(f"status → {params['status']}")
        if "topic" in params:
            doc.topic = params["topic"]
            changes.append(f"topic → {params['topic']}")

        if not changes:
            return {"success": True, "result": "No changes specified."}

        db.commit()
        return {"success": True, "result": f"Document {doc.id} updated: {', '.join(changes)}."}


class DeleteDocumentTool(BaseTool):
    name = "delete_document"
    description = "Delete a document permanently. This action cannot be undone."
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {"type": "integer", "description": "The document ID to delete"},
        },
        "required": ["document_id"],
    }
    required_permission = Permission.DELETE_DOCUMENT
    confirm_before_execute = True

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        doc = db.query(Document).filter(Document.id == params["document_id"]).first()
        if doc is None:
            return {"success": False, "result": "", "error": "Document not found."}
        if tenant_id is not None and doc.tenant_id != tenant_id:
            return {"success": False, "result": "", "error": "Document not found."}

        title = doc.title
        db.delete(doc)
        db.commit()
        return {"success": True, "result": f"Document '{title}' (ID: {params['document_id']}) deleted."}


class GetDocumentsByStatusTool(BaseTool):
    name = "get_documents_by_status"
    description = (
        "Get all documents with a specific status. Great for finding what's "
        "in draft, pending review, published, or archived."
    )
    parameters = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "Document status to filter by",
                "enum": ["draft", "pending_review", "approved", "active", "archived"],
            },
            "limit": {"type": "integer", "description": "Max results (default 20)"},
        },
        "required": ["status"],
    }
    required_role = "VIEWER"

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        status_map = {
            "draft": DocumentStatus.DRAFT,
            "pending_review": DocumentStatus.PENDING_REVIEW,
            "approved": DocumentStatus.APPROVED,
            "active": DocumentStatus.ACTIVE,
            "archived": DocumentStatus.ARCHIVED,
        }
        status_val = status_map.get(params["status"])
        if not status_val:
            return {"success": False, "result": "", "error": f"Invalid status. Use: {', '.join(status_map)}"}

        limit = min(params.get("limit", 20), 50)
        query = db.query(Document).filter(Document.status == status_val)
        if tenant_id is not None:
            query = query.filter(Document.tenant_id == tenant_id)
        docs = query.order_by(Document.updated_at.desc()).limit(limit).all()

        if not docs:
            return {"success": True, "result": f"No documents found with status '{params['status']}'."}

        lines = [f"**Documents with status '{params['status']}'** ({len(docs)} found)\n"]
        for d in docs:
            date = d.updated_at.strftime("%Y-%m-%d") if d.updated_at else "N/A"
            lines.append(f"- **{d.title}** (ID: {d.id}) | Updated: {date}")
        return {"success": True, "result": "\n".join(lines)}


class GetRecentDocumentsTool(BaseTool):
    name = "get_recent_documents"
    description = "Get the most recently created or updated documents."
    parameters = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Max results (default 10)"},
            "days": {"type": "integer", "description": "Look back period in days (default 7)"},
        },
        "required": [],
    }
    required_role = "VIEWER"

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        limit = min(params.get("limit", 10), 50)
        days = min(params.get("days", 7), 365)
        cutoff = datetime.utcnow() - timedelta(days=days)

        query = db.query(Document).filter(Document.updated_at >= cutoff)
        if tenant_id is not None:
            query = query.filter(Document.tenant_id == tenant_id)
        docs = query.order_by(Document.updated_at.desc()).limit(limit).all()

        if not docs:
            return {"success": True, "result": f"No documents updated in the last {days} days."}

        lines = [f"**Recent Documents** (last {days} days, {len(docs)} found)\n"]
        for d in docs:
            status = d.status.value if d.status else "N/A"
            date = d.updated_at.strftime("%Y-%m-%d %H:%M") if d.updated_at else "N/A"
            lines.append(f"- **{d.title}** (ID: {d.id}) | {status} | Updated: {date}")
        return {"success": True, "result": "\n".join(lines)}
