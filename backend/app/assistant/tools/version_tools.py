"""AI assistant tools for document version management."""

from __future__ import annotations

import difflib
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.assistant.rag.chunker import DocumentChunker
from app.assistant.tools.base import BaseTool
from app.container import AppContainer
from app.models import (
    AuditLog, ActionType, Document, ReviewRequest, User, UserRole, Version,
)
from app.services.permissions import Permission

logger = logging.getLogger(__name__)


def _check_doc_access(doc_id: int, tenant_id: int | None, db: Session) -> Document | None:
    q = db.query(Document).filter(Document.id == doc_id)
    if tenant_id is not None:
        q = q.filter(Document.tenant_id == tenant_id)
    return q.first()


class CompareVersionsTool(BaseTool):
    name = "compare_versions"
    description = (
        "Compare two versions of a document and show what changed. "
        "Uses a diff to describe the differences."
    )
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {"type": "integer", "description": "The document ID"},
            "version_1": {"type": "integer", "description": "First version number (older)"},
            "version_2": {"type": "integer", "description": "Second version number (newer, defaults to latest)"},
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

        versions = (
            db.query(Version)
            .filter(Version.document_id == doc_id)
            .order_by(Version.version_number)
            .all()
        )
        if len(versions) < 2:
            return {"success": False, "result": "", "error": "This document has fewer than 2 versions."}

        v1_num = params.get("version_1") or versions[0].version_number
        v2_num = params.get("version_2") or versions[-1].version_number

        v1 = next((v for v in versions if v.version_number == v1_num), None)
        v2 = next((v for v in versions if v.version_number == v2_num), None)

        if not v1 or not v2:
            avail = ", ".join(str(v.version_number) for v in versions)
            return {"success": False, "result": "", "error": f"Version not found. Available: {avail}"}

        text1 = DocumentChunker.strip_html(v1.content or "")
        text2 = DocumentChunker.strip_html(v2.content or "")

        diff = list(difflib.unified_diff(
            text1.splitlines(), text2.splitlines(),
            fromfile=f"v{v1_num}", tofile=f"v{v2_num}", lineterm="",
        ))

        additions = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
        deletions = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))

        diff_summary = "\n".join(diff[:80])
        result = (
            f"**Comparison: v{v1_num} → v{v2_num} of '{doc.title}'**\n\n"
            f"- Lines added: {additions}\n"
            f"- Lines removed: {deletions}\n\n"
            f"```diff\n{diff_summary}\n```"
        )
        return {"success": True, "result": result}


class GetDocumentHistoryTool(BaseTool):
    name = "get_document_history"
    description = (
        "Show the full version history of a document with timestamps, "
        "authors, and publishing status."
    )
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {"type": "integer", "description": "The document ID"},
            "limit": {"type": "integer", "description": "Max versions to return (default 10)"},
        },
        "required": ["document_id"],
    }
    required_role = "VIEWER"

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session,
    ) -> dict[str, Any]:
        doc_id = params["document_id"]
        limit = min(params.get("limit") or 10, 50)

        doc = _check_doc_access(doc_id, tenant_id, db)
        if not doc:
            return {"success": False, "result": "", "error": "Document not found or you don't have access."}

        versions = (
            db.query(Version)
            .filter(Version.document_id == doc_id)
            .order_by(Version.version_number.desc())
            .limit(limit)
            .all()
        )
        if not versions:
            return {"success": True, "result": f"No versions found for document '{doc.title}'."}

        user_ids = {v.created_by for v in versions if v.created_by}
        users = {u.id: u.full_name or u.email for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}

        lines = [f"**Version History: '{doc.title}'** ({len(versions)} versions)\n"]
        for v in versions:
            author = users.get(v.created_by, "Unknown")
            status = "Published" if v.is_published else "Draft"
            date = v.created_at.strftime("%Y-%m-%d %H:%M") if v.created_at else "N/A"
            sem = f" ({v.semantic_version})" if v.semantic_version else ""
            summary = f" — {v.changes_summary}" if v.changes_summary else ""
            lines.append(f"- **v{v.version_number}{sem}** | {status} | {author} | {date}{summary}")

        return {"success": True, "result": "\n".join(lines)}


class PublishDocumentTool(BaseTool):
    name = "publish_document"
    description = (
        "Publish a specific version of a document to make it visible. "
        "If no version_id is given, publishes the latest draft. "
        "Requires MANAGER role or above."
    )
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {"type": "integer", "description": "The document ID"},
            "version_id": {"type": "integer", "description": "Specific version ID to publish"},
        },
        "required": ["document_id"],
    }
    # AE-001: Publishing requires MANAGER+ (was EDITOR — privilege escalation fix)
    required_role = "MANAGER"
    required_permission = Permission.PUBLISH_DOCUMENT
    confirm_before_execute = True

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session,
    ) -> dict[str, Any]:
        doc_id = params["document_id"]
        doc = _check_doc_access(doc_id, tenant_id, db)
        if not doc:
            return {"success": False, "result": "", "error": "Document not found or you don't have access."}

        version_id = params.get("version_id")
        if not version_id:
            latest = (
                db.query(Version)
                .filter(Version.document_id == doc_id, Version.is_published == False)
                .order_by(Version.version_number.desc())
                .first()
            )
            if not latest:
                return {"success": False, "result": "", "error": "No unpublished versions found."}
            version_id = latest.id

        version = db.query(Version).filter(Version.id == version_id, Version.document_id == doc_id).first()
        if not version:
            return {"success": False, "result": "", "error": "Version not found."}
        if version.is_published:
            return {"success": True, "result": f"Version {version.version_number} is already published."}

        # AE-001: Route through PublishApprovedVersionCommandHandler (same pipeline
        # the API uses) — enforces review approval status, state machine checks,
        # and PUBLISH_DOCUMENT permission.  Replaces direct is_published = True.
        from app.application.commands.version_commands import (
            PublishApprovedVersionCommand,
            PublishApprovedVersionCommandErrorCode,
        )

        container = AppContainer()
        handler = container.publish_approved_version_command_handler(db)
        command = PublishApprovedVersionCommand(
            document_id=doc_id,
            version_id=version_id,
            current_user=user,
        )
        result = handler.execute(command)
        if result.is_err:
            err = result.error
            return {"success": False, "result": "", "error": err.message}

        return {"success": True, "result": f"Version {version.version_number} of '{doc.title}' has been published."}


class GetDocumentWorkflowTool(BaseTool):
    name = "get_document_workflow"
    description = (
        "Show the current review/approval workflow status of a document "
        "including pending reviews and reviewer feedback."
    )
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

        reviews = (
            db.query(ReviewRequest)
            .filter(ReviewRequest.document_id == doc_id)
            .order_by(ReviewRequest.submitted_at.desc())
            .limit(10)
            .all()
        )

        user_ids = set()
        for r in reviews:
            if r.submitted_by:
                user_ids.add(r.submitted_by)
            if r.reviewed_by:
                user_ids.add(r.reviewed_by)
        users = {u.id: u.full_name or u.email for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}

        lines = [
            f"**Workflow Status: '{doc.title}'**\n",
            f"Document Status: **{doc.status.value if doc.status else 'N/A'}**\n",
        ]

        if not reviews:
            lines.append("No review requests found.")
        else:
            lines.append(f"**Review Requests** ({len(reviews)}):\n")
            for r in reviews:
                submitter = users.get(r.submitted_by, "Unknown")
                reviewer = users.get(r.reviewed_by, "Unassigned") if r.reviewed_by else "Unassigned"
                status_icon = {"PENDING": "Pending", "APPROVED": "Approved", "REJECTED": "Rejected", "CANCELLED": "Cancelled"}.get(r.status.value, "Unknown")
                date = r.submitted_at.strftime("%Y-%m-%d %H:%M") if r.submitted_at else "N/A"
                line = f"- **{status_icon}** | Submitted by {submitter} -> {reviewer} | {date}"
                if r.review_comments:
                    line += f"\n  Comments: {r.review_comments[:200]}"
                lines.append(line)

        return {"success": True, "result": "\n".join(lines)}
