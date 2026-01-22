"""Attachment Service - Business logic for file attachments"""

import io
import logging
import os
import uuid
from pathlib import Path
from typing import List

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Attachment, Document, User, UserRole

logger = logging.getLogger(__name__)


def get_storage_backend():
    """Lazy import to avoid boto3 dependency when not using S3"""
    from app.services.storage_service import get_storage_backend as _get_backend

    return _get_backend()


class AttachmentService:
    """Service for managing file attachments"""

    # Allowed MIME types
    ALLOWED_TYPES = {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "text/plain",
        "text/csv",
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
    }

    # Max file size: 10MB
    MAX_FILE_SIZE = 10 * 1024 * 1024

    @staticmethod
    def get_upload_dir() -> Path:
        """Get upload directory path"""
        upload_dir = (
            Path(settings.UPLOAD_DIR) if hasattr(settings, "UPLOAD_DIR") else Path("data/uploads")
        )
        upload_dir.mkdir(parents=True, exist_ok=True)
        return upload_dir

    @staticmethod
    def get_attachments(db: Session, document_id: int, current_user: User) -> List[Attachment]:
        """Get all attachments for a document"""
        # Check document exists
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        return (
            db.query(Attachment)
            .filter(Attachment.document_id == document_id)
            .order_by(Attachment.uploaded_at.desc())
            .all()
        )

    @staticmethod
    def get_attachment(
        db: Session, document_id: int, attachment_id: int, current_user: User
    ) -> Attachment:
        """Get a specific attachment"""
        attachment = (
            db.query(Attachment)
            .filter(Attachment.id == attachment_id, Attachment.document_id == document_id)
            .first()
        )

        if not attachment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found"
            )

        return attachment

    @staticmethod
    async def upload_attachment(
        db: Session, document_id: int, file: UploadFile, current_user: User
    ) -> Attachment:
        """Upload a new attachment"""
        # Check document exists
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        # Only admin/editor/manager/system_admin can upload
        if current_user.role not in [
            UserRole.ADMIN,
            UserRole.EDITOR,
            UserRole.MANAGER,
            UserRole.SYSTEM_ADMIN,
        ]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins, managers and editors can upload attachments",
            )

        # Validate file type
        content_type = file.content_type or "application/octet-stream"
        if content_type not in AttachmentService.ALLOWED_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed: {content_type}",
            )

        # Read file content
        content = await file.read()
        file_size = len(content)

        # Validate file size
        if file_size > AttachmentService.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Max size: {AttachmentService.MAX_FILE_SIZE // (1024 * 1024)}MB",
            )

        # Generate unique filename
        original_filename = file.filename or "unnamed"
        file_ext = Path(original_filename).suffix
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"

        # Use storage backend (S3 or local)
        try:
            storage = get_storage_backend()
            file_stream = io.BytesIO(content)
            storage_key = storage.upload(
                file_stream, f"doc_{document_id}/{unique_filename}", content_type
            )
            storage_path = storage_key
            logger.info(f"Uploaded attachment to storage: {storage_key}")
        except Exception as e:
            logger.error(f"Storage upload failed: {e}")
            # Fallback to local file storage
            upload_dir = AttachmentService.get_upload_dir()
            doc_dir = upload_dir / str(document_id)
            doc_dir.mkdir(parents=True, exist_ok=True)
            file_path = doc_dir / unique_filename
            with open(file_path, "wb") as f:
                f.write(content)
            storage_path = str(file_path)

        # Create attachment record
        attachment = Attachment(
            document_id=document_id,
            filename=unique_filename,
            original_filename=original_filename,
            file_size=file_size,
            mime_type=content_type,
            storage_path=storage_path,
            uploaded_by=current_user.id,
        )

        db.add(attachment)
        db.commit()
        db.refresh(attachment)

        return attachment

    @staticmethod
    def delete_attachment(
        db: Session, document_id: int, attachment_id: int, current_user: User
    ) -> None:
        """Delete an attachment"""
        attachment = (
            db.query(Attachment)
            .filter(Attachment.id == attachment_id, Attachment.document_id == document_id)
            .first()
        )

        if not attachment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found"
            )

        # Only admin can delete
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can delete attachments"
            )

        # Delete file from storage
        try:
            storage = get_storage_backend()
            storage.delete(attachment.storage_path)
            logger.info(f"Deleted attachment from storage: {attachment.storage_path}")
        except Exception as e:
            logger.warning(f"Failed to delete from storage: {e}")
            # Try local file fallback
            try:
                if os.path.exists(attachment.storage_path):
                    os.remove(attachment.storage_path)
            except OSError:
                pass  # File may not exist

        # Delete record
        db.delete(attachment)
        db.commit()

    @staticmethod
    def get_file_path(
        db: Session, document_id: int, attachment_id: int, current_user: User
    ) -> tuple[str, str, str]:
        """Get file path for download - returns (path, filename, mime_type)"""
        attachment = AttachmentService.get_attachment(db, document_id, attachment_id, current_user)

        # Try the storage_path as-is first (might be a full path)
        if os.path.exists(attachment.storage_path):
            return attachment.storage_path, attachment.original_filename, attachment.mime_type

        # If not found, try resolving through the upload directory
        upload_dir = AttachmentService.get_upload_dir()

        # Try just the filename in uploads directory
        possible_path = upload_dir / attachment.storage_path
        if possible_path.exists():
            return str(possible_path), attachment.original_filename, attachment.mime_type

        # Try in document subdirectory
        doc_subdir = upload_dir / str(document_id) / attachment.storage_path
        if doc_subdir.exists():
            return str(doc_subdir), attachment.original_filename, attachment.mime_type

        # Try using the filename field
        possible_path = upload_dir / attachment.filename
        if possible_path.exists():
            return str(possible_path), attachment.original_filename, attachment.mime_type

        logger.error(f"File not found for attachment {attachment_id}: {attachment.storage_path}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")
