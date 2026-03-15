"""AI assistant tools for platform analytics (admin only)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.assistant.tools.base import BaseTool
from app.models import (
    AuditLog, Document, DocumentStatus, User, UserRole,
)
from app.services.permissions import Permission

logger = logging.getLogger(__name__)


def _period_cutoff(period: str) -> datetime:
    mapping = {"day": 1, "week": 7, "month": 30}
    days = mapping.get(period, 7)
    return datetime.utcnow() - timedelta(days=days)


class GetPlatformAnalyticsTool(BaseTool):
    name = "get_platform_analytics"
    description = (
        "Get platform overview analytics including total users, documents, "
        "and activity trends."
    )
    parameters = {
        "type": "object",
        "properties": {
            "period": {
                "type": "string",
                "description": "Time period: day, week, or month (default: week)",
                "enum": ["day", "week", "month"],
            },
        },
        "required": [],
    }
    required_permission = Permission.SYSTEM_SETTINGS

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session,
    ) -> dict[str, Any]:
        period = params.get("period", "week")
        cutoff = _period_cutoff(period)

        total_users = db.query(func.count(User.id)).scalar() or 0
        active_users = (
            db.query(func.count(func.distinct(AuditLog.user_id)))
            .filter(AuditLog.created_at >= cutoff)
            .scalar() or 0
        )
        total_docs = db.query(func.count(Document.id)).scalar() or 0
        published_docs = (
            db.query(func.count(Document.id))
            .filter(Document.status == DocumentStatus.ACTIVE)
            .scalar() or 0
        )
        recent_actions = (
            db.query(func.count(AuditLog.id))
            .filter(AuditLog.created_at >= cutoff)
            .scalar() or 0
        )

        result = (
            f"**Platform Analytics** (last {period})\n\n"
            f"- Total Users: {total_users}\n"
            f"- Active Users ({period}): {active_users}\n"
            f"- Total Documents: {total_docs}\n"
            f"- Published Documents: {published_docs}\n"
            f"- Actions ({period}): {recent_actions}"
        )
        return {"success": True, "result": result}


class GetEngagementAnalyticsTool(BaseTool):
    name = "get_engagement_analytics"
    description = (
        "Get user engagement metrics including most active users and popular documents."
    )
    parameters = {
        "type": "object",
        "properties": {
            "period": {"type": "string", "enum": ["day", "week", "month"]},
            "limit": {"type": "integer", "description": "Top N results (default 5)"},
        },
        "required": [],
    }
    required_permission = Permission.SYSTEM_SETTINGS

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session,
    ) -> dict[str, Any]:
        period = params.get("period", "week")
        limit = min(params.get("limit", 5), 20)
        cutoff = _period_cutoff(period)

        # Most active users
        top_users = (
            db.query(AuditLog.user_id, func.count(AuditLog.id).label("cnt"))
            .filter(AuditLog.created_at >= cutoff)
            .group_by(AuditLog.user_id)
            .order_by(func.count(AuditLog.id).desc())
            .limit(limit)
            .all()
        )

        user_ids = [uid for uid, _ in top_users]
        users = {u.id: u.full_name or u.email for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}

        lines = [f"**Engagement Analytics** (last {period})\n", "**Most Active Users:**"]
        for uid, cnt in top_users:
            lines.append(f"- {users.get(uid, f'User #{uid}')}: {cnt} actions")

        # Most edited documents
        top_docs = (
            db.query(AuditLog.document_id, func.count(AuditLog.id).label("cnt"))
            .filter(AuditLog.created_at >= cutoff, AuditLog.document_id.isnot(None))
            .group_by(AuditLog.document_id)
            .order_by(func.count(AuditLog.id).desc())
            .limit(limit)
            .all()
        )

        doc_ids = [did for did, _ in top_docs]
        docs = {d.id: d.title for d in db.query(Document).filter(Document.id.in_(doc_ids)).all()} if doc_ids else {}

        lines.append("\n**Most Active Documents:**")
        for did, cnt in top_docs:
            lines.append(f"- {docs.get(did, f'Doc #{did}')}: {cnt} actions")

        return {"success": True, "result": "\n".join(lines)}


class GetContentAnalyticsTool(BaseTool):
    name = "get_content_analytics"
    description = "Get content metrics including documents by status and top authors."
    parameters = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Top N results (default 10)"},
        },
        "required": [],
    }
    required_permission = Permission.SYSTEM_SETTINGS

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session,
    ) -> dict[str, Any]:
        limit = min(params.get("limit", 10), 50)

        # Documents by status
        status_counts = (
            db.query(Document.status, func.count(Document.id))
            .group_by(Document.status)
            .all()
        )

        # Top authors by document count
        top_authors = (
            db.query(Document.created_by, func.count(Document.id).label("cnt"))
            .group_by(Document.created_by)
            .order_by(func.count(Document.id).desc())
            .limit(limit)
            .all()
        )

        author_ids = [aid for aid, _ in top_authors]
        authors = {u.id: u.full_name or u.email for u in db.query(User).filter(User.id.in_(author_ids)).all()} if author_ids else {}

        lines = ["**Content Analytics**\n", "**Documents by Status:**"]
        for status, cnt in status_counts:
            s_val = status.value if status else "N/A"
            lines.append(f"- {s_val}: {cnt}")

        lines.append("\n**Top Authors:**")
        for aid, cnt in top_authors:
            lines.append(f"- {authors.get(aid, f'User #{aid}')}: {cnt} documents")

        return {"success": True, "result": "\n".join(lines)}
