"""Attachment deletion and original-file streaming helpers."""

from __future__ import annotations

import logging
import os
from typing import Iterator, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Attachment, AttachmentArtifact, AttachmentConversionJob, User, UserRole

from .common import AttachmentServiceCommonMixin, get_storage_backend

logger = logging.getLogger(__name__)


class AttachmentServiceStreamsMixin(AttachmentServiceCommonMixin):
    """Download/open stream and deletion operations."""

    @classmethod
    def delete_attachment(
        cls, db: Session, document_id: int, attachment_id: int, current_user: User
    ) -> None:
        """Delete an attachment."""
        attachment = (
            db.query(Attachment)
            .filter(Attachment.id == attachment_id, Attachment.document_id == document_id)
            .first()
        )

        if not attachment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found"
            )

        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can delete attachments"
            )

        storage_ref = attachment.storage_key or attachment.storage_path
        try:
            storage = get_storage_backend()
            storage.delete(storage_ref)
            logger.info("Deleted attachment from storage: %s", storage_ref)
            if attachment.storage_path != storage_ref:
                storage.delete(attachment.storage_path)
        except Exception as exc:
            logger.warning("Failed to delete from storage: %s", exc)
            try:
                local_path = cls._resolve_local_attachment_path(attachment, document_id)
                if local_path and os.path.exists(local_path):
                    os.remove(local_path)
            except OSError:
                pass

        db.query(AttachmentConversionJob).filter(
            AttachmentConversionJob.attachment_id == attachment.id
        ).delete(synchronize_session=False)
        db.query(AttachmentArtifact).filter(
            AttachmentArtifact.attachment_id == attachment.id
        ).delete(synchronize_session=False)

        db.delete(attachment)
        db.commit()

    @classmethod
    def get_file_path(
        cls, db: Session, document_id: int, attachment_id: int, current_user: User
    ) -> tuple[str, str, str]:
        """Get file path for download - returns (path, filename, mime_type)."""
        attachment = cls.get_attachment(db, document_id, attachment_id, current_user)
        local_path = cls._resolve_local_attachment_path(attachment, document_id)
        if local_path:
            return local_path, attachment.original_filename, attachment.mime_type

        logger.error(
            "File not found for attachment %s: storage_key=%s storage_path=%s",
            attachment_id,
            attachment.storage_key,
            attachment.storage_path,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")

    @classmethod
    def open_original_stream(
        cls,
        db: Session,
        document_id: int,
        attachment_id: int,
        current_user: Optional[User] = None,
    ) -> tuple[Attachment, Iterator[bytes]]:
        """Open a byte-preserving stream for the original uploaded file."""
        attachment = cls.get_attachment(db, document_id, attachment_id, current_user)

        local_path = cls._resolve_local_attachment_path(attachment, document_id)
        if local_path:
            return attachment, cls._stream_file(local_path)

        storage_refs = [attachment.storage_key, attachment.storage_path]
        for storage_ref in storage_refs:
            if not storage_ref:
                continue
            try:
                storage = get_storage_backend()
                content = storage.download(storage_ref)
                return attachment, cls._chunk_bytes(content)
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
