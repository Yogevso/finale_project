"""AI assistant tools for real-time collaboration awareness."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.assistant.tools.base import BaseTool
from app.models import CollaborationActivity, CollaborationSession, Document, User

logger = logging.getLogger(__name__)


def _check_doc_access(doc_id: int, tenant_id: int | None, db: Session) -> Document | None:
    q = db.query(Document).filter(Document.id == doc_id)
    if tenant_id is not None:
        q = q.filter(Document.tenant_id == tenant_id)
    return q.first()


class GetActiveCollaboratorsTool(BaseTool):
    name = "get_active_collaborators"
    description = "Show who is currently editing a document in real-time."
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {"type": "integer", "description": "The document ID"},
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

        sessions = (
            db.query(CollaborationSession)
            .filter(
                CollaborationSession.document_id == doc_id,
                CollaborationSession.is_active == True,
            )
            .all()
        )
        if not sessions:
            return {"success": True, "result": f"No active collaborators on '{doc.title}' right now."}

        user_ids = {s.user_id for s in sessions}
        users = {u.id: u.full_name or u.email for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}

        lines = [f"**Active collaborators on '{doc.title}'** ({len(sessions)})\n"]
        for s in sessions:
            name = users.get(s.user_id, "Unknown")
            last = s.last_activity_at.strftime("%H:%M:%S") if s.last_activity_at else "N/A"
            edits = s.edits_count or 0
            lines.append(f"- **{name}** — {edits} edits, last active at {last}")

        return {"success": True, "result": "\n".join(lines)}


class GetCollaborationHistoryTool(BaseTool):
    name = "get_collaboration_history"
    description = "Show recent collaboration activity on a document."
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {"type": "integer", "description": "The document ID"},
            "limit": {"type": "integer", "description": "Max activities to return (default 20)"},
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

        limit = min(params.get("limit", 20), 50)
        activities = (
            db.query(CollaborationActivity)
            .filter(CollaborationActivity.document_id == doc_id)
            .order_by(CollaborationActivity.created_at.desc())
            .limit(limit)
            .all()
        )
        if not activities:
            return {"success": True, "result": f"No collaboration activity found for '{doc.title}'."}

        user_ids = {a.user_id for a in activities}
        users = {u.id: u.full_name or u.email for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}

        lines = [f"**Collaboration history for '{doc.title}'** (last {len(activities)} activities)\n"]
        for a in activities:
            name = users.get(a.user_id, "Unknown")
            date = a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else "N/A"
            activity_type = a.activity_type.value if a.activity_type else "unknown"
            lines.append(f"- {date} — **{name}** — {activity_type}")

        return {"success": True, "result": "\n".join(lines)}
