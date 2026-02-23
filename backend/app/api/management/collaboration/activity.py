"""Collaboration activity endpoints."""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    CollaborationActivity,
    CollaborationActivityType,
    CollaborationSession,
    Document,
    User,
)
from app.security import get_current_active_user
from app.services.collaboration_service import CollaborationService

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
    db: Session = Depends(get_db),
):
    """
    Log a collaboration activity.

    Used for tracking edits, cursor movements, and other activities.
    """
    # Validate activity type
    try:
        activity_type = CollaborationActivityType(request.activity_type)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid activity type: {request.activity_type}",
        ) from err

    # Ensure document exists and user can access it.
    document = db.query(Document).filter(Document.id == request.document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    permissions = CollaborationService.get_user_permissions(current_user, document)
    if not permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this document",
        )

    session = None
    if request.session_id:
        session = (
            db.query(CollaborationSession)
            .filter(CollaborationSession.session_id == request.session_id)
            .first()
        )
        if not session or not session.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active session not found",
            )
        if session.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to use this session",
            )
        if session.document_id != request.document_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session does not belong to the specified document",
            )

    # Create activity record
    activity = CollaborationActivity(
        document_id=request.document_id,
        user_id=current_user.id,
        session_id=request.session_id,
        activity_type=activity_type,
        details=json.dumps(request.details) if request.details else None,
    )
    db.add(activity)

    # Update session last activity timestamp if session exists
    if session:
        session.last_activity_at = datetime.utcnow()
        if activity_type == CollaborationActivityType.CONTENT_EDITED:
            session.edits_count += 1

    db.commit()

    return {"message": "Activity logged", "id": activity.id}


@router.get("/collaboration/documents/{document_id}/activity", response_model=ActivityFeedResponse)
async def get_activity_feed(
    document_id: int,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get the activity feed for a document.

    Returns recent collaboration activities for display in the activity feed.
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

    # Query activities
    query = (
        db.query(CollaborationActivity)
        .filter(CollaborationActivity.document_id == document_id)
        .order_by(CollaborationActivity.created_at.desc())
    )

    total = query.count()
    activities = query.offset(offset).limit(limit).all()
    user_ids = list({activity.user_id for activity in activities})
    user_map = {}
    if user_ids:
        user_rows = db.query(User.id, User.username).filter(User.id.in_(user_ids)).all()
        user_map = {user_id: username for user_id, username in user_rows}

    # Build response with usernames
    activity_responses = []
    for activity in activities:
        details = None
        if activity.details:
            try:
                details = json.loads(activity.details)
            except json.JSONDecodeError:
                details = {"raw": activity.details}

        activity_responses.append(
            ActivityResponse(
                id=activity.id,
                document_id=activity.document_id,
                user_id=activity.user_id,
                username=user_map.get(activity.user_id, "Unknown"),
                activity_type=activity.activity_type.value,
                details=details,
                created_at=activity.created_at,
            )
        )

    return ActivityFeedResponse(
        document_id=document_id,
        activities=activity_responses,
        total=total,
        has_more=offset + limit < total,
    )
