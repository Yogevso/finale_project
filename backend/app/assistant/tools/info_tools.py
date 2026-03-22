"""General information tools — available to all authenticated users."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.assistant.tools.base import BaseTool
from app.models import Document, DocumentStatus, DocumentVisibility, User
from app.services.permissions import Permission, get_user_permissions


class GetMyProfileTool(BaseTool):
    name = "get_my_profile"
    description = "Get your own profile information including name, email, role, and tenant."
    parameters = {"type": "object", "properties": {}, "required": []}

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        info = (
            f"Username: {user.username}\n"
            f"Email: {user.email}\n"
            f"Full Name: {user.full_name}\n"
            f"Role: {user.role}\n"
            f"Tenant ID: {user.tenant_id}\n"
            f"Active: {user.is_active}"
        )
        return {"success": True, "result": info}


class GetMyPermissionsTool(BaseTool):
    name = "get_my_permissions"
    description = "List all permissions your current role grants you."
    parameters = {"type": "object", "properties": {}, "required": []}

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        perms = get_user_permissions(user)
        if not perms:
            return {"success": True, "result": "You have no special permissions."}
        lines = [f"Your role ({user.role}) grants {len(perms)} permission(s):"]
        for p in sorted(perms, key=lambda x: x.value):
            lines.append(f"- {p.value}")
        return {"success": True, "result": "\n".join(lines)}


class GetHelpTool(BaseTool):
    name = "get_help"
    description = "List all assistant tools available to you with their descriptions."
    parameters = {"type": "object", "properties": {}, "required": []}

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        from app.assistant.tools.registry import registry

        tools = registry.get_tools_for_user(user)
        if not tools:
            return {"success": True, "result": "No tools available."}
        lines = [f"You have access to {len(tools)} tool(s):"]
        for t in sorted(tools, key=lambda x: x.name):
            lines.append(f"- **{t.name}**: {t.description}")
        return {"success": True, "result": "\n".join(lines)}


class SearchPublicDocumentsTool(BaseTool):
    name = "search_public_documents"
    description = "Search documents you have access to (respects visibility rules)."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query", "maxLength": 500},
            "limit": {"type": "integer", "description": "Max results (default 10)"},
        },
        "required": ["query"],
    }

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        from app.models import UserRole, document_company_assignments

        q = params["query"].strip()
        limit = min(params.get("limit", 10), 50)

        # Split query into words so "API documentation" matches "API Reference Index"
        words = q.split()
        query = db.query(Document).filter(Document.status == DocumentStatus.ACTIVE)
        for word in words:
            pat = f"%{word}%"
            query = query.filter(
                (Document.title.ilike(pat))
                | (Document.description.ilike(pat))
                | (Document.tags.ilike(pat))
            )

        try:
            role = UserRole(user.role) if not isinstance(user.role, UserRole) else user.role
        except (ValueError, KeyError):
            return {"success": False, "result": "", "error": "Invalid user role."}
        if role == UserRole.CUSTOMER:
            # Customers see only PUBLIC docs or COMPANY docs assigned to their tenant
            query = query.filter(
                (Document.visibility == DocumentVisibility.PUBLIC)
                | (
                    (Document.visibility == DocumentVisibility.COMPANY)
                    & Document.assigned_companies.any(id=tenant_id)
                )
            )
        else:
            # Internal users see PUBLIC + INTERNAL + COMPANY within their tenant
            if tenant_id is not None:
                query = query.filter(
                    (Document.tenant_id == tenant_id)
                    | (Document.visibility == DocumentVisibility.PUBLIC)
                )

        docs = query.order_by(Document.updated_at.desc()).limit(limit).all()
        if not docs:
            return {"success": True, "result": f"No documents found matching '{q}'."}

        lines = [f"Found {len(docs)} document(s):"]
        for d in docs:
            lines.append(f"- [{d.id}] {d.title} ({d.visibility})")
        return {"success": True, "result": "\n".join(lines)}


class GetDocumentContentTool(BaseTool):
    name = "get_document_content"
    description = "Get the full content of a document you have permission to view."
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {"type": "integer", "description": "The document ID"},
        },
        "required": ["document_id"],
    }

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        from app.models import UserRole, Version

        doc = db.query(Document).filter(Document.id == params["document_id"]).first()
        if doc is None:
            return {"success": False, "result": "", "error": "Document not found."}

        # Visibility check
        try:
            role = UserRole(user.role) if not isinstance(user.role, UserRole) else user.role
        except (ValueError, KeyError):
            return {"success": False, "result": "", "error": "Invalid user role."}
        if role == UserRole.CUSTOMER:
            if doc.visibility == DocumentVisibility.INTERNAL:
                return {"success": False, "result": "", "error": "You do not have access to this document."}
            if doc.visibility == DocumentVisibility.COMPANY:
                if not any(c.id == tenant_id for c in doc.assigned_companies):
                    return {"success": False, "result": "", "error": "You do not have access to this document."}
        elif tenant_id is not None and doc.tenant_id != tenant_id:
            if doc.visibility != DocumentVisibility.PUBLIC:
                return {"success": False, "result": "", "error": "You do not have access to this document."}

        # Get latest version content
        version = (
            db.query(Version)
            .filter(Version.document_id == doc.id)
            .order_by(Version.created_at.desc())
            .first()
        )

        if version and version.content:
            from app.assistant.rag.chunker import DocumentChunker
            text = DocumentChunker.strip_html(version.content).strip()
            if not text:
                text = "(document contains only images or non-text content)"
        else:
            text = "(no content)"

        info = f"Title: {doc.title}\n\n{text}"
        # Truncate very long content
        if len(info) > 4000:
            info = info[:4000] + "\n\n... (truncated)"
        return {"success": True, "result": info}
