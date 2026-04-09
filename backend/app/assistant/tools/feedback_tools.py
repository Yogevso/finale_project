"""Feedback tools."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.assistant.tools.base import BaseTool
from app.models import Feedback, FeedbackStatus, FeedbackType, User
from app.services.permissions import Permission


class SubmitFeedbackTool(BaseTool):
    name = "submit_feedback"
    description = "Submit feedback on a document (rating 1-5 and optional comment)."
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {"type": "integer", "description": "The document ID"},
            "rating": {"type": "integer", "description": "Rating from 1 (poor) to 5 (excellent)"},
            "comment": {"type": "string", "description": "Optional comment", "maxLength": 2000},
        },
        "required": ["document_id", "rating"],
    }
    required_permission = Permission.SUBMIT_FEEDBACK

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        rating = max(1, min(5, params["rating"]))
        comment = (params.get("comment") or "").strip()
        fb = Feedback(
            user_id=user.id,
            document_id=params["document_id"],
            feedback_type=FeedbackType.OTHER,
            status=FeedbackStatus.PENDING,
            content=comment or "Feedback submitted",
            comment=comment or None,
            is_helpful=rating >= 4,
        )
        db.add(fb)
        db.commit()
        db.refresh(fb)
        return {"success": True, "result": f"Feedback submitted (ID: {fb.id}, rating: {rating}/5)."}


class GetMyFeedbackTool(BaseTool):
    name = "get_my_feedback"
    description = "List feedback you have submitted."
    parameters = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Max results (default 10)"},
        },
        "required": [],
    }
    required_permission = Permission.SUBMIT_FEEDBACK

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        fbs = (
            db.query(Feedback)
            .filter(Feedback.user_id == user.id)
            .order_by(Feedback.created_at.desc())
            .limit(min(params.get("limit", 10), 50))
            .all()
        )
        if not fbs:
            return {"success": True, "result": "You have not submitted any feedback."}
        lines = [f"{len(fbs)} feedback item(s):"]
        for f in fbs:
            lines.append(f"- [{f.id}] doc={f.document_id} type={f.feedback_type} status={f.status}")
        return {"success": True, "result": "\n".join(lines)}
