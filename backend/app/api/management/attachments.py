"""Attachments API Routes"""

from typing import List, Optional

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
from app.domain.specifications import ExternalEmbedPolicySpec, LinkSharingPolicySpec
from app.models import Document, User
from app.schemas import (
    AttachmentOutlineResponse,
    AttachmentReaderViewResponse,
    AttachmentResponse,
    AttachmentUploadResponse,
    MessageResponse,
)
from app.security import get_current_active_user, verify_token
from app.services.attachment_service import AttachmentService
from app.utils.http_headers import build_content_disposition

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


def _audience_headers_for_document(db: Session, document_id: int) -> dict[str, str]:
    """Return embed/sharing policy headers based on the document's visibility."""
    doc = db.query(Document).filter_by(id=document_id).first()
    if not doc:
        return {}
    embed = ExternalEmbedPolicySpec.for_document(doc)
    sharing = LinkSharingPolicySpec.for_document(doc)
    return {
        "X-Frame-Options": embed.x_frame_options_header,
        "X-Sharing-Policy": ",".join(sorted(a.value for a in sharing.allowed_actions)),
    }


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
        "Content-Disposition": build_content_disposition(filename, inline=inline),
        **_audience_headers_for_document(db, document_id),
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


def _stream_preview_pdf(
    db: Session,
    document_id: int,
    attachment_id: int,
    current_user: User,
    *,
    inline: bool = True,
) -> StreamingResponse:
    attachment, content_stream, media_type, content_length = AttachmentService.open_preview_stream(
        db, document_id, attachment_id, current_user
    )
    original_name = attachment.original_filename or attachment.filename or "preview"
    if "." in original_name:
        base_name = original_name.rsplit(".", 1)[0]
    else:
        base_name = original_name
    preview_filename = f"{base_name}.pdf"

    headers = {
        "Content-Disposition": build_content_disposition(preview_filename, inline=inline),
        "Content-Length": str(content_length),
        **_audience_headers_for_document(db, document_id),
    }
    if attachment.preview_pdf_sha256:
        headers["X-Preview-SHA256"] = attachment.preview_pdf_sha256

    return StreamingResponse(content=content_stream, media_type=media_type, headers=headers)


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
    Download preview PDF rendition for an attachment.
    """
    return _stream_preview_pdf(db, document_id, attachment_id, current_user, inline=False)


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
    Stream preview PDF artifact bytes with inline content disposition.
    """
    return _stream_preview_pdf(db, document_id, attachment_id, current_user)


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
