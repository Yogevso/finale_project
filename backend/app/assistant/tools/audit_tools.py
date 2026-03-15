"""AI assistant tools for audit log queries (admin only)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.assistant.tools.base import BaseTool
from app.models import AuditLog, User
from app.services.permissions import Permission

logger = logging.getLogger(__name__)


class SearchAuditLogsTool(BaseTool):
    name = "search_audit_logs"
    description = (
        "Search the audit log for actions by user, action type, or date range. "
        "Useful for compliance and tracking who did what."
    )
    parameters = {
        "type": "object",
        "properties": {
            "user_id": {"type": "integer", "description": "Filter by user ID"},
            "action_type": {"type": "string", "description": "Filter by action type"},
            "from_date": {"type": "string", "description": "Start date (ISO format, e.g. 2025-01-01)"},
            "to_date": {"type": "string", "description": "End date (ISO format)"},
            "limit": {"type": "integer", "description": "Max results (default 20)"},
        },
        "required": [],
    }
    required_permission = Permission.SYSTEM_SETTINGS

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session,
    ) -> dict[str, Any]:
        limit = min(params.get("limit", 20), 100)
        query = db.query(AuditLog).order_by(AuditLog.created_at.desc())

        if params.get("user_id"):
            query = query.filter(AuditLog.user_id == params["user_id"])
        if params.get("action_type"):
            query = query.filter(AuditLog.action == params["action_type"])
        if params.get("from_date"):
            try:
                query = query.filter(AuditLog.created_at >= datetime.fromisoformat(params["from_date"]))
            except ValueError:
                pass
        if params.get("to_date"):
            try:
                query = query.filter(AuditLog.created_at <= datetime.fromisoformat(params["to_date"]))
            except ValueError:
                pass

        logs = query.limit(limit).all()
        if not logs:
            return {"success": True, "result": "No audit logs found matching your criteria."}

        user_ids = {l.user_id for l in logs if l.user_id}
        users = {u.id: u.full_name or u.email for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}

        lines = [f"**Audit Logs** ({len(logs)} entries)\n"]
        for l in logs:
            who = users.get(l.user_id, f"User #{l.user_id}")
            action = l.action.value if hasattr(l.action, "value") else str(l.action)
            date = l.created_at.strftime("%Y-%m-%d %H:%M") if l.created_at else "N/A"
            details = str(l.details)[:100] if l.details else ""
            lines.append(f"- [{date}] **{who}** — {action}{f': {details}' if details else ''}")

        return {"success": True, "result": "\n".join(lines)}


class GetUserActivityTool(BaseTool):
    name = "get_user_activity"
    description = "Get recent activity for a specific user including actions and timestamps."
    parameters = {
        "type": "object",
        "properties": {
            "user_id": {"type": "integer", "description": "The user ID to look up"},
            "limit": {"type": "integer", "description": "Max results (default 20)"},
        },
        "required": ["user_id"],
    }
    required_permission = Permission.SYSTEM_SETTINGS

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session,
    ) -> dict[str, Any]:
        target_id = params["user_id"]
        limit = min(params.get("limit", 20), 100)

        target = db.query(User).filter(User.id == target_id).first()
        if not target:
            return {"success": False, "result": "", "error": "User not found."}

        name = target.full_name or target.email
        logs = (
            db.query(AuditLog)
            .filter(AuditLog.user_id == target_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .all()
        )

        lines = [f"**Activity for {name}** ({len(logs)} recent actions)\n"]
        for l in logs:
            action = l.action.value if hasattr(l.action, "value") else str(l.action)
            date = l.created_at.strftime("%Y-%m-%d %H:%M") if l.created_at else "N/A"
            details = str(l.details)[:100] if l.details else ""
            lines.append(f"- [{date}] {action}{f': {details}' if details else ''}")

        if not logs:
            lines.append("No recent activity found.")

        return {"success": True, "result": "\n".join(lines)}
