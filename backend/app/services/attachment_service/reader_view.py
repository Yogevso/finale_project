"""Reader-view artifact generation and retrieval."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from typing import Any, Optional

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Attachment, AttachmentArtifact, User

from .artifacts import AttachmentServiceArtifactsMixin

logger = logging.getLogger(__name__)

AttachmentService = None  # Assigned by package facade at import time.


class AttachmentServiceReaderViewMixin(AttachmentServiceArtifactsMixin):
    """Reader artifact lifecycle and TOC retrieval endpoints."""

    @staticmethod
    def schedule_reader_artifact_generation(
        attachment_id: int,
        *,
        background_tasks: Optional[BackgroundTasks] = None,
        force: bool = False,
    ) -> None:
        """Schedule asynchronous generation of a derived PDF reader artifact."""
        if background_tasks:
            background_tasks.add_task(
                AttachmentService.generate_pdf_reader_artifact,
                attachment_id,
                force,
            )
            return

        worker = threading.Thread(
            target=AttachmentService.generate_pdf_reader_artifact,
            args=(attachment_id, force),
            daemon=True,
        )
        worker.start()


    def _normalize_toc_items(raw_items: Any) -> list[dict[str, Any]]:
        normalized_items: list[dict[str, Any]] = []
        if not isinstance(raw_items, list):
            return normalized_items

        for index, raw_item in enumerate(raw_items):
            if not isinstance(raw_item, dict):
                continue

            title = str(raw_item.get("title") or "").strip()
            if not title:
                continue

            try:
                level = max(1, int(raw_item.get("level", 1) or 1))
                page_start = max(
                    1,
                    int(raw_item.get("page_start") or raw_item.get("page") or 1),
                )
            except (TypeError, ValueError):
                continue

            page_end_raw = raw_item.get("page_end")
            page_end: Optional[int]
            try:
                page_end = int(page_end_raw) if page_end_raw is not None else None
            except (TypeError, ValueError):
                page_end = None
            if page_end is not None and page_end < page_start:
                page_end = page_start

            anchor_id = str(raw_item.get("anchor_id") or f"pdf-page-{page_start}").strip()
            item_id = str(raw_item.get("id") or f"toc-{index}").strip() or f"toc-{index}"

            normalized_items.append(
                {
                    "id": item_id,
                    "title": title,
                    "level": level,
                    "page": page_start,
                    "page_start": page_start,
                    "page_end": page_end,
                    "anchor_id": anchor_id,
                }
            )

        return normalized_items

    @staticmethod
    def _normalize_outline_source(source: Optional[str]) -> str:
        normalized = (source or "").strip().lower()
        if normalized in {"bookmarks", "outline"}:
            return "bookmarks"
        if normalized in {"contents-fallback", "contents_page", "heuristic"}:
            return "contents-fallback"
        return "none"

    @staticmethod
    def _get_stored_reader_toc_items(
        attachment: Attachment, *, reader_artifact: Optional[AttachmentArtifact] = None
    ) -> list[dict[str, Any]]:
        raw_json = (
            reader_artifact.content_json
            if reader_artifact and reader_artifact.content_json is not None
            else attachment.reader_toc_json
        )
        if not raw_json:
            return []

        try:
            payload = json.loads(raw_json)
        except Exception:
            logger.warning("Invalid reader_toc_json for attachment %s", attachment.id)
            return []

        return AttachmentService._normalize_toc_items(payload)

    @staticmethod
    def generate_pdf_reader_artifact(attachment_id: int, force: bool = False) -> None:
        """Generate HTML reader artifact for a PDF attachment."""
        db = SessionLocal()
        try:
            attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
            if not attachment:
                logger.warning(
                    "Reader artifact generation skipped: attachment %s not found", attachment_id
                )
                return

            preview_artifact, reader_artifact = AttachmentService._ensure_artifact_rows(
                db, attachment, persist=True
            )
            preview_status = preview_artifact.status or (
                AttachmentService.PREVIEW_STATUS_READY
                if (attachment.mime_type or "").lower().startswith("application/pdf")
                else AttachmentService.PREVIEW_STATUS_PENDING
            )
            preview_artifact.status = preview_status
            AttachmentService._apply_preview_artifact_to_attachment(attachment, preview_artifact)

            if preview_status in (
                AttachmentService.PREVIEW_STATUS_PENDING,
                AttachmentService.PREVIEW_STATUS_PROCESSING,
            ):
                reader_artifact.status = AttachmentService.READER_STATUS_PENDING
                reader_artifact.error = None
                AttachmentService._apply_reader_artifact_to_attachment(attachment, reader_artifact)
                db.commit()
                AttachmentService.schedule_preview_pdf_generation(attachment.id, force=force)
                return

            if preview_status == AttachmentService.PREVIEW_STATUS_FAILED:
                reader_artifact.status = AttachmentService.READER_STATUS_FAILED
                reader_artifact.error = preview_artifact.error or "Preview PDF generation failed"
                reader_artifact.generated_at = datetime.utcnow()
                AttachmentService._apply_reader_artifact_to_attachment(attachment, reader_artifact)
                db.commit()
                return

            if (
                not (preview_artifact.mime_type or "application/pdf")
                .lower()
                .startswith("application/pdf")
            ):
                reader_artifact.status = AttachmentService.READER_STATUS_FAILED
                reader_artifact.error = "Preview artifact is not a PDF"
                reader_artifact.generated_at = datetime.utcnow()
                AttachmentService._apply_reader_artifact_to_attachment(attachment, reader_artifact)
                db.commit()
                return

            if (
                not force
                and reader_artifact.status == AttachmentService.READER_STATUS_READY
                and reader_artifact.content_text
            ):
                return

            reader_artifact.status = AttachmentService.READER_STATUS_PROCESSING
            reader_artifact.error = None
            reader_artifact.generated_at = None
            AttachmentService._apply_reader_artifact_to_attachment(attachment, reader_artifact)
            db.commit()

            from app.utils.document_converter import convert_pdf_to_reader_artifact

            pdf_bytes = AttachmentService._load_preview_pdf_bytes_for_attachment(attachment)
            artifact = convert_pdf_to_reader_artifact(pdf_bytes)
            html_content = (artifact.get("html_content") or "").strip()
            toc_items = AttachmentService._normalize_toc_items(artifact.get("toc_items") or [])
            toc_source = str(artifact.get("toc_source") or "none")
            artifact_error = str(artifact.get("error") or "").strip() or None

            conversion_error_markers = (
                "conversion not available",
                "error converting pdf",
            )
            has_error_marker = any(
                marker in html_content.lower() for marker in conversion_error_markers
            )

            if not html_content or has_error_marker or artifact_error:
                reader_artifact.status = AttachmentService.READER_STATUS_FAILED
                reader_artifact.content_text = None
                reader_artifact.content_json = None
                reader_artifact.source = None
                reader_artifact.error = (
                    "Failed to generate Reader View artifact"
                    if not html_content and not artifact_error
                    else (artifact_error or html_content)
                )
                reader_artifact.generated_at = datetime.utcnow()
                AttachmentService._apply_reader_artifact_to_attachment(attachment, reader_artifact)
                db.commit()
                return

            reader_artifact.status = AttachmentService.READER_STATUS_READY
            reader_artifact.content_text = html_content
            reader_artifact.content_json = json.dumps(toc_items)
            reader_artifact.source = toc_source
            reader_artifact.error = None
            reader_artifact.generated_at = datetime.utcnow()
            AttachmentService._apply_reader_artifact_to_attachment(attachment, reader_artifact)
            db.commit()
        except Exception as exc:
            logger.exception("Reader artifact generation failed for attachment %s", attachment_id)
            attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
            if attachment:
                preview_artifact, reader_artifact = AttachmentService._ensure_artifact_rows(
                    db, attachment, persist=False
                )
                reader_artifact.status = AttachmentService.READER_STATUS_FAILED
                reader_artifact.content_json = None
                reader_artifact.source = None
                reader_artifact.error = str(exc)
                reader_artifact.generated_at = datetime.utcnow()
                AttachmentService._apply_reader_artifact_to_attachment(attachment, reader_artifact)
                db.commit()
        finally:
            db.close()

    @staticmethod
    def get_reader_view(
        db: Session,
        document_id: int,
        attachment_id: int,
        current_user: User,
        *,
        background_tasks: Optional[BackgroundTasks] = None,
        force_retry: bool = False,
    ) -> dict:
        """Get derived Reader View HTML/status for a PDF attachment."""
        attachment = AttachmentService.get_attachment(db, document_id, attachment_id, current_user)
        preview_artifact, reader_artifact = AttachmentService._ensure_artifact_rows(
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

        if force_retry:
            preview_artifact.error = None
            preview_artifact.generated_at = None
            if not mime_lower.startswith("application/pdf"):
                preview_artifact.status = AttachmentService.PREVIEW_STATUS_PENDING
                preview_artifact.storage_key = None
                preview_artifact.mime_type = None
                preview_artifact.size_bytes = None
                preview_artifact.sha256 = None
            reader_artifact.status = AttachmentService.READER_STATUS_PENDING
            reader_artifact.error = None
            reader_artifact.content_text = None
            reader_artifact.content_json = None
            reader_artifact.source = None
            reader_artifact.generated_at = None
            AttachmentService._apply_preview_artifact_to_attachment(attachment, preview_artifact)
            AttachmentService._apply_reader_artifact_to_attachment(attachment, reader_artifact)
            db.commit()
            db.refresh(preview_artifact)
            db.refresh(reader_artifact)
            db.refresh(attachment)

        if preview_artifact.status in (
            AttachmentService.PREVIEW_STATUS_PENDING,
            AttachmentService.PREVIEW_STATUS_PROCESSING,
        ):
            if not reader_artifact.status:
                reader_artifact.status = AttachmentService.READER_STATUS_PENDING
                AttachmentService._apply_reader_artifact_to_attachment(attachment, reader_artifact)
                db.commit()
                db.refresh(reader_artifact)
                db.refresh(attachment)
            AttachmentService.schedule_preview_pdf_generation(
                attachment.id,
                background_tasks=background_tasks,
                force=force_retry,
            )
        elif preview_artifact.status == AttachmentService.PREVIEW_STATUS_FAILED:
            reader_artifact.status = AttachmentService.READER_STATUS_FAILED
            reader_artifact.error = preview_artifact.error or "Preview PDF generation failed"
            reader_artifact.generated_at = datetime.utcnow()
            AttachmentService._apply_reader_artifact_to_attachment(attachment, reader_artifact)
            db.commit()
            db.refresh(reader_artifact)
            db.refresh(attachment)
        elif (not reader_artifact.status) or (
            reader_artifact.status == AttachmentService.READER_STATUS_PENDING
            and not reader_artifact.content_text
        ):
            reader_artifact.status = AttachmentService.READER_STATUS_PENDING
            AttachmentService._apply_reader_artifact_to_attachment(attachment, reader_artifact)
            db.commit()
            db.refresh(reader_artifact)
            db.refresh(attachment)
            AttachmentService.schedule_reader_artifact_generation(
                attachment.id,
                background_tasks=background_tasks,
                force=force_retry,
            )

        toc_items = AttachmentService._get_stored_reader_toc_items(
            attachment, reader_artifact=reader_artifact
        )
        return {
            "attachment_id": attachment.id,
            "status": reader_artifact.status,
            "html_content": reader_artifact.content_text,
            "toc_items": toc_items,
            "toc_source": reader_artifact.source,
            "error": reader_artifact.error,
            "generated_at": reader_artifact.generated_at,
        }

    @staticmethod
    def retry_reader_view_generation(
        db: Session,
        document_id: int,
        attachment_id: int,
        current_user: User,
        *,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> dict:
        """Force a fresh Reader artifact generation attempt."""
        return AttachmentService.get_reader_view(
            db,
            document_id,
            attachment_id,
            current_user,
            background_tasks=background_tasks,
            force_retry=True,
        )

    @staticmethod
    def get_pdf_outline(
        db: Session,
        document_id: int,
        attachment_id: int,
        current_user: Optional[User] = None,
    ) -> dict:
        """Extract PDF outline/bookmarks for an attachment preview TOC."""
        attachment = AttachmentService.get_attachment(db, document_id, attachment_id, current_user)
        preview_artifact, reader_artifact = AttachmentService._ensure_artifact_rows(
            db, attachment, persist=True
        )

        if not preview_artifact.status:
            if (attachment.mime_type or "").lower().startswith("application/pdf"):
                preview_artifact.status = AttachmentService.PREVIEW_STATUS_READY
                preview_artifact.storage_key = attachment.storage_key or attachment.storage_path
                preview_artifact.mime_type = "application/pdf"
                preview_artifact.size_bytes = attachment.size_bytes or attachment.file_size
                preview_artifact.sha256 = attachment.sha256
            else:
                preview_artifact.status = AttachmentService.PREVIEW_STATUS_PENDING
            AttachmentService._apply_preview_artifact_to_attachment(attachment, preview_artifact)
            db.commit()
            db.refresh(preview_artifact)
            db.refresh(attachment)

        if preview_artifact.status in (
            AttachmentService.PREVIEW_STATUS_PENDING,
            AttachmentService.PREVIEW_STATUS_PROCESSING,
        ):
            AttachmentService.schedule_preview_pdf_generation(attachment.id)
            return {
                "attachment_id": attachment.id,
                "has_outline": False,
                "items": [],
                "source": "none",
                "error": "Preview PDF is being generated",
            }

        if preview_artifact.status == AttachmentService.PREVIEW_STATUS_FAILED:
            return {
                "attachment_id": attachment.id,
                "has_outline": False,
                "items": [],
                "source": "none",
                "error": preview_artifact.error or "Preview PDF generation failed",
            }

        stored_toc_items = AttachmentService._get_stored_reader_toc_items(
            attachment, reader_artifact=reader_artifact
        )
        if stored_toc_items:
            source = AttachmentService._normalize_outline_source(reader_artifact.source)
            if source == "none":
                source = "contents-fallback"
            return {
                "attachment_id": attachment.id,
                "has_outline": True,
                "items": stored_toc_items,
                "source": source,
                "error": None,
            }

        try:
            from app.utils.document_converter import extract_pdf_toc

            pdf_bytes = AttachmentService._load_preview_pdf_bytes_for_attachment(attachment)
            toc_payload = extract_pdf_toc(pdf_bytes)
            normalized_items = AttachmentService._normalize_toc_items(
                toc_payload.get("toc_items") or []
            )

            source = AttachmentService._normalize_outline_source(
                str(toc_payload.get("toc_source") or "")
            )
            if source == "none" and normalized_items:
                source = "contents-fallback"

            return {
                "attachment_id": attachment.id,
                "has_outline": bool(normalized_items),
                "items": normalized_items,
                "source": source,
                "error": toc_payload.get("error"),
            }
        except Exception as exc:
            logger.warning(
                "Failed extracting PDF outline for attachment %s: %s",
                attachment.id,
                exc,
            )
            return {
                "attachment_id": attachment.id,
                "has_outline": False,
                "items": [],
                "source": "none",
                "error": "Failed to extract PDF outline",
            }
