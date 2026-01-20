"""Attachments API Routes"""
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile, status, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.schemas import (
    AttachmentResponse,
    AttachmentUploadResponse,
    MessageResponse,
)
from app.security import get_current_active_user, verify_token
from app.services.attachment_service import AttachmentService

router = APIRouter()


@router.get("/documents/{document_id}/attachments", response_model=List[AttachmentResponse])
def list_attachments(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all attachments for a document.
    """
    return AttachmentService.get_attachments(db, document_id, current_user)


@router.get("/documents/{document_id}/attachments/{attachment_id}", response_model=AttachmentResponse)
def get_attachment(
    document_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific attachment metadata.
    """
    return AttachmentService.get_attachment(db, document_id, attachment_id, current_user)


@router.get("/documents/{document_id}/attachments/{attachment_id}/download")
def download_attachment(
    document_id: int,
    attachment_id: int,
    token: Optional[str] = Query(None, description="JWT token for authentication (alternative to header)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Download an attachment file.
    """
    file_path, filename, mime_type = AttachmentService.get_file_path(
        db, document_id, attachment_id, current_user
    )
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=mime_type
    )


@router.post(
    "/documents/{document_id}/attachments",
    response_model=AttachmentUploadResponse,
    status_code=status.HTTP_201_CREATED
)
async def upload_attachment(
    document_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload a new attachment.

    Only admins and editors can upload attachments.
    Max file size: 10MB.
    Allowed types: PDF, Office docs, images, text files.
    """
    attachment = await AttachmentService.upload_attachment(
        db, document_id, file, current_user
    )
    return AttachmentUploadResponse(
        id=attachment.id,
        filename=attachment.original_filename,
        url=f"/api/v1/documents/{document_id}/attachments/{attachment.id}/download",
        message="File uploaded successfully"
    )


@router.delete(
    "/documents/{document_id}/attachments/{attachment_id}",
    response_model=MessageResponse
)
def delete_attachment(
    document_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete an attachment.

    Only admins can delete attachments.
    """
    AttachmentService.delete_attachment(db, document_id, attachment_id, current_user)
    return MessageResponse(message="Attachment deleted successfully")
