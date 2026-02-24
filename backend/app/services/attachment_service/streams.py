"""Attachment deletion and download streaming helpers."""

from __future__ import annotations

import logging
import os
from typing import Iterator, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Attachment, AttachmentArtifact, AttachmentConversionJob, User, UserRole

from .common import AttachmentServiceCommonMixin, get_storage_backend

logger = logging.getLogger(__name__)

AttachmentService = None  # Assigned by package facade at import time.


class AttachmentServiceStreamsMixin(AttachmentServiceCommonMixin):
    """Download/open stream and deletion operations."""

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
        storage_ref = attachment.storage_key or attachment.storage_path
        preview_artifact = AttachmentService._get_artifact_record(
            db, attachment.id, AttachmentService.ARTIFACT_KIND_PREVIEW_PDF
        )
        preview_ref = (
            preview_artifact.storage_key
            if preview_artifact and preview_artifact.storage_key
            else attachment.preview_pdf_storage_key
        )
        try:
            storage = get_storage_backend()
            storage.delete(storage_ref)
            logger.info(f"Deleted attachment from storage: {storage_ref}")
            if attachment.storage_path != storage_ref:
                storage.delete(attachment.storage_path)
            if preview_ref and preview_ref not in {storage_ref, attachment.storage_path}:
                storage.delete(preview_ref)
        except Exception as e:
            logger.warning(f"Failed to delete from storage: {e}")
            # Try local file fallback
            try:
                local_path = AttachmentService._resolve_local_attachment_path(
                    attachment, document_id
                )
                if local_path and os.path.exists(local_path):
                    os.remove(local_path)
            except OSError:
                pass  # File may not exist

        # Delete job/artifact rows explicitly for databases without FK cascade enforcement.
        db.query(AttachmentConversionJob).filter(
            AttachmentConversionJob.attachment_id == attachment.id
        ).delete(synchronize_session=False)
        db.query(AttachmentArtifact).filter(
            AttachmentArtifact.attachment_id == attachment.id
        ).delete(synchronize_session=False)

        # Delete record
        db.delete(attachment)
        db.commit()

    @staticmethod
    def get_file_path(
        db: Session, document_id: int, attachment_id: int, current_user: User
    ) -> tuple[str, str, str]:
        """Get file path for download - returns (path, filename, mime_type)"""
        attachment = AttachmentService.get_attachment(db, document_id, attachment_id, current_user)
        local_path = AttachmentService._resolve_local_attachment_path(attachment, document_id)
        if local_path:
            return local_path, attachment.original_filename, attachment.mime_type

        logger.error(
            "File not found for attachment %s: storage_key=%s storage_path=%s",
            attachment_id,
            attachment.storage_key,
            attachment.storage_path,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")

    @staticmethod
    def open_original_stream(
        db: Session,
        document_id: int,
        attachment_id: int,
        current_user: Optional[User] = None,
    ) -> tuple[Attachment, Iterator[bytes]]:
        """Open a byte-preserving stream for the original uploaded file."""
        attachment = AttachmentService.get_attachment(db, document_id, attachment_id, current_user)

        local_path = AttachmentService._resolve_local_attachment_path(attachment, document_id)
        if local_path:
            return attachment, AttachmentService._stream_file(local_path)

        storage_refs = [attachment.storage_key, attachment.storage_path]
        for storage_ref in storage_refs:
            if not storage_ref:
                continue
            try:
                storage = get_storage_backend()
                content = storage.download(storage_ref)
                return attachment, AttachmentService._chunk_bytes(content)
            except Exception as exc:
                logger.warning(
                    "Storage download failed for attachment %s (ref=%s): %s",
                    attachment_id,
                    storage_ref,
                    exc,
                )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original file not found in storage",
        )

    @staticmethod
    def open_preview_stream(
        db: Session, document_id: int, attachment_id: int, current_user: Optional[User] = None
    ) -> tuple[Attachment, Iterator[bytes], str, int]:
        """Open stream for the preview PDF artifact (always PDF-based)."""
        attachment = AttachmentService.get_attachment(db, document_id, attachment_id, current_user)
        preview_artifact, _reader_artifact = AttachmentService._ensure_artifact_rows(
            db, attachment, persist=True
        )
        mime_lower = (attachment.mime_type or "").lower()

        if not preview_artifact.status:
            preview_artifact.status = (
                AttachmentService.PREVIEW_STATUS_READY
                if mime_lower.startswith("application/pdf")
                else AttachmentService.PREVIEW_STATUS_PENDING
            )
            if preview_artifact.status == AttachmentService.PREVIEW_STATUS_READY:
                preview_artifact.storage_key = attachment.storage_key or attachment.storage_path
                preview_artifact.mime_type = "application/pdf"
                preview_artifact.size_bytes = attachment.size_bytes or attachment.file_size
                preview_artifact.sha256 = attachment.sha256
            AttachmentService._apply_preview_artifact_to_attachment(attachment, preview_artifact)
            db.commit()
            db.refresh(preview_artifact)
            db.refresh(attachment)

        if preview_artifact.status in (
            AttachmentService.PREVIEW_STATUS_PENDING,
            AttachmentService.PREVIEW_STATUS_PROCESSING,
        ):
            AttachmentService.schedule_preview_pdf_generation(attachment.id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Preview PDF is being generated",
            )

        if preview_artifact.status == AttachmentService.PREVIEW_STATUS_FAILED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=preview_artifact.error or "Preview PDF generation failed",
            )

        preview_key = preview_artifact.storage_key
        if not preview_key and mime_lower.startswith("application/pdf"):
            preview_key = attachment.storage_key or attachment.storage_path

        if not preview_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Preview PDF not found",
            )

        local_path = None
        if preview_key in {attachment.storage_key, attachment.storage_path}:
            local_path = AttachmentService._resolve_local_attachment_path(attachment, document_id)
        elif os.path.exists(preview_key):
            local_path = preview_key

        if local_path:
            size = preview_artifact.size_bytes or attachment.size_bytes or attachment.file_size
            return (
                attachment,
                AttachmentService._stream_file(local_path),
                "application/pdf",
                int(size),
            )

        try:
            storage = get_storage_backend()
            content = storage.download(preview_key)
            return (
                attachment,
                AttachmentService._chunk_bytes(content),
                "application/pdf",
                len(content),
            )
        except Exception as exc:
            logger.warning(
                "Preview download failed for attachment %s (ref=%s): %s",
                attachment.id,
                preview_key,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Preview PDF not found in storage",
            ) from exc
