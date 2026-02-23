"""Preview PDF generation orchestration."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Optional

from fastapi import BackgroundTasks

from app.db import SessionLocal
from app.models import Attachment

from .common import AttachmentServiceCommonMixin

logger = logging.getLogger(__name__)

AttachmentService = None  # Assigned by package facade at import time.


class AttachmentServicePreviewPdfMixin(AttachmentServiceCommonMixin):
    """Preview PDF scheduling and generation."""

    @staticmethod
    def schedule_preview_pdf_generation(
        attachment_id: int,
        *,
        background_tasks: Optional[BackgroundTasks] = None,
        force: bool = False,
    ) -> None:
        """Backward-compatible alias for conversion enqueue."""
        AttachmentService.enqueue_conversion(
            attachment_id,
            background_tasks=background_tasks,
            force=force,
        )

    def generate_preview_pdf_artifact(attachment_id: int, force: bool = False) -> None:
        """Generate (or bind) the preview PDF artifact for an attachment."""
        db = SessionLocal()
        try:
            attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
            if not attachment:
                logger.warning("Preview generation skipped: attachment %s not found", attachment_id)
                return

            preview_artifact, reader_artifact = AttachmentService._ensure_artifact_rows(
                db, attachment, persist=True
            )

            if (
                not force
                and preview_artifact.status == AttachmentService.PREVIEW_STATUS_READY
                and preview_artifact.storage_key
            ):
                return

            preview_artifact.status = AttachmentService.PREVIEW_STATUS_PROCESSING
            preview_artifact.error = None
            preview_artifact.generated_at = None
            AttachmentService._apply_preview_artifact_to_attachment(attachment, preview_artifact)
            db.commit()

            mime_lower = (attachment.mime_type or "").lower()
            if mime_lower.startswith("application/pdf"):
                preview_artifact.status = AttachmentService.PREVIEW_STATUS_READY
                preview_artifact.storage_key = attachment.storage_key or attachment.storage_path
                preview_artifact.mime_type = "application/pdf"
                preview_artifact.size_bytes = attachment.size_bytes or attachment.file_size
                preview_artifact.sha256 = attachment.sha256
                preview_artifact.error = None
                preview_artifact.generated_at = datetime.utcnow()
                AttachmentService._apply_preview_artifact_to_attachment(
                    attachment, preview_artifact
                )
                db.commit()
            else:
                original_bytes = AttachmentService._load_original_bytes_for_attachment(attachment)
                preview_pdf_bytes = AttachmentService._convert_non_pdf_to_preview_pdf(
                    content=original_bytes,
                    mime_type=attachment.mime_type or "application/octet-stream",
                    filename=attachment.original_filename or attachment.filename or "document",
                )
                if not preview_pdf_bytes:
                    raise ValueError("Preview PDF conversion produced empty output")

                preview_key = AttachmentService._upload_artifact_bytes(
                    document_id=attachment.document_id,
                    attachment_id=attachment.id,
                    content=preview_pdf_bytes,
                    content_type="application/pdf",
                    suffix=".pdf",
                )

                preview_artifact.status = AttachmentService.PREVIEW_STATUS_READY
                preview_artifact.storage_key = preview_key
                preview_artifact.mime_type = "application/pdf"
                preview_artifact.size_bytes = len(preview_pdf_bytes)
                preview_artifact.sha256 = hashlib.sha256(preview_pdf_bytes).hexdigest()
                preview_artifact.error = None
                preview_artifact.generated_at = datetime.utcnow()
                AttachmentService._apply_preview_artifact_to_attachment(
                    attachment, preview_artifact
                )
                db.commit()

            AttachmentService.generate_pdf_reader_artifact(attachment.id, force=force)
        except Exception as exc:
            logger.exception(
                "Preview PDF artifact generation failed for attachment %s", attachment_id
            )
            attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
            if attachment:
                preview_artifact, reader_artifact = AttachmentService._ensure_artifact_rows(
                    db, attachment, persist=False
                )
                preview_artifact.status = AttachmentService.PREVIEW_STATUS_FAILED
                preview_artifact.error = str(exc)
                preview_artifact.generated_at = datetime.utcnow()
                if not reader_artifact.status:
                    reader_artifact.status = AttachmentService.READER_STATUS_FAILED
                AttachmentService._apply_preview_artifact_to_attachment(
                    attachment, preview_artifact
                )
                AttachmentService._apply_reader_artifact_to_attachment(attachment, reader_artifact)
                db.commit()
        finally:
            db.close()
