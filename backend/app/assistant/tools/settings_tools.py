"""Settings, announcements, and topic management tools."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.assistant.tools.base import BaseTool
from app.models import ActionType, Announcement, SystemSetting, Topic, User
from app.services.audit_helper import write_audit_log
from app.services.permissions import Permission


class GetSiteSettingsTool(BaseTool):
    name = "get_site_settings"
    description = "Get current site-level settings (key-value pairs)."
    parameters = {"type": "object", "properties": {}, "required": []}
    required_permission = Permission.SYSTEM_SETTINGS

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        rows = db.query(SystemSetting).all()
        if not rows:
            return {"success": True, "result": "No site settings configured."}
        lines = ["Current site settings:"]
        for r in rows:
            lines.append(f"- {r.key} = {r.value}")
        return {"success": True, "result": "\n".join(lines)}


class UpdateSiteSettingTool(BaseTool):
    name = "update_site_setting"
    description = "Create or update a site-level setting by key."
    parameters = {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Setting key", "maxLength": 255},
            "value": {"type": "string", "description": "Setting value", "maxLength": 2000},
        },
        "required": ["key", "value"],
    }
    required_permission = Permission.SYSTEM_SETTINGS

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        row = db.query(SystemSetting).filter(SystemSetting.key == params["key"]).first()
        if row:
            row.value = params["value"]
            row.updated_by = user.id
        else:
            row = SystemSetting(key=params["key"], value=params["value"], updated_by=user.id)
            db.add(row)
        # AE-005: Audit trail for AI-initiated setting changes
        write_audit_log(
            user_id=user.id,
            action=ActionType.UPDATE,
            details=f"Updated site setting '{params['key']}' via AI assistant",
        )
        db.commit()
        return {"success": True, "result": f"Setting '{params['key']}' set to '{params['value']}'."}


class CreateAnnouncementTool(BaseTool):
    name = "create_announcement"
    description = "Create a platform-wide announcement visible to all users."
    parameters = {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Announcement message text", "maxLength": 2000},
            "type": {
                "type": "string",
                "description": "Announcement type (default: info)",
                "enum": ["info", "warning", "success", "error"],
            },
        },
        "required": ["message"],
    }
    required_permission = Permission.SYSTEM_SETTINGS

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        ann = Announcement(
            message=params["message"],
            type=params.get("type", "info"),
            active=True,
            created_by=user.id,
        )
        db.add(ann)
        # AE-005: Audit trail for AI-initiated announcement creation
        write_audit_log(
            user_id=user.id,
            action=ActionType.CREATE,
            details=f"Created announcement via AI assistant: {params['message'][:100]}",
        )
        db.commit()
        db.refresh(ann)
        return {"success": True, "result": f"Announcement created (ID: {ann.id})."}


class ListAnnouncementsTool(BaseTool):
    name = "list_announcements"
    description = "List current active announcements."
    parameters = {"type": "object", "properties": {}, "required": []}
    required_permission = Permission.SYSTEM_SETTINGS

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        anns = db.query(Announcement).filter(Announcement.active.is_(True)).all()
        if not anns:
            return {"success": True, "result": "No active announcements."}
        lines = [f"{len(anns)} active announcement(s):"]
        for a in anns:
            lines.append(f"- [{a.id}] ({a.type}) {a.message}")
        return {"success": True, "result": "\n".join(lines)}


class ListTopicsTool(BaseTool):
    name = "list_topics"
    description = "List all document topics/categories."
    parameters = {"type": "object", "properties": {}, "required": []}
    required_permission = Permission.VIEW_INTERNAL_DOCS

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        topics = db.query(Topic).order_by(Topic.name).all()
        if not topics:
            return {"success": True, "result": "No topics configured."}
        lines = [f"{len(topics)} topic(s):"]
        for t in topics:
            lines.append(f"- {t.name} (slug: {t.slug})")
        return {"success": True, "result": "\n".join(lines)}


class CreateTopicTool(BaseTool):
    name = "create_topic"
    description = "Create a new document topic/category."
    parameters = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Topic name", "maxLength": 255},
            "slug": {"type": "string", "description": "URL-friendly slug (optional, auto-generated)", "maxLength": 100},
            "description": {"type": "string", "description": "Topic description (optional)", "maxLength": 1000},
        },
        "required": ["name"],
    }
    required_permission = Permission.SYSTEM_SETTINGS

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        slug = params.get("slug") or params["name"].lower().replace(" ", "-")
        if db.query(Topic).filter(Topic.slug == slug).first():
            return {"success": False, "result": "", "error": f"Topic with slug '{slug}' already exists."}

        topic = Topic(name=params["name"], slug=slug, description=params.get("description"))
        db.add(topic)
        # AE-005: Audit trail for AI-initiated topic creation
        write_audit_log(
            user_id=user.id,
            action=ActionType.CREATE,
            details=f"Created topic '{params['name']}' (slug: {slug}) via AI assistant",
        )
        db.commit()
        db.refresh(topic)
        return {"success": True, "result": f"Topic '{topic.name}' created (slug: {topic.slug})."}
