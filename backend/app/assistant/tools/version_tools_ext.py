"""Extended version tools — scheduled publishing, rollback, bulk operations."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.assistant.tools.base import BaseTool
from app.models import ActionType, AuditLog, Document, User, UserRole, Version
from app.services.permissions import Permission


class ListScheduledPublishesTool(BaseTool):
    name = "list_scheduled_publishes"
    description = "List document versions that are scheduled for future publishing."
    parameters = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Max results (default 20)"},
        },
        "required": [],
    }
    required_permission = Permission.PUBLISH_DOCUMENT

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        limit = min(params.get("limit", 20), 50)
        q = db.query(Version).filter(
            Version.scheduled_publish_at.isnot(None),
            Version.is_published.is_(False),
        )
        if tenant_id:
            q = q.join(Document).filter(Document.tenant_id == tenant_id)
        versions = q.order_by(Version.scheduled_publish_at).limit(limit).all()
        if not versions:
            return {"success": True, "result": "No scheduled publishes found."}
        lines = [f"{len(versions)} version(s) scheduled for publishing:"]
        for v in versions:
            doc = db.query(Document).filter(Document.id == v.document_id).first()
            title = doc.title if doc else f"Doc#{v.document_id}"
            lines.append(
                f"- [{v.id}] {title} v{v.semantic_version or v.version_number} "
                f"→ scheduled for {v.scheduled_publish_at:%Y-%m-%d %H:%M}"
            )
        return {"success": True, "result": "\n".join(lines)}


class GetVersionDetailsTool(BaseTool):
    name = "get_version_details"
    description = "Get detailed information about a specific document version."
    parameters = {
        "type": "object",
        "properties": {
            "version_id": {"type": "integer", "description": "The version ID"},
        },
        "required": ["version_id"],
    }
    required_permission = Permission.VIEW_INTERNAL_DOCS

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        v = db.query(Version).filter(Version.id == params["version_id"]).first()
        if not v:
            return {"success": False, "result": "Version not found."}
        # AE-006: Tenant isolation — prevent cross-tenant version reads
        doc = db.query(Document).filter(Document.id == v.document_id).first()
        if not doc:
            return {"success": False, "result": "Version not found."}
        if tenant_id is not None and doc.tenant_id != tenant_id:
            return {"success": False, "result": "Version not found."}
        title = doc.title
        creator = db.query(User).filter(User.id == v.created_by).first()
        creator_name = creator.full_name if creator else "Unknown"
        published_by = ""
        if v.published_by:
            pub_user = db.query(User).filter(User.id == v.published_by).first()
            published_by = f"\n- Published by: {pub_user.full_name if pub_user else 'Unknown'} at {v.published_at:%Y-%m-%d %H:%M}" if v.published_at else ""
        scheduled = f"\n- Scheduled publish: {v.scheduled_publish_at:%Y-%m-%d %H:%M}" if v.scheduled_publish_at else ""
        content_len = len(v.content) if v.content else 0
        return {
            "success": True,
            "result": (
                f"Version #{v.id} — {title}\n"
                f"- Version: {v.semantic_version or v.version_number} ({v.bump_type.value})\n"
                f"- Created by: {creator_name} on {v.created_at:%Y-%m-%d %H:%M}\n"
                f"- Published: {'Yes' if v.is_published else 'No'}{published_by}{scheduled}\n"
                f"- Content length: {content_len:,} chars\n"
                f"- Changes summary: {v.changes_summary or '(none)'}"
            ),
        }


class GetDocumentVersionStatsTool(BaseTool):
    name = "get_document_version_stats"
    description = "Get version statistics for a document — total versions, published count, latest version."
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {"type": "integer", "description": "Document ID"},
        },
        "required": ["document_id"],
    }
    required_permission = Permission.VIEW_INTERNAL_DOCS

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        doc_id = params["document_id"]
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return {"success": False, "result": f"Document {doc_id} not found."}
        # AE-006: Tenant isolation — prevent cross-tenant version stat reads
        if tenant_id is not None and doc.tenant_id != tenant_id:
            return {"success": False, "result": f"Document {doc_id} not found."}
        total = db.query(func.count(Version.id)).filter(Version.document_id == doc_id).scalar() or 0
        published = db.query(func.count(Version.id)).filter(
            Version.document_id == doc_id, Version.is_published.is_(True)
        ).scalar() or 0
        latest = (
            db.query(Version)
            .filter(Version.document_id == doc_id)
            .order_by(Version.version_number.desc())
            .first()
        )
        latest_info = f"v{latest.semantic_version or latest.version_number}" if latest else "none"
        scheduled = db.query(func.count(Version.id)).filter(
            Version.document_id == doc_id,
            Version.scheduled_publish_at.isnot(None),
            Version.is_published.is_(False),
        ).scalar() or 0
        return {
            "success": True,
            "result": (
                f"'{doc.title}' version stats:\n"
                f"- Total versions: {total}\n"
                f"- Published: {published}\n"
                f"- Latest: {latest_info}\n"
                f"- Scheduled for publish: {scheduled}"
            ),
        }


class CancelScheduledPublishTool(BaseTool):
    name = "cancel_scheduled_publish"
    description = "Cancel a scheduled publish for a version."
    parameters = {
        "type": "object",
        "properties": {
            "version_id": {"type": "integer", "description": "Version ID to cancel scheduled publish"},
        },
        "required": ["version_id"],
    }
    required_permission = Permission.PUBLISH_DOCUMENT
    confirm_before_execute = True

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        v = db.query(Version).filter(Version.id == params["version_id"]).first()
        if not v:
            return {"success": False, "result": "Version not found."}
        # AE-007: Tenant isolation — prevent cross-tenant scheduled publish cancellation
        doc = db.query(Document).filter(Document.id == v.document_id).first()
        if not doc:
            return {"success": False, "result": "Version not found."}
        if tenant_id is not None and doc.tenant_id != tenant_id:
            return {"success": False, "result": "Version not found."}
        if not v.scheduled_publish_at:
            return {"success": True, "result": "This version has no scheduled publish date."}
        if v.is_published:
            return {"success": False, "result": "This version is already published."}
        v.scheduled_publish_at = None
        # AE-005: Audit trail for AI-initiated scheduled publish cancellation
        db.add(AuditLog(
            user_id=user.id,
            document_id=v.document_id,
            action=ActionType.UPDATE,
            details=f"Cancelled scheduled publish for version #{v.id} via AI assistant",
        ))
        db.commit()
        return {"success": True, "result": f"Scheduled publish cancelled for version #{v.id}."}


class ListUnpublishedVersionsTool(BaseTool):
    name = "list_unpublished_versions"
    description = "List draft (unpublished) versions across documents."
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {"type": "integer", "description": "Filter to a specific document (optional)"},
            "limit": {"type": "integer", "description": "Max results (default 20)"},
        },
        "required": [],
    }
    required_permission = Permission.VIEW_INTERNAL_DOCS

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        limit = min(params.get("limit", 20), 50)
        q = db.query(Version).filter(Version.is_published.is_(False))
        if params.get("document_id"):
            q = q.filter(Version.document_id == params["document_id"])
        elif tenant_id:
            q = q.join(Document).filter(Document.tenant_id == tenant_id)
        versions = q.order_by(Version.created_at.desc()).limit(limit).all()
        if not versions:
            return {"success": True, "result": "No unpublished versions found."}
        lines = [f"{len(versions)} unpublished version(s):"]
        for v in versions:
            doc = db.query(Document).filter(Document.id == v.document_id).first()
            title = doc.title if doc else f"Doc#{v.document_id}"
            sched = f" (scheduled: {v.scheduled_publish_at:%Y-%m-%d})" if v.scheduled_publish_at else ""
            lines.append(f"- [{v.id}] {title} v{v.semantic_version or v.version_number}{sched}")
        return {"success": True, "result": "\n".join(lines)}
