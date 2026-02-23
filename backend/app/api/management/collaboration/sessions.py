"""Collaboration session endpoints."""

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    ActionType,
    AuditLog,
    CollaborationActivity,
    CollaborationActivityType,
    CollaborationSession,
    Document,
    User,
)
from app.security import get_current_active_user
from app.services.collaboration_service import CollaborationService

router = APIRouter()


class SessionStartRequest(BaseModel):
    """Request to start a collaboration session."""

    document_id: int


class SessionStartResponse(BaseModel):
    """Response after starting a session."""

    session_id: str
    document_id: int
    started_at: datetime


class SessionEndRequest(BaseModel):
    """Request to end a collaboration session."""

    session_id: str
    edits_count: int = 0


class ActiveSessionResponse(BaseModel):
    """Active session information."""

    session_id: str
    user_id: int
    username: str
    started_at: datetime
    last_activity_at: datetime
    edits_count: int


@router.post("/collaboration/sessions/start", response_model=SessionStartResponse)
async def start_collaboration_session(
    request: SessionStartRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Start a new collaboration session.

    Called when a user joins a document for collaborative editing.
    """
    # Get the document
    document = db.query(Document).filter(Document.id == request.document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Check permissions
    permissions = CollaborationService.get_user_permissions(current_user, document)
    if not permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this document",
        )

    # Generate session ID
    session_id = f"collab_{current_user.id}_{request.document_id}_{uuid.uuid4().hex[:8]}"

    # Create session record
    session = CollaborationSession(
        document_id=request.document_id,
        user_id=current_user.id,
        session_id=session_id,
        started_at=datetime.utcnow(),
        is_active=True,
        edits_count=0,
        last_activity_at=datetime.utcnow(),
    )
    db.add(session)

    # Log activity
    activity = CollaborationActivity(
        document_id=request.document_id,
        user_id=current_user.id,
        session_id=session_id,
        activity_type=CollaborationActivityType.USER_JOINED,
        details=json.dumps({"username": current_user.username}),
    )
    db.add(activity)

    # Create audit log entry
    audit_log = AuditLog(
        user_id=current_user.id,
        document_id=request.document_id,
        action=ActionType.VIEW,
        details=f"Started collaboration session: {session_id}",
    )
    db.add(audit_log)

    db.commit()

    return SessionStartResponse(
        session_id=session_id,
        document_id=request.document_id,
        started_at=session.started_at,
    )


@router.post("/collaboration/sessions/end")
async def end_collaboration_session(
    request: SessionEndRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    End a collaboration session.

    Called when a user leaves a document or disconnects.
    """
    # Find the session
    session = (
        db.query(CollaborationSession)
        .filter(
            CollaborationSession.session_id == request.session_id,
            CollaborationSession.user_id == current_user.id,
            CollaborationSession.is_active.is_(True),
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Active session not found"
        )

    # Update session
    session.ended_at = datetime.utcnow()
    session.is_active = False
    session.edits_count = request.edits_count

    # Log activity
    activity = CollaborationActivity(
        document_id=session.document_id,
        user_id=current_user.id,
        session_id=request.session_id,
        activity_type=CollaborationActivityType.USER_LEFT,
        details=json.dumps(
            {
                "username": current_user.username,
                "duration_seconds": int((session.ended_at - session.started_at).total_seconds()),
                "edits_count": request.edits_count,
            }
        ),
    )
    db.add(activity)

    db.commit()

    return {"message": "Session ended successfully", "session_id": request.session_id}


@router.get("/collaboration/documents/{document_id}/sessions")
async def get_active_sessions(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get active collaboration sessions for a document.

    Returns all currently active sessions (users editing the document).
    """
    # Get the document
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Check permissions
    permissions = CollaborationService.get_user_permissions(current_user, document)
    if not permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this document",
        )

    # Query active sessions
    sessions = (
        db.query(CollaborationSession)
        .filter(
            CollaborationSession.document_id == document_id,
            CollaborationSession.is_active.is_(True),
        )
        .all()
    )
    session_user_ids = list({session.user_id for session in sessions})
    user_map = {}
    if session_user_ids:
        user_rows = db.query(User.id, User.username).filter(User.id.in_(session_user_ids)).all()
        user_map = {user_id: username for user_id, username in user_rows}

    # Build response
    session_responses = []
    for session in sessions:
        session_responses.append(
            ActiveSessionResponse(
                session_id=session.session_id,
                user_id=session.user_id,
                username=user_map.get(session.user_id, "Unknown"),
                started_at=session.started_at,
                last_activity_at=session.last_activity_at,
                edits_count=session.edits_count,
            )
        )

    return {
        "document_id": document_id,
        "sessions": session_responses,
        "count": len(session_responses),
    }
