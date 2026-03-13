"""Reader-view artifact generation and retrieval for structured office documents."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from typing import Any, Optional

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.legacy_wrappers import get_document_converter_wrapper
from app.models import Attachment, AttachmentArtifact, User

from .artifacts import AttachmentServiceArtifactsMixin

logger = logging.getLogger(__name__)

AttachmentService = None  # Assigned by package facade at import time.

_UNSUPPORTED_READER_VIEW_ERROR = "Reader View is only available for DOCX and PPTX attachments"


class AttachmentServiceReaderViewMixin(AttachmentServiceArtifactsMixin):
    """Reader artifact lifecycle and retrieval endpoints."""

    @staticmethod
    def schedule_reader_artifact_generation(
        attachment_id: int,
        *,
        background_tasks: Optional[BackgroundTasks] = None,
        force: bool = False,
    ) -> None:
        """Schedule asynchronous generation of a derived reader artifact."""
        if background_tasks:
            background_tasks.add_task(
                AttachmentService.generate_reader_artifact,
                attachment_id,
                force,
            )
            return

        worker = threading.Thread(
            target=AttachmentService.generate_reader_artifact,
            args=(attachment_id, force),
            daemon=True,
        )
        worker.start()

    @staticmethod
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

            anchor_id = str(raw_item.get("anchor_id") or f"page-{page_start}").strip()
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
    def _get_stored_reader_toc_items(
        attachment: Attachment, *, reader_artifact: Optional[AttachmentArtifact] = None
    ) -> list[dict[str, Any]]:
        payload = AttachmentService._get_stored_reader_payload(
            attachment,
            reader_artifact=reader_artifact,
        )
        return AttachmentService._normalize_toc_items(payload.get("toc_items") or [])

    @staticmethod
    def _get_stored_reader_payload(
        attachment: Attachment, *, reader_artifact: Optional[AttachmentArtifact] = None
    ) -> dict[str, Any]:
        raw_json = (
            reader_artifact.content_json
            if reader_artifact and reader_artifact.content_json is not None
            else attachment.reader_toc_json
        )
        if not raw_json:
            return {}

        try:
            payload = json.loads(raw_json)
        except Exception:
            logger.warning("Invalid reader_toc_json for attachment %s", attachment.id)
            return {}

        if isinstance(payload, dict):
            return payload
        if isinstance(payload, list):
            return {"toc_items": payload}
        return {}

    @staticmethod
    def _normalize_reader_warnings(raw_warnings: Any) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        if not isinstance(raw_warnings, list):
            return normalized

        for item in raw_warnings:
            if not isinstance(item, dict):
                continue
            code = str(item.get("code") or "").strip()
            message = str(item.get("message") or "").strip()
            if not code or not message:
                continue
            count = item.get("count")
            if count is not None:
                try:
                    count = int(count)
                except (TypeError, ValueError):
                    count = None
            normalized.append({"code": code, "message": message, "count": count})
        return normalized

    @staticmethod
    def _attachment_supports_structured_reader_artifact(attachment: Attachment) -> bool:
        return AttachmentService._supports_structured_reader_artifact(
            attachment.mime_type or "",
            attachment.original_filename or attachment.filename or "",
        )

    @staticmethod
    def generate_reader_artifact(attachment_id: int, force: bool = False) -> None:
        """Generate HTML reader artifact for supported DOCX and PPTX attachments."""
        db = SessionLocal()
        try:
            attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
            if not attachment:
                logger.warning(
                    "Reader artifact generation skipped: attachment %s not found", attachment_id
                )
                return

            reader_artifact = AttachmentService._ensure_artifact_rows(db, attachment, persist=True)

            if not AttachmentService._attachment_supports_structured_reader_artifact(attachment):
                reader_artifact.status = AttachmentService.READER_STATUS_FAILED
                reader_artifact.content_text = None
                reader_artifact.content_json = None
                reader_artifact.source = None
                reader_artifact.error = _UNSUPPORTED_READER_VIEW_ERROR
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

            wrapper = get_document_converter_wrapper()
            original_bytes = AttachmentService._load_original_bytes_for_attachment(attachment)
            artifact = wrapper.convert_document_to_reader_artifact(
                original_bytes,
                attachment.mime_type or "application/octet-stream",
                attachment.original_filename or attachment.filename or "document",
            )
            if not artifact:
                raise ValueError("Structured reader extraction is not available")

            html_content = (artifact.get("html_content") or "").strip()
            toc_items = AttachmentService._normalize_toc_items(artifact.get("toc_items") or [])
            toc_source = str(artifact.get("toc_source") or "headings").strip() or "headings"
            artifact_error = str(artifact.get("error") or "").strip() or None
            payload = artifact.get("payload") or {}
            if not isinstance(payload, dict):
                payload = {"toc_items": toc_items}
            payload.setdefault("toc_items", toc_items)

            if not html_content or artifact_error or artifact.get("status") != "ready":
                reader_artifact.status = AttachmentService.READER_STATUS_FAILED
                reader_artifact.content_text = None
                reader_artifact.content_json = None
                reader_artifact.source = None
                reader_artifact.error = (
                    artifact_error or "Failed to generate Reader View artifact"
                )
                reader_artifact.generated_at = datetime.utcnow()
                AttachmentService._apply_reader_artifact_to_attachment(attachment, reader_artifact)
                db.commit()
                return

            reader_artifact.status = AttachmentService.READER_STATUS_READY
            reader_artifact.content_text = html_content
            reader_artifact.content_json = json.dumps(payload)
            reader_artifact.source = toc_source
            reader_artifact.error = None
            reader_artifact.generated_at = datetime.utcnow()
            AttachmentService._apply_reader_artifact_to_attachment(attachment, reader_artifact)
            db.commit()
        except Exception as exc:
            logger.exception("Reader artifact generation failed for attachment %s", attachment_id)
            attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
            if attachment:
                reader_artifact = AttachmentService._ensure_artifact_rows(
                    db, attachment, persist=False
                )
                reader_artifact.status = AttachmentService.READER_STATUS_FAILED
                reader_artifact.content_text = None
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
        """Get derived Reader View HTML/status for a supported attachment."""
        attachment = AttachmentService.get_attachment(db, document_id, attachment_id, current_user)
        reader_artifact = AttachmentService._ensure_artifact_rows(db, attachment, persist=True)

        if not AttachmentService._attachment_supports_structured_reader_artifact(attachment):
            if force_retry or reader_artifact.status != AttachmentService.READER_STATUS_FAILED:
                reader_artifact.status = AttachmentService.READER_STATUS_FAILED
                reader_artifact.content_text = None
                reader_artifact.content_json = None
                reader_artifact.source = None
                reader_artifact.error = _UNSUPPORTED_READER_VIEW_ERROR
                reader_artifact.generated_at = datetime.utcnow()
                AttachmentService._apply_reader_artifact_to_attachment(attachment, reader_artifact)
                db.commit()
                db.refresh(reader_artifact)
                db.refresh(attachment)

            return {
                "attachment_id": attachment.id,
                "status": reader_artifact.status,
                "html_content": reader_artifact.content_text,
                "toc_items": [],
                "toc_source": reader_artifact.source,
                "warnings": [],
                "confidence": None,
                "error": reader_artifact.error,
                "generated_at": reader_artifact.generated_at,
            }

        if force_retry:
            reader_artifact.status = AttachmentService.READER_STATUS_PENDING
            reader_artifact.error = None
            reader_artifact.content_text = None
            reader_artifact.content_json = None
            reader_artifact.source = None
            reader_artifact.generated_at = None
            AttachmentService._apply_reader_artifact_to_attachment(attachment, reader_artifact)
            db.commit()
            db.refresh(reader_artifact)
            db.refresh(attachment)

        should_schedule = (not reader_artifact.status) or (
            reader_artifact.status
            in (
                AttachmentService.READER_STATUS_PENDING,
                AttachmentService.READER_STATUS_PROCESSING,
            )
            and not reader_artifact.content_text
        )

        if should_schedule:
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
        reader_payload = AttachmentService._get_stored_reader_payload(
            attachment,
            reader_artifact=reader_artifact,
        )
        reader_warnings = AttachmentService._normalize_reader_warnings(
            reader_payload.get("warnings") or []
        )
        confidence_value = reader_payload.get("confidence")
        try:
            confidence = float(confidence_value) if confidence_value is not None else None
        except (TypeError, ValueError):
            confidence = None
        return {
            "attachment_id": attachment.id,
            "status": reader_artifact.status,
            "html_content": reader_artifact.content_text,
            "toc_items": toc_items,
            "toc_source": reader_artifact.source,
            "warnings": reader_warnings,
            "confidence": confidence,
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
