"""Attachments API Routes"""

from typing import List, Optional
from urllib.parse import quote

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.schemas import (
    AttachmentOutlineResponse,
    AttachmentReaderViewResponse,
    AttachmentResponse,
    AttachmentUploadResponse,
    MessageResponse,
)
from app.security import get_current_active_user, verify_token
from app.services.attachment_service import AttachmentService

router = APIRouter()


def _get_current_active_user_or_token(
    request: Request,
    token: Optional[str] = Query(
        None, description="JWT token for authentication (alternative to Authorization header)"
    ),
    db: Session = Depends(get_db),
) -> User:
    auth_header = request.headers.get("authorization")
    bearer_token: Optional[str] = None
    if auth_header and auth_header.lower().startswith("bearer "):
        bearer_token = auth_header.split(" ", 1)[1].strip()

    resolved_token = bearer_token or token
    if not resolved_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(resolved_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user = db.query(User).filter(User.id == user_id_int).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    return user


def _build_content_disposition(filename: str, inline: bool = False) -> str:
    disposition_type = "inline" if inline else "attachment"
    safe_filename = filename.replace('"', "").replace("\\", "_") or "download"
    utf8_filename = quote(filename or "download")
    return (
        f'{disposition_type}; filename="{safe_filename}"; '
        f"filename*=UTF-8''{utf8_filename}"
    )


def _stream_original_attachment(
    db: Session,
    document_id: int,
    attachment_id: int,
    current_user: User,
    *,
    inline: bool = False,
) -> StreamingResponse:
    attachment, content_stream = AttachmentService.open_original_stream(
        db, document_id, attachment_id, current_user
    )
    filename = attachment.original_filename or attachment.filename or "download"
    headers = {
        "Content-Disposition": _build_content_disposition(filename, inline=inline),
    }
    size_bytes = attachment.size_bytes or attachment.file_size
    if size_bytes is not None:
        headers["Content-Length"] = str(size_bytes)
    if attachment.sha256:
        headers["X-Checksum-SHA256"] = attachment.sha256

    return StreamingResponse(
        content=content_stream,
        media_type=attachment.mime_type or "application/octet-stream",
        headers=headers,
    )


@router.get("/documents/{document_id}/attachments", response_model=List[AttachmentResponse])
def list_attachments(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    List all attachments for a document.
    """
    return AttachmentService.get_attachments(db, document_id, current_user)


@router.get(
    "/documents/{document_id}/attachments/{attachment_id}", response_model=AttachmentResponse
)
def get_attachment(
    document_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a specific attachment metadata.
    """
    return AttachmentService.get_attachment(db, document_id, attachment_id, current_user)


@router.get("/documents/{document_id}/attachments/{attachment_id}/download")
def download_attachment(
    document_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(_get_current_active_user_or_token),
):
    """
    Download an attachment file.
    """
    return _stream_original_attachment(db, document_id, attachment_id, current_user, inline=False)


@router.get("/documents/{document_id}/attachments/{attachment_id}/download-original")
def download_attachment_original(
    document_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(_get_current_active_user_or_token),
):
    """
    Download the exact original bytes as uploaded.
    """
    return _stream_original_attachment(db, document_id, attachment_id, current_user, inline=False)


@router.get("/documents/{document_id}/attachments/{attachment_id}/preview")
def preview_attachment(
    document_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(_get_current_active_user_or_token),
):
    """
    Stream the original bytes with inline content disposition for browser preview.
    """
    return _stream_original_attachment(db, document_id, attachment_id, current_user, inline=True)


@router.get(
    "/documents/{document_id}/attachments/{attachment_id}/outline",
    response_model=AttachmentOutlineResponse,
)
def get_attachment_outline(
    document_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(_get_current_active_user_or_token),
):
    """
    Return PDF outline/bookmarks for attachment TOC.
    """
    payload = AttachmentService.get_pdf_outline(
        db,
        document_id,
        attachment_id,
        current_user,
    )
    return AttachmentOutlineResponse(**payload)


@router.get(
    "/documents/{document_id}/attachments/{attachment_id}/reader-view",
    response_model=AttachmentReaderViewResponse,
)
def get_attachment_reader_view(
    document_id: int,
    attachment_id: int,
    background_tasks: BackgroundTasks,
    retry: bool = Query(False, description="Force regeneration when Reader View failed"),
    db: Session = Depends(get_db),
    current_user: User = Depends(_get_current_active_user_or_token),
):
    """
    Get Reader View derived artifact for PDF attachments.
    """
    payload = AttachmentService.get_reader_view(
        db,
        document_id,
        attachment_id,
        current_user,
        background_tasks=background_tasks,
        force_retry=retry,
    )
    return AttachmentReaderViewResponse(**payload)


@router.post(
    "/documents/{document_id}/attachments/{attachment_id}/reader-view/retry",
    response_model=AttachmentReaderViewResponse,
)
def retry_attachment_reader_view(
    document_id: int,
    attachment_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(_get_current_active_user_or_token),
):
    """
    Retry Reader View artifact generation for a PDF attachment.
    """
    payload = AttachmentService.retry_reader_view_generation(
        db,
        document_id,
        attachment_id,
        current_user,
        background_tasks=background_tasks,
    )
    return AttachmentReaderViewResponse(**payload)


@router.post(
    "/documents/{document_id}/attachments/{attachment_id}/reader-view/regenerate",
    response_model=AttachmentReaderViewResponse,
    include_in_schema=False,
)
def regenerate_attachment_reader_view(
    document_id: int,
    attachment_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(_get_current_active_user_or_token),
):
    """
    Backward-compatible alias for retry endpoint.
    """
    payload = AttachmentService.retry_reader_view_generation(
        db,
        document_id,
        attachment_id,
        current_user,
        background_tasks=background_tasks,
    )
    return AttachmentReaderViewResponse(**payload)


@router.get(
    "/documents/{document_id}/attachments/{attachment_id}/reader-view/status",
    response_model=AttachmentReaderViewResponse,
    include_in_schema=False,
)
def get_attachment_reader_view_status(
    document_id: int,
    attachment_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(_get_current_active_user_or_token),
):
    payload = AttachmentService.get_reader_view(
        db,
        document_id,
        attachment_id,
        current_user,
        background_tasks=background_tasks,
    )
    return AttachmentReaderViewResponse(**payload)


@router.post(
    "/documents/{document_id}/attachments",
    response_model=AttachmentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    document_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Upload a new attachment.

    Only admins and editors can upload attachments.
    Max file size: 10MB.
    Allowed types: PDF, Office docs, images, text files.
    """
    attachment = await AttachmentService.upload_attachment(
        db,
        document_id,
        file,
        current_user,
        background_tasks=background_tasks,
    )
    return AttachmentUploadResponse(
        id=attachment.id,
        filename=attachment.original_filename,
        sha256=attachment.sha256,
        url=f"/api/v1/documents/{document_id}/attachments/{attachment.id}/download",
        message="File uploaded successfully",
    )


@router.delete(
    "/documents/{document_id}/attachments/{attachment_id}", response_model=MessageResponse
)
def delete_attachment(
    document_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete an attachment.

    Only admins can delete attachments.
    """
    AttachmentService.delete_attachment(db, document_id, attachment_id, current_user)
    return MessageResponse(message="Attachment deleted successfully")
