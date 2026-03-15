"""AI assistant tools for user notifications."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.assistant.tools.base import BaseTool
from app.models import Notification, User

logger = logging.getLogger(__name__)


class GetMyNotificationsTool(BaseTool):
    name = "get_my_notifications"
    description = "List your recent notifications including mentions, review requests, and system alerts."
    parameters = {
        "type": "object",
        "properties": {
            "unread_only": {"type": "boolean", "description": "Only show unread (default false)"},
            "limit": {"type": "integer", "description": "Max results (default 20)"},
        },
        "required": [],
    }

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session,
    ) -> dict[str, Any]:
        limit = min(params.get("limit", 20), 100)
        query = db.query(Notification).filter(Notification.user_id == user.id)

        if params.get("unread_only"):
            query = query.filter(Notification.is_read == False)

        notifs = query.order_by(Notification.created_at.desc()).limit(limit).all()

        if not notifs:
            msg = "No unread notifications." if params.get("unread_only") else "No notifications."
            return {"success": True, "result": msg}

        unread = sum(1 for n in notifs if not n.is_read)
        lines = [f"**Your Notifications** ({len(notifs)} shown, {unread} unread)\n"]
        for n in notifs:
            read_mark = "" if n.is_read else "[NEW] "
            ntype = n.type.value if hasattr(n.type, "value") else str(n.type)
            date = n.created_at.strftime("%Y-%m-%d %H:%M") if n.created_at else "N/A"
            title = n.title or ntype
            lines.append(f"- {read_mark}**{title}** (ID: {n.id}) | {date}")
            if n.message:
                lines.append(f"  {n.message[:150]}")

        return {"success": True, "result": "\n".join(lines)}


class MarkNotificationsReadTool(BaseTool):
    name = "mark_notifications_read"
    description = "Mark one or more notifications as read."
    parameters = {
        "type": "object",
        "properties": {
            "notification_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "List of notification IDs to mark as read",
            },
            "mark_all": {"type": "boolean", "description": "Mark all as read (default false)"},
        },
        "required": [],
    }

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session,
    ) -> dict[str, Any]:
        now = datetime.utcnow()
        ids = params.get("notification_ids")
        mark_all = params.get("mark_all", False)

        query = db.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.is_read == False,
        )

        if not mark_all and ids:
            query = query.filter(Notification.id.in_(ids))
        elif not mark_all:
            return {"success": False, "result": "", "error": "Provide notification_ids or set mark_all=true."}

        count = 0
        for n in query.all():
            n.is_read = True
            n.read_at = now
            count += 1

        db.commit()
        return {"success": True, "result": f"Marked {count} notification(s) as read."}
