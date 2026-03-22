"""Upload/create workflows for attachments."""

from __future__ import annotations

import hashlib
import io
import logging
import uuid
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.legacy_wrappers import get_document_converter_wrapper
from app.models import Attachment, User, Version, VersionBumpType

from .common import AttachmentServiceCommonMixin, get_storage_backend

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Raised when storage operations fail and fallback is disabled."""


class AttachmentServiceUploadMixin(AttachmentServiceCommonMixin):
    """Upload and create entry points."""

    @classmethod
    def create_attachment_from_bytes(
        cls,
        db: Session,
        document_id: int,
        content: bytes,
        original_filename: str,
        content_type: str,
        current_user: User,
        *,
        convert_to_html: bool = False,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> Attachment:
        """Create attachment from raw bytes (optional HTML conversion).

        The uploaded bytes are stored exactly as received; conversion artifacts
        are generated separately and never replace the original binary.
        """
        # Validate file size
        file_size = len(content)
        if file_size > cls.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Max size: {cls.MAX_FILE_SIZE // (1024 * 1024)}MB",
            )

        # AG-014: Magic-byte validation for restricted types
        cls._validate_magic_bytes(content, original_filename, content_type)

        checksum_sha256 = hashlib.sha256(content).hexdigest()

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
            if not settings.ALLOW_LOCAL_STORAGE_FALLBACK:
                raise StorageError(f"Storage unavailable and fallback disabled: {e}") from e
            logger.warning("Falling back to local file storage")
            # Fallback to local file storage
            upload_dir = cls.get_upload_dir()
            doc_dir = upload_dir / str(document_id)
            doc_dir.mkdir(parents=True, exist_ok=True)
            file_path = doc_dir / unique_filename
            with open(file_path, "wb") as f:
                f.write(content)
            storage_path = str(file_path)

        # Create attachment record
        supports_reader_artifact = cls._supports_structured_reader_artifact(
            content_type,
            original_filename,
        )
        attachment = Attachment(
            document_id=document_id,
            filename=unique_filename,
            original_filename=original_filename,
            file_size=file_size,
            size_bytes=file_size,
            mime_type=content_type,
            storage_path=storage_path,
            storage_key=storage_path,
            sha256=checksum_sha256,
            reader_html_status=(
                cls.READER_STATUS_PENDING if supports_reader_artifact else None
            ),
            uploaded_by=current_user.id,
        )

        # Y15-021: Wrap DB commit in try/finally to clean up storage on failure
        try:
            db.add(attachment)
            db.commit()
            db.refresh(attachment)
        except Exception as db_error:
            # Clean up orphaned storage file if DB commit fails
            logger.error(f"DB commit failed for attachment, cleaning up storage: {db_error}")
            try:
                storage = get_storage_backend()
                storage.delete(storage_path)
                logger.info(f"Cleaned up orphaned storage file: {storage_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up storage file {storage_path}: {cleanup_error}")
            raise
        
        cls._ensure_artifact_rows(db, attachment, persist=True)

        if supports_reader_artifact:
            cls.schedule_reader_artifact_generation(attachment.id, background_tasks=background_tasks)

        if convert_to_html:
            try:
                wrapper = get_document_converter_wrapper()
                html_content = wrapper.convert_document_to_html(
                    content,
                    content_type,
                    original_filename,
                )

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
                        else cls._next_patch_semver(
                            existing_version.semantic_version, existing_version.version_number
                        )
                    )

                    version = Version(
                        document_id=document_id,
                        version_number=next_version,
                        semantic_version=next_semantic,
                        bump_type=VersionBumpType.PATCH
                        if existing_version
                        else VersionBumpType.MAJOR,
                        content=html_content,
                        changes_summary=f"Initial content from uploaded file: {original_filename}",
                        is_published=True,
                        published_at=attachment.uploaded_at,
                        published_by=current_user.id,
                        created_by=current_user.id,
                    )
                    db.add(version)
                    db.commit()
                    logger.info(
                        f"Created initial version {next_version} for document {document_id}"
                    )
            except Exception as e:
                logger.error(f"Failed to convert document to HTML: {e}")

        return attachment

    @staticmethod
    def enqueue_conversion(
        attachment_id: int,
        *,
        background_tasks: Optional[BackgroundTasks] = None,
        force: bool = False,
    ) -> None:
        """Enqueue async generation of the reader artifact for the given attachment."""
        from app.services.conversion_jobs import enqueue_conversion as enqueue_conversion_job

        enqueue_conversion_job(
            attachment_id,
            background_tasks=background_tasks,
            force=force,
        )
