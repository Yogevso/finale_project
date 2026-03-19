"""Attachments API Routes"""

import hashlib
import hmac
import time
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
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.domain.specifications import ExternalEmbedPolicySpec, LinkSharingPolicySpec
from app.models import Document, User
from app.schemas import (
    AttachmentReaderViewResponse,
    AttachmentResponse,
    AttachmentUploadResponse,
    MessageResponse,
)
from app.security import get_current_active_user, verify_token
from app.services.attachment_service import AttachmentService
from app.utils.http_headers import build_content_disposition

router = APIRouter()

# AD-002: Signed download tickets replace raw JWT tokens in URLs.
_DOWNLOAD_TICKET_TTL_SECONDS = 300  # 5 minutes


def _sign_download_ticket(user_id: int, document_id: int, attachment_id: int, ts: int) -> str:
    """Create an HMAC-SHA256 signature for a download ticket."""
    msg = f"{user_id}:{document_id}:{attachment_id}:{ts}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()


def _verify_download_ticket(
    ticket: str, document_id: int, attachment_id: int, db: Session
) -> User:
    """Validate a signed download ticket and return the authenticated user."""
    try:
        parts = ticket.split(":")
        if len(parts) != 4:
            raise ValueError("malformed ticket")
        user_id_str, doc_id_str, att_id_str, ts_str = parts
        user_id = int(user_id_str)
        ticket_doc_id = int(doc_id_str)
        ticket_att_id = int(att_id_str)
        ts = int(ts_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid download ticket",
        ) from None

    if ticket_doc_id != document_id or ticket_att_id != attachment_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid download ticket",
        )

    if int(time.time()) - ts > _DOWNLOAD_TICKET_TTL_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Download ticket expired",
        )

    expected_sig = _sign_download_ticket(user_id, document_id, attachment_id, ts)
    provided_sig = _sign_download_ticket(user_id, ticket_doc_id, ticket_att_id, ts)
    if not hmac.compare_digest(expected_sig, provided_sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid download ticket",
        )

    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid download ticket",
        )
    return user


class DownloadTicketRequest(BaseModel):
    document_id: int
    attachment_id: int


class DownloadTicketResponse(BaseModel):
    ticket: str
    expires_in: int


@router.post("/attachments/download-ticket", response_model=DownloadTicketResponse)
def issue_download_ticket(
    body: DownloadTicketRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Issue a short-lived signed download ticket (AD-002).

    The ticket replaces passing raw JWT tokens as URL query parameters.
    """
    ts = int(time.time())
    sig = _sign_download_ticket(current_user.id, body.document_id, body.attachment_id, ts)
    ticket = f"{current_user.id}:{body.document_id}:{body.attachment_id}:{ts}"
    # Append HMAC so ticket is self-contained
    signed_ticket = f"{ticket}:{sig}"
    return DownloadTicketResponse(ticket=signed_ticket, expires_in=_DOWNLOAD_TICKET_TTL_SECONDS)


def _get_current_active_user_or_token(
    request: Request,
    token: Optional[str] = Query(
        None, description="Signed download ticket (preferred) or legacy JWT token"
    ),
    db: Session = Depends(get_db),
) -> User:
    """Authenticate via Authorization header, signed download ticket, or legacy JWT query param."""
    # 1. Prefer standard Authorization header
    auth_header = request.headers.get("authorization")
    bearer_token: Optional[str] = None
    if auth_header and auth_header.lower().startswith("bearer "):
        bearer_token = auth_header.split(" ", 1)[1].strip()

    if bearer_token:
        payload = verify_token(bearer_token)
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
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    # 2. Signed download ticket (AD-002 — preferred for URL-based access)
    if token and ":" in token:
        # Extract document_id and attachment_id from the URL path
        path = request.url.path
        path_parts = path.strip("/").split("/")
        # Expected path: .../documents/{doc_id}/attachments/{att_id}/...
        doc_id = att_id = None
        for i, part in enumerate(path_parts):
            if part == "documents" and i + 1 < len(path_parts):
                try:
                    doc_id = int(path_parts[i + 1])
                except (ValueError, IndexError):
                    pass
            if part == "attachments" and i + 1 < len(path_parts):
                try:
                    att_id = int(path_parts[i + 1])
                except (ValueError, IndexError):
                    pass
        if doc_id is not None and att_id is not None:
            return _verify_download_ticket(token, doc_id, att_id, db)

    # 3. Legacy JWT in query param (kept for backward compat, but discouraged)
    if token:
        payload = verify_token(token)
        if payload is not None:
            user_id = payload.get("sub")
            if user_id is not None:
                user = db.query(User).filter(User.id == int(user_id)).first()
                if user and user.is_active:
                    return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


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
    Download the original attachment bytes.
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
    Get Reader View derived artifact for supported attachment types.
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
    Retry Reader View artifact generation for a supported attachment.
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
    Allowed types: Office docs, images, text files.
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
