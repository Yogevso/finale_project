"""Versions API Routes"""

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from app.application.commands.dependencies import get_publish_approved_version_command_handler
from app.application.commands.version_commands import (
    PublishApprovedVersionCommand,
    PublishApprovedVersionCommandErrorCode,
    PublishApprovedVersionCommandHandler,
)
from app.dependencies.services import get_version_service
from app.errors import (
    ConflictError,
    InvalidStateError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.dependencies.permissions import require_editor, require_manager, require_system_admin
from app.models import User
from app.schemas import (
    CancelScheduledPublishResponse,
    ForcePublishRequest,
    ForcePublishResponse,
    MessageResponse,
    PublishPreflightResponse,
    ScheduledPublishReport,
    SchedulePublishRequest,
    SchedulePublishResponse,
    VersionCreate,
    VersionListResponse,
    VersionResponse,
    VersionUpdate,
)
from app.services.version_service import VersionService

router = APIRouter()


@router.get("/documents/{document_id}/versions", response_model=VersionListResponse)
def list_versions(
    document_id: int,
    version_service: VersionService = Depends(get_version_service),
    current_user: User = Depends(require_editor),
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
    current_user: User = Depends(require_editor),
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
    current_user: User = Depends(require_editor),
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
    current_user: User = Depends(require_editor),
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


@router.get(
    "/documents/{document_id}/versions/{version_id}/publish/preflight",
    response_model=PublishPreflightResponse,
)
def publish_preflight(
    document_id: int,
    version_id: int,
    version_service: VersionService = Depends(get_version_service),
    current_user: User = Depends(require_editor),
):
    """
    Get a preflight checklist for publishing a version.

    Returns a list of checks that must pass before the version can be published:
    - version_exists: The version exists for the document
    - not_already_published: Version is not already published
    - user_can_publish: User has permission to publish
    - review_approved: The version has an approved review
    - audience_ready: Audience configuration is valid (company visibility requires assignments)
    """
    return version_service.publish_preflight_checks(document_id, version_id, current_user)


@router.post(
    "/documents/{document_id}/versions/{version_id}/publish", response_model=VersionResponse
)
def publish_version(
    document_id: int,
    version_id: int,
    response: Response,
    current_user: User = Depends(require_manager),
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
        if result.error.code == PublishApprovedVersionCommandErrorCode.VALIDATION:
            raise ValidationError(result.error.message)
        raise HTTPException(status_code=500, detail="Unexpected publish command error")
    response.headers["ETag"] = f"\"{result.value['etag']}\""
    return result.value


@router.post(
    "/documents/{document_id}/versions/{version_id}/force-publish",
    response_model=ForcePublishResponse,
)
def force_publish_version(
    document_id: int,
    version_id: int,
    data: ForcePublishRequest,
    version_service: VersionService = Depends(get_version_service),
    current_user: User = Depends(require_system_admin),
):
    """
    Force publish a version with admin override.

    This bypasses normal review requirements and creates an enhanced audit trail.
    Requires system_admin role and explicit acknowledgment of risks.

    Use cases:
    - Emergency fixes that must be published immediately
    - Documents that don't require review approval
    - Repairing stuck publishing workflows
    """
    return version_service.force_publish_version(
        document_id=document_id,
        version_id=version_id,
        current_user=current_user,
        reason=data.reason,
        acknowledge_risks=data.acknowledge_risks,
    )


@router.delete("/documents/{document_id}/versions/{version_id}", response_model=MessageResponse)
def delete_version(
    document_id: int,
    version_id: int,
    version_service: VersionService = Depends(get_version_service),
    current_user: User = Depends(require_editor),
):
    """
    Delete an unpublished version.

    Published versions cannot be deleted.
    Only admins can delete versions.
    """
    version_service.delete_version(document_id, version_id, current_user)
    return MessageResponse(message="Version deleted successfully")


@router.post(
    "/documents/{document_id}/versions/{version_id}/restore-audience",
)
def restore_audience_from_version(
    document_id: int,
    version_id: int,
    version_service: VersionService = Depends(get_version_service),
    current_user: User = Depends(require_editor),
):
    """
    Restore document audience state from a published version's snapshot.

    This provides rollback capability if audience settings were changed incorrectly
    after a version was published. Only admins can perform this operation.

    Returns the restored visibility and company IDs.
    """
    return version_service.restore_audience_from_version(document_id, version_id, current_user)


@router.post(
    "/documents/{document_id}/versions/{version_id}/schedule-publish",
    response_model=SchedulePublishResponse,
)
def schedule_publish(
    document_id: int,
    version_id: int,
    data: SchedulePublishRequest,
    version_service: VersionService = Depends(get_version_service),
    current_user: User = Depends(require_editor),
):
    """
    Schedule a version to be published at a specific future time.

    Audience is validated at schedule time and re-validated at publish time.
    Requires an approved review for the version.
    """
    try:
        return version_service.schedule_publish(
            document_id=document_id,
            version_id=version_id,
            scheduled_at=data.scheduled_publish_at,
            current_user=current_user,
        )
    except InvalidStateError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.delete(
    "/documents/{document_id}/versions/{version_id}/schedule-publish",
    response_model=CancelScheduledPublishResponse,
)
def cancel_scheduled_publish(
    document_id: int,
    version_id: int,
    version_service: VersionService = Depends(get_version_service),
    current_user: User = Depends(require_editor),
):
    """
    Cancel a scheduled publish for a version.
    """
    try:
        return version_service.cancel_scheduled_publish(
            document_id=document_id,
            version_id=version_id,
            current_user=current_user,
        )
    except InvalidStateError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/scheduled-publishes/process",
    response_model=ScheduledPublishReport,
)
def process_scheduled_publishes(
    batch_size: int = 10,
    version_service: VersionService = Depends(get_version_service),
    current_user: User = Depends(require_editor),
):
    """
    Process scheduled publishes that are due.

    This is an admin endpoint for manually triggering the scheduled publish processor.
    In production, this should be called by a background job.

    Re-validates audience before each publish and handles:
    - Audience drift since scheduling
    - Stale (deactivated) companies
    - Validation failures
    """
    from app.models import UserRole

    if current_user.role not in (UserRole.ADMIN, UserRole.SYSTEM_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can process scheduled publishes",
        )
    return version_service.process_scheduled_publishes(batch_size=batch_size)
