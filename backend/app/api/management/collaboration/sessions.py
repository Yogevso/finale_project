"""Collaboration session endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.collaboration.dependencies import get_session_manager
from app.collaboration.session_manager import SessionManager
from app.models import User
from app.observability import UseCaseTimer
from app.security import get_current_active_user
from .telemetry import record_collaboration_telemetry

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
    session_manager: SessionManager = Depends(get_session_manager),
):
    """
    Start a new collaboration session.

    Called when a user joins a document for collaborative editing.
    """
    timer = UseCaseTimer.start()
    outcome = "failure"
    error_type: str | None = None
    try:
        payload = session_manager.start_collaboration_session(
            document_id=request.document_id,
            current_user=current_user,
        )
        outcome = "success"
        return SessionStartResponse(
            session_id=payload["session_id"],
            document_id=payload["document_id"],
            started_at=payload["started_at"],
        )
    except Exception as exc:  # policy: BOUNDARY — route telemetry must capture failures before re-raising
        error_type = type(exc).__name__
        raise
    finally:
        record_collaboration_telemetry(
            use_case_name="start_collaboration_session",
            timer=timer,
            outcome=outcome,
            error_type=error_type,
        )


@router.post("/collaboration/sessions/end")
async def end_collaboration_session(
    request: SessionEndRequest,
    current_user: User = Depends(get_current_active_user),
    session_manager: SessionManager = Depends(get_session_manager),
):
    """
    End a collaboration session.

    Called when a user leaves a document or disconnects.
    """
    timer = UseCaseTimer.start()
    outcome = "failure"
    error_type: str | None = None
    try:
        payload = session_manager.end_collaboration_session(
            session_id=request.session_id,
            edits_count=request.edits_count,
            current_user=current_user,
        )
        outcome = "success"
        return payload
    except Exception as exc:  # policy: BOUNDARY — route telemetry must capture failures before re-raising
        error_type = type(exc).__name__
        raise
    finally:
        record_collaboration_telemetry(
            use_case_name="end_collaboration_session",
            timer=timer,
            outcome=outcome,
            error_type=error_type,
        )


@router.get("/collaboration/documents/{document_id}/sessions")
async def get_active_sessions(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    session_manager: SessionManager = Depends(get_session_manager),
):
    """
    Get active collaboration sessions for a document.

    Returns all currently active sessions (users editing the document).
    """
    payload = session_manager.get_active_sessions(
        document_id=document_id,
        current_user=current_user,
    )
    return {
        "document_id": payload["document_id"],
        "sessions": [ActiveSessionResponse(**session) for session in payload["sessions"]],
        "count": payload["count"],
    }
