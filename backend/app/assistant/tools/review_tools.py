"""AI assistant tools for document review workflows."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.assistant.tools.base import BaseTool
from app.container import AppContainer
from app.models import AuditLog, ActionType, Document, ReviewRequest, ReviewStatus, User
from app.services.permissions import Permission

logger = logging.getLogger(__name__)


class SubmitReviewTool(BaseTool):
    name = "submit_review"
    description = "Submit a review decision (approve or reject) for a pending review request."
    parameters = {
        "type": "object",
        "properties": {
            "review_id": {"type": "integer", "description": "The review request ID"},
            "decision": {
                "type": "string",
                "description": "Review decision: 'approve' or 'reject'",
                "enum": ["approve", "reject"],
            },
            "comments": {"type": "string", "description": "Reviewer comments", "maxLength": 5000},
        },
        "required": ["review_id", "decision"],
    }
    required_role = "EDITOR"
    required_permission = Permission.APPROVE_REVIEW
    confirm_before_execute = True

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session,
    ) -> dict[str, Any]:
        review = (
            db.query(ReviewRequest)
            .filter(ReviewRequest.id == params["review_id"])
            .first()
        )
        if not review:
            return {"success": False, "result": "", "error": "Review request not found."}

        # Verify the user is the assigned reviewer
        if review.reviewed_by and review.reviewed_by != user.id:
            return {"success": False, "result": "", "error": "You are not the assigned reviewer."}

        if review.status != ReviewStatus.PENDING:
            return {
                "success": False,
                "result": "",
                "error": f"Review is already {review.status.value}, cannot modify.",
            }

        # Verify document access via tenant
        if tenant_id is not None:
            doc = db.query(Document).filter(
                Document.id == review.document_id,
                Document.tenant_id == tenant_id,
            ).first()
            if not doc:
                return {"success": False, "result": "", "error": "Document not found in your tenant."}

        decision = params["decision"]

        if decision == "approve":
            # AE-002: Route approval through ApproveReviewCommandHandler (same
            # pipeline the API uses) — enforces ReviewPolicy.can_approve_review(),
            # blocks self-approval, creates audit log + notification.
            from app.application.commands.review_commands import (
                ApproveReviewCommand,
            )

            container = AppContainer()
            handler = container.approve_review_command_handler(db)
            command = ApproveReviewCommand(
                review_id=review.id,
                comments=params.get("comments"),
                current_user=user,
            )
            result = handler.execute(command)
            if result.is_err:
                err = result.error
                return {"success": False, "result": "", "error": err.message}

            return {
                "success": True,
                "result": f"Review {review.id} has been **approved** for document ID {review.document_id}.",
            }
        else:
            # Reject path: enforce self-rejection block and create audit trail
            # AE-002: Block self-rejection (submitter == reviewer)
            if review.submitted_by == user.id:
                return {
                    "success": False,
                    "result": "",
                    "error": "You cannot reject your own submission.",
                }

            review.status = ReviewStatus.REJECTED
            review.reviewed_by = user.id
            review.reviewed_at = datetime.utcnow()
            if params.get("comments"):
                review.review_comments = params["comments"][:2000]

            # AE-005: Audit log for reject decision
            db.add(AuditLog(
                user_id=user.id,
                document_id=review.document_id,
                action=ActionType.UPDATE,
                details=f"Rejected review #{review.id} via AI assistant",
            ))
            db.commit()

            return {
                "success": True,
                "result": f"Review {review.id} has been **rejected** for document ID {review.document_id}.",
            }


class ListPendingReviewsTool(BaseTool):
    name = "list_pending_reviews"
    description = "List pending review requests assigned to the current user."
    parameters = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Max results (default 20)"},
        },
        "required": [],
    }
    required_role = "EDITOR"

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session,
    ) -> dict[str, Any]:
        limit = min(params.get("limit", 20), 50)
        reviews = (
            db.query(ReviewRequest)
            .filter(
                ReviewRequest.reviewed_by == user.id,
                ReviewRequest.status == ReviewStatus.PENDING,
            )
            .order_by(ReviewRequest.submitted_at.desc())
            .limit(limit)
            .all()
        )
        if not reviews:
            return {"success": True, "result": "No pending reviews assigned to you."}

        doc_ids = {r.document_id for r in reviews}
        submitter_ids = {r.submitted_by for r in reviews}
        docs = {d.id: d.title for d in db.query(Document).filter(Document.id.in_(doc_ids)).all()} if doc_ids else {}
        users = {u.id: u.full_name or u.email for u in db.query(User).filter(User.id.in_(submitter_ids)).all()} if submitter_ids else {}

        lines = [f"**Pending Reviews** ({len(reviews)})\n"]
        for r in reviews:
            title = docs.get(r.document_id, f"Doc {r.document_id}")
            submitter = users.get(r.submitted_by, "Unknown")
            date = r.submitted_at.strftime("%Y-%m-%d %H:%M") if r.submitted_at else "N/A"
            msg = f" — {r.message[:80]}" if r.message else ""
            lines.append(f"- **{title}** (Review #{r.id}) — by {submitter} on {date}{msg}")

        return {"success": True, "result": "\n".join(lines)}
