"""AI assistant tools for document attachment queries."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.assistant.tools.base import BaseTool
from app.models import Attachment, Document, User

logger = logging.getLogger(__name__)


def _check_doc_access(doc_id: int, tenant_id: int | None, db: Session) -> Document | None:
    q = db.query(Document).filter(Document.id == doc_id)
    if tenant_id is not None:
        q = q.filter(Document.tenant_id == tenant_id)
    return q.first()


class ListAttachmentsTool(BaseTool):
    name = "list_attachments"
    description = "List all files attached to a document."
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {"type": "integer", "description": "The document ID"},
        },
        "required": ["document_id"],
    }
    required_role = "VIEWER"

    async def execute(
        self,
        user: User,
        tenant_id: int | None,
        params: dict[str, Any],
        db: Session,
    ) -> dict[str, Any]:
        doc_id = params["document_id"]
        doc = _check_doc_access(doc_id, tenant_id, db)
        if not doc:
            return {
                "success": False,
                "result": "",
                "error": "Document not found or you don't have access.",
            }

        attachments = (
            db.query(Attachment)
            .filter(Attachment.document_id == doc_id)
            .order_by(Attachment.uploaded_at.desc())
            .all()
        )
        if not attachments:
            return {"success": True, "result": f"No attachments found for '{doc.title}'."}

        user_ids = {a.uploaded_by for a in attachments if a.uploaded_by}
        users = (
            {
                u.id: u.full_name or u.email
                for u in db.query(User).filter(User.id.in_(user_ids)).all()
            }
            if user_ids
            else {}
        )

        lines = [f"**Attachments for '{doc.title}'** ({len(attachments)} files)\n"]
        for a in attachments:
            uploader = users.get(a.uploaded_by, "Unknown")
            size_kb = (a.file_size or 0) / 1024
            date = a.uploaded_at.strftime("%Y-%m-%d %H:%M") if a.uploaded_at else "N/A"
            lines.append(
                f"- **{a.original_filename}** (ID: {a.id}) | "
                f"{a.mime_type} | {size_kb:.1f} KB | "
                f"Uploaded by {uploader} on {date}"
            )
        return {"success": True, "result": "\n".join(lines)}


class GetAttachmentInfoTool(BaseTool):
    name = "get_attachment_info"
    description = "Get detailed information about a specific file attachment."
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {"type": "integer", "description": "The document ID"},
            "attachment_id": {"type": "integer", "description": "The attachment ID"},
        },
        "required": ["document_id", "attachment_id"],
    }
    required_role = "VIEWER"

    async def execute(
        self,
        user: User,
        tenant_id: int | None,
        params: dict[str, Any],
        db: Session,
    ) -> dict[str, Any]:
        doc_id = params["document_id"]
        doc = _check_doc_access(doc_id, tenant_id, db)
        if not doc:
            return {
                "success": False,
                "result": "",
                "error": "Document not found or you don't have access.",
            }

        attachment = (
            db.query(Attachment)
            .filter(Attachment.id == params["attachment_id"], Attachment.document_id == doc_id)
            .first()
        )
        if not attachment:
            return {"success": False, "result": "", "error": "Attachment not found."}

        uploader_name = "Unknown"
        if attachment.uploaded_by:
            u = db.query(User).filter(User.id == attachment.uploaded_by).first()
            if u:
                uploader_name = u.full_name or u.email

        size_kb = (attachment.file_size or 0) / 1024
        date = (
            attachment.uploaded_at.strftime("%Y-%m-%d %H:%M") if attachment.uploaded_at else "N/A"
        )

        lines = [
            "**Attachment Details**\n",
            f"- **Filename:** {attachment.original_filename}",
            f"- **Type:** {attachment.mime_type}",
            f"- **Size:** {size_kb:.1f} KB",
            f"- **SHA256:** {attachment.sha256 or 'N/A'}",
            f"- **Uploaded by:** {uploader_name}",
            f"- **Uploaded at:** {date}",
            f"- **Reader view status:** {attachment.reader_html_status or 'N/A'}",
        ]
        return {"success": True, "result": "\n".join(lines)}
