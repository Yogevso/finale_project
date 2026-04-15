"""Collaboration session and activity manager."""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.collaboration.base import CollaborationManagerBase
from app.errors import NotFoundError, PermissionDeniedError, ValidationError
from app.models import (
    ActionType,
    CollaborationActivity,
    CollaborationActivityType,
    CollaborationSession,
    User,
)
from app.repositories import UserRepository
from app.services.audit_helper import write_audit_log


class SessionManager(CollaborationManagerBase):
    """Manages collaboration sessions and activity feeds."""

    def __init__(self, db: Session, **kwargs) -> None:
        super().__init__(db, **kwargs)
        self.user_repository = UserRepository(db)

    def start_collaboration_session(
        self, *, document_id: int, current_user: User
    ) -> dict[str, object]:
        document = self.get_document_or_404(document_id)
        self.ensure_document_read_access(document=document, current_user=current_user)

        session_id = f"collab_{current_user.id}_{document_id}_{uuid.uuid4().hex[:8]}"
        session = CollaborationSession(
            document_id=document_id,
            user_id=current_user.id,
            session_id=session_id,
            started_at=datetime.utcnow(),
            is_active=True,
            edits_count=0,
            last_activity_at=datetime.utcnow(),
        )
        self.chat_db.add(session)

        activity = CollaborationActivity(
            document_id=document_id,
            user_id=current_user.id,
            session_id=session_id,
            activity_type=CollaborationActivityType.USER_JOINED,
            details=json.dumps({"username": current_user.username}),
        )
        self.chat_db.add(activity)

        write_audit_log(
            user_id=current_user.id,
            document_id=document_id,
            action=ActionType.VIEW,
            details=f"Started collaboration session: {session_id}",
        )
        self.chat_db.commit()

        return {
            "session_id": session_id,
            "document_id": document_id,
            "started_at": session.started_at,
        }

    def end_collaboration_session(
        self, *, session_id: str, edits_count: int, current_user: User
    ) -> dict[str, str]:
        session = (
            self.chat_db.query(CollaborationSession)
            .filter(
                CollaborationSession.session_id == session_id,
                CollaborationSession.user_id == current_user.id,
                CollaborationSession.is_active.is_(True),
            )
            .first()
        )
        if not session:
            raise NotFoundError("Active session not found")

        session.ended_at = datetime.utcnow()
        session.is_active = False
        session.edits_count = edits_count

        activity = CollaborationActivity(
            document_id=session.document_id,
            user_id=current_user.id,
            session_id=session_id,
            activity_type=CollaborationActivityType.USER_LEFT,
            details=json.dumps(
                {
                    "username": current_user.username,
                    "duration_seconds": int(
                        (session.ended_at - session.started_at).total_seconds()
                    ),
                    "edits_count": edits_count,
                }
            ),
        )
        self.chat_db.add(activity)
        self.chat_db.commit()

        return {"message": "Session ended successfully", "session_id": session_id}

    def get_active_sessions(self, *, document_id: int, current_user: User) -> dict[str, object]:
        document = self.get_document_or_404(document_id)
        self.ensure_document_read_access(document=document, current_user=current_user)

        sessions = (
            self.chat_db.query(CollaborationSession)
            .filter(
                CollaborationSession.document_id == document_id,
                CollaborationSession.is_active.is_(True),
            )
            .all()
        )
        session_user_ids = list({session.user_id for session in sessions})
        user_map = {
            user.id: user.username for user in self.user_repository.list_by_ids(session_user_ids)
        }

        payload_sessions = [
            {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "username": user_map.get(session.user_id, "Unknown"),
                "started_at": session.started_at,
                "last_activity_at": session.last_activity_at,
                "edits_count": session.edits_count,
            }
            for session in sessions
        ]

        return {
            "document_id": document_id,
            "sessions": payload_sessions,
            "count": len(payload_sessions),
        }

    def log_activity(
        self,
        *,
        document_id: int,
        activity_type: str,
        details: dict | None,
        session_id: str | None,
        current_user: User,
    ) -> dict[str, object]:
        try:
            normalized_activity_type = CollaborationActivityType(activity_type)
        except ValueError as err:
            raise ValidationError(f"Invalid activity type: {activity_type}") from err

        document = self.get_document_or_404(document_id)
        self.ensure_document_read_access(document=document, current_user=current_user)

        session = None
        if session_id:
            session = (
                self.chat_db.query(CollaborationSession)
                .filter(CollaborationSession.session_id == session_id)
                .first()
            )
            if not session or not session.is_active:
                raise NotFoundError("Active session not found")
            if session.user_id != current_user.id:
                raise PermissionDeniedError("You don't have permission to use this session")
            if session.document_id != document_id:
                raise ValidationError("Session does not belong to the specified document")

        activity = CollaborationActivity(
            document_id=document_id,
            user_id=current_user.id,
            session_id=session_id,
            activity_type=normalized_activity_type,
            details=json.dumps(details) if details else None,
        )
        self.chat_db.add(activity)

        if session:
            session.last_activity_at = datetime.utcnow()
            if normalized_activity_type == CollaborationActivityType.CONTENT_EDITED:
                session.edits_count += 1

        self.chat_db.commit()
        return {"message": "Activity logged", "id": activity.id}

    def get_activity_feed(
        self,
        *,
        document_id: int,
        limit: int,
        offset: int,
        current_user: User,
    ) -> dict[str, object]:
        document = self.get_document_or_404(document_id)
        self.ensure_document_read_access(document=document, current_user=current_user)

        query = (
            self.chat_db.query(CollaborationActivity)
            .filter(CollaborationActivity.document_id == document_id)
            .order_by(CollaborationActivity.created_at.desc())
        )

        total = query.count()
        activities = query.offset(offset).limit(limit).all()
        user_ids = list({activity.user_id for activity in activities})
        user_map = {user.id: user.username for user in self.user_repository.list_by_ids(user_ids)}

        payload_activities: list[dict[str, object]] = []
        for activity in activities:
            parsed_details = None
            if activity.details:
                try:
                    parsed_details = json.loads(activity.details)
                except json.JSONDecodeError:
                    parsed_details = {"raw": activity.details}

            payload_activities.append(
                {
                    "id": activity.id,
                    "document_id": activity.document_id,
                    "user_id": activity.user_id,
                    "username": user_map.get(activity.user_id, "Unknown"),
                    "activity_type": activity.activity_type.value,
                    "details": parsed_details,
                    "created_at": activity.created_at,
                }
            )

        return {
            "document_id": document_id,
            "activities": payload_activities,
            "total": total,
            "has_more": offset + limit < total,
        }
