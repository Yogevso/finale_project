"""Collaboration activity endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.collaboration.dependencies import get_session_manager
from app.collaboration.session_manager import SessionManager
from app.models import User
from app.security import get_current_active_user

router = APIRouter()


class ActivityLogRequest(BaseModel):
    """Request to log a collaboration activity."""

    document_id: int
    session_id: Optional[str] = None
    activity_type: str
    details: Optional[dict] = None


class ActivityResponse(BaseModel):
    """Single activity item."""

    id: int
    document_id: int
    user_id: int
    username: str
    activity_type: str
    details: Optional[dict] = None
    created_at: datetime


class ActivityFeedResponse(BaseModel):
    """Response containing activity feed."""

    document_id: int
    activities: list[ActivityResponse]
    total: int
    has_more: bool


@router.post("/collaboration/activity")
async def log_activity(
    request: ActivityLogRequest,
    current_user: User = Depends(get_current_active_user),
    session_manager: SessionManager = Depends(get_session_manager),
):
    """
    Log a collaboration activity.

    Used for tracking edits, cursor movements, and other activities.
    """
    return session_manager.log_activity(
        document_id=request.document_id,
        activity_type=request.activity_type,
        details=request.details,
        session_id=request.session_id,
        current_user=current_user,
    )


@router.get("/collaboration/documents/{document_id}/activity", response_model=ActivityFeedResponse)
async def get_activity_feed(
    document_id: int,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    session_manager: SessionManager = Depends(get_session_manager),
):
    """
    Get the activity feed for a document.

    Returns recent collaboration activities for display in the activity feed.
    """
    payload = session_manager.get_activity_feed(
        document_id=document_id,
        limit=limit,
        offset=offset,
        current_user=current_user,
    )
    return ActivityFeedResponse(
        document_id=payload["document_id"],
        activities=[ActivityResponse(**activity) for activity in payload["activities"]],
        total=payload["total"],
        has_more=payload["has_more"],
    )
