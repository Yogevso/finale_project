"""Extended attachment tools — search, stats, bulk info."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.assistant.tools.base import BaseTool
from app.models import Attachment, Document, User
from app.services.permissions import Permission


class SearchAttachmentsTool(BaseTool):
    name = "search_attachments"
    description = "Search attachments across documents by filename or type."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search by filename keyword", "maxLength": 255},
            "mime_type": {"type": "string", "description": "Filter by MIME type prefix (e.g. 'image/', 'application/pdf')", "maxLength": 255},
            "document_id": {"type": "integer", "description": "Limit to a specific document (optional)"},
            "limit": {"type": "integer", "description": "Max results (default 20)"},
        },
        "required": [],
    }
    required_permission = Permission.DOWNLOAD_ATTACHMENTS

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        limit = min(params.get("limit", 20), 50)
        q = db.query(Attachment)
        if tenant_id:
            q = q.join(Document).filter(Document.tenant_id == tenant_id)
        if params.get("query"):
            q = q.filter(Attachment.original_filename.ilike(f"%{params['query']}%"))
        if params.get("mime_type"):
            q = q.filter(Attachment.mime_type.ilike(f"{params['mime_type']}%"))
        if params.get("document_id"):
            q = q.filter(Attachment.document_id == params["document_id"])
        attachments = q.order_by(Attachment.uploaded_at.desc()).limit(limit).all()
        if not attachments:
            return {"success": True, "result": "No attachments found matching your criteria."}
        lines = [f"{len(attachments)} attachment(s) found:"]
        for a in attachments:
            size_kb = round(a.file_size / 1024, 1) if a.file_size else 0
            lines.append(
                f"- [{a.id}] {a.original_filename} ({a.mime_type}, {size_kb} KB) "
                f"— doc #{a.document_id}, uploaded {a.uploaded_at:%Y-%m-%d}"
            )
        return {"success": True, "result": "\n".join(lines)}


class GetAttachmentStatsTool(BaseTool):
    name = "get_attachment_stats"
    description = "Get attachment statistics for a document or tenant — count, total size, types."
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {"type": "integer", "description": "Specific document (optional, omit for tenant-wide)"},
        },
        "required": [],
    }
    required_permission = Permission.DOWNLOAD_ATTACHMENTS

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        q = db.query(Attachment)
        scope = "platform"
        if params.get("document_id"):
            q = q.filter(Attachment.document_id == params["document_id"])
            doc = db.query(Document).filter(Document.id == params["document_id"]).first()
            scope = f"document '{doc.title}'" if doc else f"document #{params['document_id']}"
        elif tenant_id:
            q = q.join(Document).filter(Document.tenant_id == tenant_id)
            scope = "your tenant"
        total = q.count()
        if total == 0:
            return {"success": True, "result": f"No attachments in {scope}."}
        total_size = q.with_entities(func.sum(Attachment.file_size)).scalar() or 0
        size_mb = round(total_size / (1024 * 1024), 1)
        # Top MIME types
        types = (
            q.with_entities(Attachment.mime_type, func.count(Attachment.id))
            .group_by(Attachment.mime_type)
            .order_by(func.count(Attachment.id).desc())
            .limit(5)
            .all()
        )
        type_lines = [f"  - {t}: {c}" for t, c in types]
        return {
            "success": True,
            "result": (
                f"Attachment stats for {scope}:\n"
                f"- Total files: {total}\n"
                f"- Total size: {size_mb} MB\n"
                f"- Top file types:\n" + "\n".join(type_lines)
            ),
        }


class GetLargestAttachmentsTool(BaseTool):
    name = "get_largest_attachments"
    description = "List the largest attachments (useful for storage management)."
    parameters = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Max results (default 10)"},
        },
        "required": [],
    }
    required_permission = Permission.DOWNLOAD_ATTACHMENTS

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        limit = min(params.get("limit", 10), 50)
        q = db.query(Attachment)
        if tenant_id:
            q = q.join(Document).filter(Document.tenant_id == tenant_id)
        attachments = q.order_by(Attachment.file_size.desc()).limit(limit).all()
        if not attachments:
            return {"success": True, "result": "No attachments found."}
        lines = [f"Top {len(attachments)} largest attachment(s):"]
        for a in attachments:
            size_mb = round(a.file_size / (1024 * 1024), 2) if a.file_size else 0
            lines.append(f"- [{a.id}] {a.original_filename} ({size_mb} MB) — doc #{a.document_id}")
        return {"success": True, "result": "\n".join(lines)}
