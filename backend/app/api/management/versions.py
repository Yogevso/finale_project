"""Versions API Routes"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.schemas import (
    MessageResponse,
    VersionCreate,
    VersionListResponse,
    VersionResponse,
    VersionUpdate,
)
from app.security import get_current_active_user
from app.services.version_service import VersionService

router = APIRouter()


@router.get("/documents/{document_id}/versions", response_model=VersionListResponse)
def list_versions(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all versions for a document.
    """
    versions = VersionService.get_versions(db, document_id, current_user)
    return VersionListResponse(items=versions, total=len(versions))


@router.get("/documents/{document_id}/versions/{version_id}", response_model=VersionResponse)
def get_version(
    document_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific version.
    """
    return VersionService.get_version(db, document_id, version_id, current_user)


@router.post(
    "/documents/{document_id}/versions",
    response_model=VersionResponse,
    status_code=status.HTTP_201_CREATED
)
def create_version(
    document_id: int,
    version_data: VersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new version for a document.

    Only admins and editors can create versions.
    """
    return VersionService.create_version(db, document_id, version_data, current_user)


@router.patch("/documents/{document_id}/versions/{version_id}", response_model=VersionResponse)
def update_version(
    document_id: int,
    version_id: int,
    version_data: VersionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update an unpublished version.

    Published versions are immutable and cannot be modified.
    """
    return VersionService.update_version(db, document_id, version_id, version_data, current_user)


@router.post("/documents/{document_id}/versions/{version_id}/publish", response_model=VersionResponse)
def publish_version(
    document_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Publish a version.

    Published versions become immutable and cannot be modified or deleted.
    Only admins can publish versions.
    """
    return VersionService.publish_version(db, document_id, version_id, current_user)


@router.delete(
    "/documents/{document_id}/versions/{version_id}",
    response_model=MessageResponse
)
def delete_version(
    document_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete an unpublished version.

    Published versions cannot be deleted.
    Only admins can delete versions.
    """
    VersionService.delete_version(db, document_id, version_id, current_user)
    return MessageResponse(message="Version deleted successfully")
