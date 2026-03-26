"""Attachment deletion and original-file streaming helpers."""

from __future__ import annotations

import logging
import os
from typing import Iterator, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.errors import NotFoundError, PermissionDeniedError
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
        # Enforce tenant isolation and document access before allowing deletion
        cls._get_document_for_attachment_access(db, document_id, current_user)
        
        attachment = (
            db.query(Attachment)
            .filter(Attachment.id == attachment_id, Attachment.document_id == document_id)
            .first()
        )

        if not attachment:
            raise NotFoundError("Attachment not found")

        if current_user.role != UserRole.ADMIN:
            raise PermissionDeniedError("Only admins can delete attachments")

        shared_storage_refs = []
        if attachment.storage_key:
            shared_storage_refs.append(Attachment.storage_key == attachment.storage_key)
        if attachment.storage_path:
            shared_storage_refs.append(Attachment.storage_path == attachment.storage_path)

        has_other_references = False
        if shared_storage_refs:
            has_other_references = (
                db.query(Attachment)
                .filter(
                    Attachment.id != attachment.id,
                )
                .filter(or_(*shared_storage_refs))
                .first()
                is not None
            )

        storage_ref = attachment.storage_key or attachment.storage_path
        if not has_other_references:
            try:
                storage = get_storage_backend()
                storage.delete(storage_ref)
                logger.info("Deleted attachment from storage: %s", storage_ref)
                if attachment.storage_path != storage_ref:
                    storage.delete(attachment.storage_path)
            except Exception as exc:  # policy: COMPENSATING — storage delete fallback may continue with local cleanup
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
        raise NotFoundError("File not found on disk")

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
            except Exception as exc:  # policy: DEGRADED — alternate storage refs may still recover the original file
                logger.warning(
                    "Storage download failed for attachment %s (ref=%s): %s",
                    attachment_id,
                    storage_ref,
                    exc,
                )

        raise NotFoundError("Original file not found in storage")
