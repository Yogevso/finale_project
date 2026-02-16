"""Collaboration API Routes - Handles real-time document collaboration"""

import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
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
    SnapshotType,
    User,
)
from app.security import get_current_active_user
from app.services.collaboration_service import CollaborationService
from app.services.snapshot_service import SnapshotService

router = APIRouter()


# ========== Schemas ==========


class CollaboratorInfo(BaseModel):
    """Information about a collaborator"""

    user_id: int
    username: str
    color: str
    is_editing: bool = False


class CollaborationStatusResponse(BaseModel):
    """Response containing collaboration status for a document"""

    document_id: int
    active_collaborators: list[CollaboratorInfo]
    is_collaborative_mode: bool
    has_unsaved_changes: bool


# ========== Endpoints ==========
# Note: The /auth/collab-token endpoint is in auth.py (the canonical endpoint)


@router.get("/collaboration/documents/{document_id}/state")
async def get_document_state(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get the Yjs state for a document.

    This endpoint is called by the Hocuspocus server to load document state.
    Returns binary data (application/octet-stream).
    """
    # Get the document
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Check permissions
    permissions = CollaborationService.get_user_permissions(current_user, document)
    if "read" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this document",
        )

    # Get the state
    state = document.yjs_state
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No collaboration state exists for this document",
        )

    return Response(
        content=state,
        media_type="application/octet-stream",
    )


@router.put("/collaboration/documents/{document_id}/state")
async def save_document_state(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Save the Yjs state for a document.

    This endpoint is called by the Hocuspocus server to persist document state.
    Expects binary data (application/octet-stream).
    """
    # Get the document
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Check permissions
    permissions = CollaborationService.get_user_permissions(current_user, document)
    if "write" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this document",
        )

    # Read the binary state from request body
    state = await request.body()

    # Save the state
    success = CollaborationService.save_document_state(db, document_id, state)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save document state",
        )

    return {"message": "State saved successfully", "size": len(state)}


@router.delete("/collaboration/documents/{document_id}/state")
async def clear_document_state(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Clear the Yjs state for a document.

    This resets the document's collaboration state. Use with caution.
    """
    # Get the document
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Check permissions - only admins and managers can clear state
    permissions = CollaborationService.get_user_permissions(current_user, document)
    if "write" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to clear this document's state",
        )

    # Clear the state
    success = CollaborationService.clear_document_state(db, document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear document state",
        )

    return {"message": "State cleared successfully"}


@router.get(
    "/collaboration/documents/{document_id}/status", response_model=CollaborationStatusResponse
)
async def get_collaboration_status(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get the collaboration status for a document.

    Returns information about active collaborators and document state.
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

    # Get active collaborators (would query Hocuspocus in production)
    collaborators = CollaborationService.get_active_collaborators(document_id)

    return CollaborationStatusResponse(
        document_id=document_id,
        active_collaborators=[CollaboratorInfo(**c) for c in collaborators],
        is_collaborative_mode=document.yjs_state is not None,
        has_unsaved_changes=False,  # Would be tracked by Hocuspocus
    )


# ========== Activity Tracking Schemas ==========


class SessionStartRequest(BaseModel):
    """Request to start a collaboration session"""

    document_id: int


class SessionStartResponse(BaseModel):
    """Response after starting a session"""

    session_id: str
    document_id: int
    started_at: datetime


class SessionEndRequest(BaseModel):
    """Request to end a collaboration session"""

    session_id: str
    edits_count: int = 0


class ActivityLogRequest(BaseModel):
    """Request to log a collaboration activity"""

    document_id: int
    session_id: Optional[str] = None
    activity_type: str
    details: Optional[dict] = None


class ActivityResponse(BaseModel):
    """Single activity item"""

    id: int
    document_id: int
    user_id: int
    username: str
    activity_type: str
    details: Optional[dict] = None
    created_at: datetime


class ActivityFeedResponse(BaseModel):
    """Response containing activity feed"""

    document_id: int
    activities: list[ActivityResponse]
    total: int
    has_more: bool


class ActiveSessionResponse(BaseModel):
    """Active session information"""

    session_id: str
    user_id: int
    username: str
    started_at: datetime
    last_activity_at: datetime
    edits_count: int


# ========== Activity Tracking Endpoints ==========


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
    if request.session_id:
        session = (
            db.query(CollaborationSession)
            .filter(
                CollaborationSession.session_id == request.session_id,
                CollaborationSession.is_active.is_(True),
            )
            .first()
        )
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

    # Build response with usernames
    activity_responses = []
    for activity in activities:
        user = db.query(User).filter(User.id == activity.user_id).first()
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
                username=user.username if user else "Unknown",
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

    # Build response
    session_responses = []
    for session in sessions:
        user = db.query(User).filter(User.id == session.user_id).first()
        session_responses.append(
            ActiveSessionResponse(
                session_id=session.session_id,
                user_id=session.user_id,
                username=user.username if user else "Unknown",
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


# ========== Snapshot Schemas ==========


class SnapshotCreateRequest(BaseModel):
    """Request to create a snapshot"""

    name: Optional[str] = None
    description: Optional[str] = None
    session_id: Optional[str] = None


class SnapshotUpdateRequest(BaseModel):
    """Request to update snapshot metadata"""

    name: Optional[str] = None
    description: Optional[str] = None
    is_pinned: Optional[bool] = None


class SnapshotRestoreRequest(BaseModel):
    """Request to restore a snapshot"""

    session_id: Optional[str] = None


class SnapshotResponse(BaseModel):
    """Snapshot information"""

    id: int
    document_id: int
    snapshot_type: str
    name: Optional[str]
    description: Optional[str]
    state_size: int
    created_by: Optional[int]
    created_by_username: Optional[str]
    session_id: Optional[str]
    is_pinned: bool
    expires_at: Optional[datetime]
    created_at: datetime


class SnapshotListResponse(BaseModel):
    """Response containing list of snapshots"""

    document_id: int
    snapshots: list[SnapshotResponse]
    total: int
    has_more: bool


# ========== Snapshot Endpoints ==========


@router.post("/collaboration/documents/{document_id}/snapshots", response_model=SnapshotResponse)
async def create_snapshot(
    document_id: int,
    request: SnapshotCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a manual snapshot of the document's current state.

    Snapshots are point-in-time saves during collaboration.
    They are NOT the same as Versions (which are for releases).
    """
    # Get the document
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Check permissions
    permissions = CollaborationService.get_user_permissions(current_user, document)
    if "write" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to create snapshots for this document",
        )

    # Check if document has Yjs state
    if not document.yjs_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has no collaboration state to snapshot",
        )

    # Create the snapshot
    snapshot = SnapshotService.create_snapshot(
        db=db,
        document_id=document_id,
        snapshot_type=SnapshotType.MANUAL_SAVE,
        yjs_state=document.yjs_state,
        user_id=current_user.id,
        session_id=request.session_id,
        name=request.name,
        description=request.description,
    )

    return SnapshotResponse(
        id=snapshot.id,
        document_id=snapshot.document_id,
        snapshot_type=snapshot.snapshot_type.value,
        name=snapshot.name,
        description=snapshot.description,
        state_size=snapshot.state_size,
        created_by=snapshot.created_by,
        created_by_username=current_user.username,
        session_id=snapshot.session_id,
        is_pinned=snapshot.is_pinned,
        expires_at=snapshot.expires_at,
        created_at=snapshot.created_at,
    )


@router.get("/collaboration/documents/{document_id}/snapshots", response_model=SnapshotListResponse)
async def list_snapshots(
    document_id: int,
    limit: int = 50,
    offset: int = 0,
    include_expired: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List all snapshots for a document.
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

    # Get snapshots
    snapshots, total = SnapshotService.list_snapshots(
        db=db,
        document_id=document_id,
        include_expired=include_expired,
        limit=limit,
        offset=offset,
    )

    # Build response
    snapshot_responses = []
    for snapshot in snapshots:
        username = None
        if snapshot.created_by:
            user = db.query(User).filter(User.id == snapshot.created_by).first()
            username = user.username if user else None

        snapshot_responses.append(
            SnapshotResponse(
                id=snapshot.id,
                document_id=snapshot.document_id,
                snapshot_type=snapshot.snapshot_type.value,
                name=snapshot.name,
                description=snapshot.description,
                state_size=snapshot.state_size,
                created_by=snapshot.created_by,
                created_by_username=username,
                session_id=snapshot.session_id,
                is_pinned=snapshot.is_pinned,
                expires_at=snapshot.expires_at,
                created_at=snapshot.created_at,
            )
        )

    return SnapshotListResponse(
        document_id=document_id,
        snapshots=snapshot_responses,
        total=total,
        has_more=offset + limit < total,
    )


@router.get(
    "/collaboration/documents/{document_id}/snapshots/{snapshot_id}",
    response_model=SnapshotResponse,
)
async def get_snapshot(
    document_id: int,
    snapshot_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get details of a specific snapshot.
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

    # Get snapshot
    snapshot = SnapshotService.get_snapshot(db, snapshot_id)
    if not snapshot or snapshot.document_id != document_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")

    username = None
    if snapshot.created_by:
        user = db.query(User).filter(User.id == snapshot.created_by).first()
        username = user.username if user else None

    return SnapshotResponse(
        id=snapshot.id,
        document_id=snapshot.document_id,
        snapshot_type=snapshot.snapshot_type.value,
        name=snapshot.name,
        description=snapshot.description,
        state_size=snapshot.state_size,
        created_by=snapshot.created_by,
        created_by_username=username,
        session_id=snapshot.session_id,
        is_pinned=snapshot.is_pinned,
        expires_at=snapshot.expires_at,
        created_at=snapshot.created_at,
    )


@router.post("/collaboration/documents/{document_id}/snapshots/{snapshot_id}/restore")
async def restore_snapshot(
    document_id: int,
    snapshot_id: int,
    request: SnapshotRestoreRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Restore the document to a previous snapshot state.

    This will create a backup snapshot of the current state before restoring.
    Active collaborators will need to refresh to see the restored content.
    """
    # Get the document
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Check permissions - only users with write access can restore
    permissions = CollaborationService.get_user_permissions(current_user, document)
    if "write" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to restore snapshots for this document",
        )

    # Verify snapshot exists and belongs to this document
    snapshot = SnapshotService.get_snapshot(db, snapshot_id)
    if not snapshot or snapshot.document_id != document_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")

    # Restore the snapshot
    updated_document = SnapshotService.restore_snapshot(
        db=db,
        snapshot_id=snapshot_id,
        user_id=current_user.id,
        session_id=request.session_id,
    )

    if not updated_document:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to restore snapshot"
        )

    return {
        "message": "Snapshot restored successfully",
        "snapshot_id": snapshot_id,
        "snapshot_name": snapshot.name,
        "document_id": document_id,
    }


@router.patch(
    "/collaboration/documents/{document_id}/snapshots/{snapshot_id}",
    response_model=SnapshotResponse,
)
async def update_snapshot(
    document_id: int,
    snapshot_id: int,
    request: SnapshotUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update snapshot metadata (name, description, pinned status).
    """
    # Get the document
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Check permissions
    permissions = CollaborationService.get_user_permissions(current_user, document)
    if "write" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to modify snapshots for this document",
        )

    # Verify snapshot exists and belongs to this document
    snapshot = SnapshotService.get_snapshot(db, snapshot_id)
    if not snapshot or snapshot.document_id != document_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")

    # Update the snapshot
    updated_snapshot = SnapshotService.update_snapshot(
        db=db,
        snapshot_id=snapshot_id,
        name=request.name,
        description=request.description,
        is_pinned=request.is_pinned,
    )

    username = None
    if updated_snapshot.created_by:
        user = db.query(User).filter(User.id == updated_snapshot.created_by).first()
        username = user.username if user else None

    return SnapshotResponse(
        id=updated_snapshot.id,
        document_id=updated_snapshot.document_id,
        snapshot_type=updated_snapshot.snapshot_type.value,
        name=updated_snapshot.name,
        description=updated_snapshot.description,
        state_size=updated_snapshot.state_size,
        created_by=updated_snapshot.created_by,
        created_by_username=username,
        session_id=updated_snapshot.session_id,
        is_pinned=updated_snapshot.is_pinned,
        expires_at=updated_snapshot.expires_at,
        created_at=updated_snapshot.created_at,
    )


@router.delete("/collaboration/documents/{document_id}/snapshots/{snapshot_id}")
async def delete_snapshot(
    document_id: int,
    snapshot_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Delete a snapshot.
    """
    # Get the document
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Check permissions
    permissions = CollaborationService.get_user_permissions(current_user, document)
    if "write" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete snapshots for this document",
        )

    # Verify snapshot exists and belongs to this document
    snapshot = SnapshotService.get_snapshot(db, snapshot_id)
    if not snapshot or snapshot.document_id != document_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")

    # Delete the snapshot
    success = SnapshotService.delete_snapshot(db, snapshot_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete snapshot"
        )

    return {"message": "Snapshot deleted successfully", "snapshot_id": snapshot_id}


@router.post("/collaboration/documents/{document_id}/auto-snapshot")
async def create_auto_snapshot(
    document_id: int,
    session_id: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create an auto-save snapshot if enough time has passed since the last one.

    This endpoint is called periodically by the frontend during collaboration.
    Returns whether a snapshot was created.
    """
    # Get the document
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Check if document has Yjs state
    if not document.yjs_state:
        return {"created": False, "reason": "No collaboration state"}

    # Check if we should create an auto-save
    if not SnapshotService.should_auto_save(db, document_id):
        return {"created": False, "reason": "Too soon since last auto-save"}

    # Create the snapshot
    snapshot = SnapshotService.create_snapshot(
        db=db,
        document_id=document_id,
        snapshot_type=SnapshotType.AUTO_SAVE,
        yjs_state=document.yjs_state,
        user_id=current_user.id,
        session_id=session_id,
    )

    return {
        "created": True,
        "snapshot_id": snapshot.id,
        "snapshot_name": snapshot.name,
    }
