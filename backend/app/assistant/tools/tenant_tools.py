"""Tenant management tools — SYSTEM_ADMIN only."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.assistant.tools.base import BaseTool
from app.models import ActionType, AuditLog, Tenant, User, UserRole


class ListTenantsTool(BaseTool):
    name = "list_tenants"
    description = "List all tenants (organisations) with their status."
    parameters = {
        "type": "object",
        "properties": {
            "is_active": {"type": "boolean", "description": "Filter by active status"},
            "limit": {"type": "integer", "description": "Max results (default 50)"},
        },
        "required": [],
    }
    required_role = UserRole.SYSTEM_ADMIN

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        query = db.query(Tenant)
        if params.get("is_active") is not None:
            query = query.filter(Tenant.is_active == params["is_active"])
        tenants = query.order_by(Tenant.id).limit(min(params.get("limit", 50), 200)).all()
        if not tenants:
            return {"success": True, "result": "No tenants found."}
        lines = [f"{len(tenants)} tenant(s):"]
        for t in tenants:
            status = "active" if t.is_active else "inactive"
            lines.append(f"- [{t.id}] {t.name} (slug: {t.slug}, type: {t.company_type}, {status})")
        return {"success": True, "result": "\n".join(lines)}


class GetTenantTool(BaseTool):
    name = "get_tenant"
    description = "Get detailed information about a specific tenant."
    parameters = {
        "type": "object",
        "properties": {
            "tenant_id": {"type": "integer", "description": "The tenant ID"},
        },
        "required": ["tenant_id"],
    }
    required_role = UserRole.SYSTEM_ADMIN

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        t = db.query(Tenant).filter(Tenant.id == params["tenant_id"]).first()
        if t is None:
            return {"success": False, "result": "", "error": "Tenant not found."}
        user_count = db.query(User).filter(User.tenant_id == t.id).count()
        info = (
            f"Name: {t.name}\n"
            f"Slug: {t.slug}\n"
            f"Active: {t.is_active}\n"
            f"Type: {t.company_type}\n"
            f"Contact: {t.contact_email or 'not set'}\n"
            f"Users: {user_count}\n"
            f"Created: {t.created_at}"
        )
        return {"success": True, "result": info}


class UpdateTenantTool(BaseTool):
    name = "update_tenant"
    description = "Update a tenant's name, contact email, or settings."
    parameters = {
        "type": "object",
        "properties": {
            "tenant_id": {"type": "integer", "description": "The tenant ID"},
            "name": {"type": "string", "description": "New tenant name (optional)", "maxLength": 255},
            "contact_email": {"type": "string", "description": "New contact email (optional)", "maxLength": 255},
            "is_active": {"type": "boolean", "description": "Activate or deactivate (optional)"},
        },
        "required": ["tenant_id"],
    }
    required_role = UserRole.SYSTEM_ADMIN
    confirm_before_execute = True

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        t = db.query(Tenant).filter(Tenant.id == params["tenant_id"]).first()
        if t is None:
            return {"success": False, "result": "", "error": "Tenant not found."}
        changes: list[str] = []
        if "name" in params:
            t.name = params["name"]
            changes.append(f"name → '{params['name']}'")
        if "contact_email" in params:
            t.contact_email = params["contact_email"]
            changes.append(f"contact_email → '{params['contact_email']}'")
        if "is_active" in params:
            t.is_active = params["is_active"]
            changes.append(f"is_active → {params['is_active']}")
        if not changes:
            return {"success": True, "result": "No changes specified."}
        # AE-005: Audit trail for AI-initiated tenant updates
        db.add(AuditLog(
            user_id=user.id,
            action=ActionType.UPDATE,
            details=f"Updated tenant '{t.name}' (ID: {t.id}): {', '.join(changes)} via AI assistant",
        ))
        db.commit()
        return {"success": True, "result": f"Tenant '{t.name}' updated: {', '.join(changes)}."}
