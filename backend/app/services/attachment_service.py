"""Attachment Service - Business logic for file attachments"""

import io
import logging
import os
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Attachment, Document, User, UserRole, Version, VersionBumpType

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
        "application/json",
        "text/markdown",
        "text/html",
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
    def _parse_semver(raw_value: Optional[str], fallback_version_number: int) -> Tuple[int, int, int]:
        if raw_value:
            parts = raw_value.strip().split(".")
            if len(parts) == 3 and all(part.isdigit() for part in parts):
                return int(parts[0]), int(parts[1]), int(parts[2])
        base = fallback_version_number if fallback_version_number > 0 else 1
        return base, 0, 0

    @staticmethod
    def _next_patch_semver(raw_value: Optional[str], fallback_version_number: int) -> str:
        major, minor, patch = AttachmentService._parse_semver(raw_value, fallback_version_number)
        return f"{major}.{minor}.{patch + 1}"

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
        db: Session,
        document_id: int,
        file: UploadFile,
        current_user: User,
        *,
        convert_to_html: bool = True,
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

        # Validate file type (allow octet-stream if extension is supported)
        content_type = file.content_type or "application/octet-stream"
        original_filename = file.filename or "unnamed"
        file_ext = Path(original_filename).suffix.lower()
        allowed_extensions = {".pdf", ".doc", ".docx", ".txt", ".md", ".html", ".htm", ".json"}

        if content_type not in AttachmentService.ALLOWED_TYPES and file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed: {content_type}",
            )

        # Read file content
        content = await file.read()
        attachment = AttachmentService.create_attachment_from_bytes(
            db=db,
            document_id=document_id,
            content=content,
            original_filename=original_filename,
            content_type=content_type,
            current_user=current_user,
            convert_to_html=convert_to_html,
        )
        
        # Convert document to HTML and create initial version
        return attachment

    @staticmethod
    def create_attachment_from_bytes(
        db: Session,
        document_id: int,
        content: bytes,
        original_filename: str,
        content_type: str,
        current_user: User,
        *,
        convert_to_html: bool = False,
    ) -> Attachment:
        """Create attachment from raw bytes (optional HTML conversion)."""
        # Validate file size
        file_size = len(content)
        if file_size > AttachmentService.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Max size: {AttachmentService.MAX_FILE_SIZE // (1024 * 1024)}MB",
            )

        # Generate unique filename
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

        if convert_to_html:
            try:
                from app.utils.document_converter import convert_document_to_html
                
                html_content = convert_document_to_html(content, content_type, original_filename)
                
                if html_content:
                    existing_version = (
                        db.query(Version)
                        .filter(Version.document_id == document_id)
                        .order_by(Version.version_number.desc())
                        .first()
                    )
                    next_version = (existing_version.version_number + 1) if existing_version else 1
                    next_semantic = (
                        "1.0.0"
                        if not existing_version
                        else AttachmentService._next_patch_semver(
                            existing_version.semantic_version, existing_version.version_number
                        )
                    )
                    
                    version = Version(
                        document_id=document_id,
                        version_number=next_version,
                        semantic_version=next_semantic,
                        bump_type=VersionBumpType.PATCH if existing_version else VersionBumpType.MAJOR,
                        content=html_content,
                        changes_summary=f"Initial content from uploaded file: {original_filename}",
                        is_published=True,
                        published_at=attachment.uploaded_at,
                        published_by=current_user.id,
                        created_by=current_user.id,
                    )
                    db.add(version)
                    db.commit()
                    logger.info(f"Created initial version {next_version} for document {document_id}")
            except Exception as e:
                logger.error(f"Failed to convert document to HTML: {e}")

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
