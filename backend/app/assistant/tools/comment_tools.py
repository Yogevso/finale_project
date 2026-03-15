"""AI assistant tools for document comments."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.assistant.tools.base import BaseTool
from app.models import Comment, Document, User
from app.services.permissions import Permission

logger = logging.getLogger(__name__)


def _check_doc_access(doc_id: int, tenant_id: int | None, db: Session) -> Document | None:
    q = db.query(Document).filter(Document.id == doc_id)
    if tenant_id is not None:
        q = q.filter(Document.tenant_id == tenant_id)
    return q.first()


class ListDocumentCommentsTool(BaseTool):
    name = "list_document_comments"
    description = "List all comments on a document, optionally including resolved comments."
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {"type": "integer", "description": "The document ID"},
            "include_resolved": {"type": "boolean", "description": "Include resolved comments (default false)"},
        },
        "required": ["document_id"],
    }
    required_role = "VIEWER"

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session,
    ) -> dict[str, Any]:
        doc_id = params["document_id"]
        doc = _check_doc_access(doc_id, tenant_id, db)
        if not doc:
            return {"success": False, "result": "", "error": "Document not found or you don't have access."}

        query = db.query(Comment).filter(
            Comment.document_id == doc_id,
            Comment.parent_id.is_(None),  # top-level only
        )
        if not params.get("include_resolved"):
            query = query.filter(Comment.is_resolved == False)

        comments = query.order_by(Comment.created_at.desc()).all()
        if not comments:
            return {"success": True, "result": f"No comments found on '{doc.title}'."}

        user_ids = {c.user_id for c in comments}
        # Also gather reply authors
        all_comment_ids = [c.id for c in comments]
        replies = (
            db.query(Comment)
            .filter(Comment.parent_id.in_(all_comment_ids))
            .order_by(Comment.created_at)
            .all()
        )
        for r in replies:
            user_ids.add(r.user_id)
        users = {u.id: u.full_name or u.email for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}

        reply_map: dict[int, list] = {}
        for r in replies:
            reply_map.setdefault(r.parent_id, []).append(r)

        lines = [f"**Comments on '{doc.title}'** ({len(comments)} top-level)\n"]
        for c in comments:
            author = users.get(c.user_id, "Unknown")
            date = c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else "N/A"
            resolved = " [Resolved]" if c.is_resolved else ""
            lines.append(f"- **{author}** ({date}){resolved} — ID: {c.id}")
            lines.append(f"  {c.content[:200]}")
            for r in reply_map.get(c.id, []):
                r_author = users.get(r.user_id, "Unknown")
                r_date = r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "N/A"
                lines.append(f"  ↳ **{r_author}** ({r_date}): {r.content[:150]}")

        return {"success": True, "result": "\n".join(lines)}


class AddCommentTool(BaseTool):
    name = "add_comment"
    description = "Add a comment to a document. Can reply to an existing comment by providing parent_id."
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {"type": "integer", "description": "The document ID"},
            "content": {"type": "string", "description": "Comment text"},
            "parent_id": {"type": "integer", "description": "Parent comment ID for threaded reply"},
        },
        "required": ["document_id", "content"],
    }
    required_role = "VIEWER"

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session,
    ) -> dict[str, Any]:
        doc_id = params["document_id"]
        doc = _check_doc_access(doc_id, tenant_id, db)
        if not doc:
            return {"success": False, "result": "", "error": "Document not found or you don't have access."}

        content = params.get("content", "").strip()
        if not content:
            return {"success": False, "result": "", "error": "Comment content is required."}

        comment = Comment(
            document_id=doc_id,
            user_id=user.id,
            content=content[:2000],
            parent_id=params.get("parent_id"),
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)

        return {
            "success": True,
            "result": f"Comment added (ID: {comment.id}) on '{doc.title}'.",
        }


class ResolveCommentTool(BaseTool):
    name = "resolve_comment"
    description = "Mark a comment as resolved."
    parameters = {
        "type": "object",
        "properties": {
            "comment_id": {"type": "integer", "description": "The comment ID to resolve"},
        },
        "required": ["comment_id"],
    }
    required_role = "EDITOR"

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session,
    ) -> dict[str, Any]:
        comment = db.query(Comment).filter(Comment.id == params["comment_id"]).first()
        if not comment:
            return {"success": False, "result": "", "error": "Comment not found."}

        # Verify document access
        doc = _check_doc_access(comment.document_id, tenant_id, db)
        if not doc:
            return {"success": False, "result": "", "error": "You don't have access to this document."}

        comment.is_resolved = True
        db.commit()
        return {"success": True, "result": f"Comment {comment.id} marked as resolved."}
