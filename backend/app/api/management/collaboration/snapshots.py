"""Collaboration snapshot endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.collaboration.dependencies import get_snapshot_manager
from app.collaboration.snapshot_manager import SnapshotManager
from app.models import User
from app.security import get_current_active_user

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


@router.post("/collaboration/documents/{document_id}/snapshots", response_model=SnapshotResponse)
async def create_snapshot(
    document_id: int,
    request: SnapshotCreateRequest,
    current_user: User = Depends(get_current_active_user),
    snapshot_manager: SnapshotManager = Depends(get_snapshot_manager),
):
    payload = snapshot_manager.create_snapshot(
        document_id=document_id,
        current_user=current_user,
        name=request.name,
        description=request.description,
        session_id=request.session_id,
    )
    return SnapshotResponse(**payload)


@router.get("/collaboration/documents/{document_id}/snapshots", response_model=SnapshotListResponse)
async def list_snapshots(
    document_id: int,
    limit: int = 50,
    offset: int = 0,
    include_expired: bool = False,
    current_user: User = Depends(get_current_active_user),
    snapshot_manager: SnapshotManager = Depends(get_snapshot_manager),
):
    payload = snapshot_manager.list_snapshots(
        document_id=document_id,
        current_user=current_user,
        limit=limit,
        offset=offset,
        include_expired=include_expired,
    )
    return SnapshotListResponse(
        document_id=payload["document_id"],
        snapshots=[SnapshotResponse(**snapshot) for snapshot in payload["snapshots"]],
        total=payload["total"],
        has_more=payload["has_more"],
    )


@router.get(
    "/collaboration/documents/{document_id}/snapshots/{snapshot_id}",
    response_model=SnapshotResponse,
)
async def get_snapshot(
    document_id: int,
    snapshot_id: int,
    current_user: User = Depends(get_current_active_user),
    snapshot_manager: SnapshotManager = Depends(get_snapshot_manager),
):
    payload = snapshot_manager.get_snapshot(
        document_id=document_id,
        snapshot_id=snapshot_id,
        current_user=current_user,
    )
    return SnapshotResponse(**payload)


@router.post("/collaboration/documents/{document_id}/snapshots/{snapshot_id}/restore")
async def restore_snapshot(
    document_id: int,
    snapshot_id: int,
    request: SnapshotRestoreRequest,
    current_user: User = Depends(get_current_active_user),
    snapshot_manager: SnapshotManager = Depends(get_snapshot_manager),
):
    return snapshot_manager.restore_snapshot(
        document_id=document_id,
        snapshot_id=snapshot_id,
        session_id=request.session_id,
        current_user=current_user,
    )


@router.patch(
    "/collaboration/documents/{document_id}/snapshots/{snapshot_id}",
    response_model=SnapshotResponse,
)
async def update_snapshot(
    document_id: int,
    snapshot_id: int,
    request: SnapshotUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    snapshot_manager: SnapshotManager = Depends(get_snapshot_manager),
):
    payload = snapshot_manager.update_snapshot(
        document_id=document_id,
        snapshot_id=snapshot_id,
        current_user=current_user,
        name=request.name,
        description=request.description,
        is_pinned=request.is_pinned,
    )
    return SnapshotResponse(**payload)


@router.delete("/collaboration/documents/{document_id}/snapshots/{snapshot_id}")
async def delete_snapshot(
    document_id: int,
    snapshot_id: int,
    current_user: User = Depends(get_current_active_user),
    snapshot_manager: SnapshotManager = Depends(get_snapshot_manager),
):
    return snapshot_manager.delete_snapshot(
        document_id=document_id,
        snapshot_id=snapshot_id,
        current_user=current_user,
    )


@router.post("/collaboration/documents/{document_id}/auto-snapshot")
async def create_auto_snapshot(
    document_id: int,
    session_id: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    snapshot_manager: SnapshotManager = Depends(get_snapshot_manager),
):
    return snapshot_manager.create_auto_snapshot(
        document_id=document_id,
        session_id=session_id,
        current_user=current_user,
    )
