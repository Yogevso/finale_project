"""Collaboration snapshot endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Document, SnapshotType, User
from app.security import get_current_active_user
from app.services.collaboration_service import CollaborationService
from app.services.snapshot_service import SnapshotService

router = APIRouter()


class SnapshotCreateRequest(BaseModel):
    """Request to create a snapshot."""

    name: Optional[str] = None
    description: Optional[str] = None
    session_id: Optional[str] = None


class SnapshotUpdateRequest(BaseModel):
    """Request to update snapshot metadata."""

    name: Optional[str] = None
    description: Optional[str] = None
    is_pinned: Optional[bool] = None


class SnapshotRestoreRequest(BaseModel):
    """Request to restore a snapshot."""

    session_id: Optional[str] = None


class SnapshotResponse(BaseModel):
    """Snapshot information."""

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
    """Response containing list of snapshots."""

    document_id: int
    snapshots: list[SnapshotResponse]
    total: int
    has_more: bool


def _batch_snapshot_creator_usernames(
    db: Session, snapshots: list
) -> dict[int, str]:
    creator_ids = {snapshot.created_by for snapshot in snapshots if snapshot.created_by}
    if not creator_ids:
        return {}
    rows = db.query(User.id, User.username).filter(User.id.in_(creator_ids)).all()
    return {row[0]: row[1] for row in rows}


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
    usernames_by_id = _batch_snapshot_creator_usernames(db, snapshots)
    snapshot_responses = []
    for snapshot in snapshots:
        snapshot_responses.append(
            SnapshotResponse(
                id=snapshot.id,
                document_id=snapshot.document_id,
                snapshot_type=snapshot.snapshot_type.value,
                name=snapshot.name,
                description=snapshot.description,
                state_size=snapshot.state_size,
                created_by=snapshot.created_by,
                created_by_username=usernames_by_id.get(snapshot.created_by),
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
