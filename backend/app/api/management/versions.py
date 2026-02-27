"""Versions API Routes"""

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from app.application.commands.dependencies import get_publish_approved_version_command_handler
from app.application.commands.version_commands import (
    PublishApprovedVersionCommand,
    PublishApprovedVersionCommandErrorCode,
    PublishApprovedVersionCommandHandler,
)
from app.dependencies.services import get_version_service
from app.errors import ConflictError, InvalidStateError, NotFoundError, PermissionDeniedError
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
    version_service: VersionService = Depends(get_version_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    List all versions for a document.
    """
    versions = version_service.get_versions(document_id, current_user)
    return VersionListResponse(items=versions, total=len(versions))


@router.get("/documents/{document_id}/versions/{version_id}", response_model=VersionResponse)
def get_version(
    document_id: int,
    version_id: int,
    response: Response,
    version_service: VersionService = Depends(get_version_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a specific version.
    """
    version = version_service.get_version(document_id, version_id, current_user)
    response.headers["ETag"] = f"\"{version['etag']}\""
    return version


@router.post(
    "/documents/{document_id}/versions",
    response_model=VersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_version(
    document_id: int,
    version_data: VersionCreate,
    response: Response,
    version_service: VersionService = Depends(get_version_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new version for a document.

    Only admins and editors can create versions.
    """
    version = version_service.create_version(document_id, version_data, current_user)
    response.headers["ETag"] = f"\"{version['etag']}\""
    return version


@router.patch("/documents/{document_id}/versions/{version_id}", response_model=VersionResponse)
def update_version(
    document_id: int,
    version_id: int,
    version_data: VersionUpdate,
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    version_service: VersionService = Depends(get_version_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update an unpublished version.

    Published versions are immutable and cannot be modified.
    """
    version = version_service.update_version(
        document_id,
        version_id,
        version_data,
        current_user,
        if_match=if_match,
    )
    response.headers["ETag"] = f"\"{version['etag']}\""
    return version


@router.post(
    "/documents/{document_id}/versions/{version_id}/publish", response_model=VersionResponse
)
def publish_version(
    document_id: int,
    version_id: int,
    response: Response,
    current_user: User = Depends(get_current_active_user),
    publish_approved_version_command_handler: PublishApprovedVersionCommandHandler = Depends(
        get_publish_approved_version_command_handler
    ),
):
    """
    Publish a version.

    Published versions become immutable and cannot be modified or deleted.
    Only admins can publish versions.
    """
    result = publish_approved_version_command_handler.execute(
        PublishApprovedVersionCommand(
            document_id=document_id,
            version_id=version_id,
            current_user=current_user,
        )
    )
    if result.is_err:
        if result.error.code == PublishApprovedVersionCommandErrorCode.NOT_FOUND:
            raise NotFoundError(result.error.message)
        if result.error.code == PublishApprovedVersionCommandErrorCode.PERMISSION_DENIED:
            raise PermissionDeniedError(result.error.message)
        if result.error.code == PublishApprovedVersionCommandErrorCode.INVALID_STATE:
            raise InvalidStateError(result.error.message)
        if result.error.code == PublishApprovedVersionCommandErrorCode.CONFLICT:
            raise ConflictError(result.error.message)
        raise HTTPException(status_code=500, detail="Unexpected publish command error")
    response.headers["ETag"] = f"\"{result.value['etag']}\""
    return result.value


@router.delete("/documents/{document_id}/versions/{version_id}", response_model=MessageResponse)
def delete_version(
    document_id: int,
    version_id: int,
    version_service: VersionService = Depends(get_version_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete an unpublished version.

    Published versions cannot be deleted.
    Only admins can delete versions.
    """
    version_service.delete_version(document_id, version_id, current_user)
    return MessageResponse(message="Version deleted successfully")
