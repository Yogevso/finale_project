"""Reader-view artifact generation and retrieval for structured office documents."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.legacy_wrappers import get_document_converter_wrapper
from app.models import Attachment, AttachmentArtifact, User

from .artifacts import AttachmentServiceArtifactsMixin

logger = logging.getLogger(__name__)

_UNSUPPORTED_READER_VIEW_ERROR = "Reader View is only available for DOCX and PPTX attachments"
_DOCX_READER_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_PPTX_READER_MIME_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


class AttachmentServiceReaderViewMixin(AttachmentServiceArtifactsMixin):
    """Reader artifact lifecycle and retrieval endpoints."""

    @classmethod
    def schedule_reader_artifact_generation(
        cls,
        attachment_id: int,
        *,
        db: Session | None = None,
        background_tasks: Optional[BackgroundTasks] = None,
        force: bool = False,
    ) -> None:
        """Schedule asynchronous generation through the durable conversion queue."""
        cls.enqueue_conversion(
            attachment_id,
            db=db,
            background_tasks=background_tasks,
            force=force,
        )

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

    @classmethod
    def _get_stored_reader_toc_items(
        cls,
        attachment: Attachment,
        *,
        reader_artifact: Optional[AttachmentArtifact] = None,
    ) -> list[dict[str, Any]]:
        payload = cls._get_stored_reader_payload(
            attachment,
            reader_artifact=reader_artifact,
        )
        return cls._normalize_toc_items(payload.get("toc_items") or [])

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
        except (
            Exception
        ):  # policy: DEGRADED — invalid stored TOC payload falls back to an empty structure
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

    @classmethod
    def _attachment_supports_structured_reader_artifact(cls, attachment: Attachment) -> bool:
        return cls._supports_structured_reader_artifact(
            attachment.mime_type or "",
            attachment.original_filename or attachment.filename or "",
        )

    @staticmethod
    def _resolve_structured_reader_kind(attachment: Attachment) -> str | None:
        normalized_mime = (attachment.mime_type or "").lower()
        suffix = Path(attachment.original_filename or attachment.filename or "").suffix.lower()

        if normalized_mime == _DOCX_READER_MIME_TYPE or suffix == ".docx":
            return "docx"
        if normalized_mime == _PPTX_READER_MIME_TYPE or suffix == ".pptx":
            return "pptx"
        if normalized_mime == "application/pdf" or suffix == ".pdf":
            return "pdf"
        return None

    @staticmethod
    def generate_docx_reader_artifact(
        original_bytes: bytes,
        attachment: Attachment,
    ) -> dict[str, Any] | None:
        wrapper = get_document_converter_wrapper()
        return wrapper.convert_document_to_reader_artifact(
            original_bytes,
            _DOCX_READER_MIME_TYPE,
            attachment.original_filename or attachment.filename or "document.docx",
        )

    @staticmethod
    def generate_pptx_reader_artifact(
        original_bytes: bytes,
        attachment: Attachment,
    ) -> dict[str, Any] | None:
        wrapper = get_document_converter_wrapper()
        return wrapper.convert_document_to_reader_artifact(
            original_bytes,
            _PPTX_READER_MIME_TYPE,
            attachment.original_filename or attachment.filename or "presentation.pptx",
        )

    @staticmethod
    def generate_pdf_reader_artifact(
        original_bytes: bytes,
        attachment: Attachment,
    ) -> dict[str, Any] | None:
        """Convert PDF → DOCX bytes, then delegate to the DOCX reader artifact pipeline."""
        from app.conversion.pdf_to_docx import convert_pdf_to_docx

        result = convert_pdf_to_docx(original_bytes)
        if result.error:
            return {"status": "error", "error": result.error}
        wrapper = get_document_converter_wrapper()
        return wrapper.convert_document_to_reader_artifact(
            result.docx_bytes,
            _DOCX_READER_MIME_TYPE,
            (attachment.original_filename or attachment.filename or "document").rsplit(".", 1)[0]
            + ".docx",
        )

    @classmethod
    def _generate_structured_reader_artifact(
        cls,
        original_bytes: bytes,
        attachment: Attachment,
    ) -> dict[str, Any] | None:
        reader_kind = cls._resolve_structured_reader_kind(attachment)
        if reader_kind == "docx":
            return cls.generate_docx_reader_artifact(original_bytes, attachment)
        if reader_kind == "pptx":
            return cls.generate_pptx_reader_artifact(original_bytes, attachment)
        if reader_kind == "pdf":
            return cls.generate_pdf_reader_artifact(original_bytes, attachment)
        return None

    @classmethod
    def map_status_to_response(
        cls,
        attachment: Attachment,
        reader_artifact: AttachmentArtifact,
        *,
        toc_items: Optional[list[dict[str, Any]]] = None,
        reader_payload: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        resolved_toc_items = (
            toc_items
            if toc_items is not None
            else cls._get_stored_reader_toc_items(
                attachment,
                reader_artifact=reader_artifact,
            )
        )
        resolved_payload = (
            reader_payload
            if reader_payload is not None
            else cls._get_stored_reader_payload(
                attachment,
                reader_artifact=reader_artifact,
            )
        )
        reader_warnings = cls._normalize_reader_warnings(resolved_payload.get("warnings") or [])
        confidence_value = resolved_payload.get("confidence")
        try:
            confidence = float(confidence_value) if confidence_value is not None else None
        except (TypeError, ValueError):
            confidence = None

        return {
            "attachment_id": attachment.id,
            "status": reader_artifact.status,
            "html_content": reader_artifact.content_text,
            "toc_items": resolved_toc_items,
            "toc_source": reader_artifact.source,
            "warnings": reader_warnings,
            "confidence": confidence,
            "error": reader_artifact.error,
            "generated_at": reader_artifact.generated_at,
        }

    @classmethod
    def generate_reader_artifact(cls, attachment_id: int, force: bool = False) -> None:
        """Generate HTML reader artifact for supported DOCX and PPTX attachments."""
        db = SessionLocal()
        try:
            attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
            if not attachment:
                logger.warning(
                    "Reader artifact generation skipped: attachment %s not found", attachment_id
                )
                return

            reader_artifact = cls._ensure_artifact_rows(db, attachment, persist=True)

            if not cls._attachment_supports_structured_reader_artifact(attachment):
                reader_artifact.status = cls.READER_STATUS_FAILED
                reader_artifact.content_text = None
                reader_artifact.content_json = None
                reader_artifact.source = None
                reader_artifact.error = _UNSUPPORTED_READER_VIEW_ERROR
                reader_artifact.generated_at = datetime.utcnow()
                cls._apply_reader_artifact_to_attachment(attachment, reader_artifact)
                db.commit()
                return

            if (
                not force
                and reader_artifact.status == cls.READER_STATUS_READY
                and reader_artifact.content_text
            ):
                return

            # Atomic claim: UPDATE ... WHERE status != 'processing' prevents TOCTOU races.
            # If another process already set status to PROCESSING, updated == 0 and we skip.
            claim_filter = db.query(AttachmentArtifact).filter(
                AttachmentArtifact.id == reader_artifact.id,
            )
            if not force:
                claim_filter = claim_filter.filter(
                    AttachmentArtifact.status != cls.READER_STATUS_PROCESSING,
                )
            claimed = claim_filter.update(
                {
                    AttachmentArtifact.status: cls.READER_STATUS_PROCESSING,
                    AttachmentArtifact.error: None,
                    AttachmentArtifact.generated_at: None,
                },
                synchronize_session="fetch",
            )
            if not claimed and not force:
                logger.info(
                    "Reader artifact already processing for attachment %s, skipping", attachment_id
                )
                return

            db.refresh(reader_artifact)
            cls._apply_reader_artifact_to_attachment(attachment, reader_artifact)
            db.commit()

            original_bytes = cls._load_original_bytes_for_attachment(attachment)
            artifact = cls._generate_structured_reader_artifact(
                original_bytes,
                attachment,
            )
            if not artifact:
                raise ValueError("Structured reader extraction is not available")

            html_content = (artifact.get("html_content") or "").strip()
            toc_items = cls._normalize_toc_items(artifact.get("toc_items") or [])
            toc_source = str(artifact.get("toc_source") or "headings").strip() or "headings"
            artifact_error = str(artifact.get("error") or "").strip() or None
            payload = artifact.get("payload") or {}
            if not isinstance(payload, dict):
                payload = {"toc_items": toc_items}
            payload.setdefault("toc_items", toc_items)

            if not html_content or artifact_error or artifact.get("status") != "ready":
                reader_artifact.status = cls.READER_STATUS_FAILED
                reader_artifact.content_text = None
                reader_artifact.content_json = None
                reader_artifact.source = None
                reader_artifact.error = artifact_error or "Failed to generate Reader View artifact"
                reader_artifact.generated_at = datetime.utcnow()
                cls._apply_reader_artifact_to_attachment(attachment, reader_artifact)
                db.commit()
                return

            reader_artifact.status = cls.READER_STATUS_READY
            reader_artifact.content_text = html_content
            reader_artifact.content_json = json.dumps(payload)
            reader_artifact.source = toc_source
            reader_artifact.error = None
            reader_artifact.generated_at = datetime.utcnow()
            cls._apply_reader_artifact_to_attachment(attachment, reader_artifact)
            db.commit()
        except Exception as exc:  # policy: COMPENSATING — persist a failed artifact state instead of crashing the worker
            logger.exception("Reader artifact generation failed for attachment %s", attachment_id)
            attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
            if attachment:
                reader_artifact = cls._ensure_artifact_rows(db, attachment, persist=False)
                reader_artifact.status = cls.READER_STATUS_FAILED
                reader_artifact.content_text = None
                reader_artifact.content_json = None
                reader_artifact.source = None
                reader_artifact.error = str(exc)
                reader_artifact.generated_at = datetime.utcnow()
                cls._apply_reader_artifact_to_attachment(attachment, reader_artifact)
                db.commit()
        finally:
            db.close()

    @classmethod
    def get_reader_view(
        cls,
        db: Session,
        document_id: int,
        attachment_id: int,
        current_user: User,
        *,
        background_tasks: Optional[BackgroundTasks] = None,
        force_retry: bool = False,
    ) -> dict:
        """Get derived Reader View HTML/status for a supported attachment."""
        attachment = cls.get_attachment(db, document_id, attachment_id, current_user)
        reader_artifact = cls._ensure_artifact_rows(db, attachment, persist=True)

        if not cls._attachment_supports_structured_reader_artifact(attachment):
            if force_retry or reader_artifact.status != cls.READER_STATUS_FAILED:
                reader_artifact.status = cls.READER_STATUS_FAILED
                reader_artifact.content_text = None
                reader_artifact.content_json = None
                reader_artifact.source = None
                reader_artifact.error = _UNSUPPORTED_READER_VIEW_ERROR
                reader_artifact.generated_at = datetime.utcnow()
                cls._apply_reader_artifact_to_attachment(attachment, reader_artifact)
                db.commit()
                db.refresh(reader_artifact)
                db.refresh(attachment)

            return cls.map_status_to_response(
                attachment,
                reader_artifact,
                toc_items=[],
                reader_payload={},
            )

        if force_retry:
            reader_artifact.status = cls.READER_STATUS_PENDING
            reader_artifact.error = None
            reader_artifact.content_text = None
            reader_artifact.content_json = None
            reader_artifact.source = None
            reader_artifact.generated_at = None
            cls._apply_reader_artifact_to_attachment(attachment, reader_artifact)
            db.commit()
            db.refresh(reader_artifact)
            db.refresh(attachment)

        should_schedule = (not reader_artifact.status) or (
            reader_artifact.status
            in (
                cls.READER_STATUS_PENDING,
                cls.READER_STATUS_PROCESSING,
            )
            and not reader_artifact.content_text
        )

        if should_schedule:
            reader_artifact.status = cls.READER_STATUS_PENDING
            cls._apply_reader_artifact_to_attachment(attachment, reader_artifact)
            db.commit()
            db.refresh(reader_artifact)
            db.refresh(attachment)
            cls.schedule_reader_artifact_generation(
                attachment.id,
                db=db,
                background_tasks=background_tasks,
                force=force_retry,
            )

        toc_items = cls._get_stored_reader_toc_items(
            attachment,
            reader_artifact=reader_artifact,
        )
        reader_payload = cls._get_stored_reader_payload(
            attachment,
            reader_artifact=reader_artifact,
        )
        return cls.map_status_to_response(
            attachment,
            reader_artifact,
            toc_items=toc_items,
            reader_payload=reader_payload,
        )

    @classmethod
    def retry_reader_view_generation(
        cls,
        db: Session,
        document_id: int,
        attachment_id: int,
        current_user: User,
        *,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> dict:
        """Force a fresh Reader artifact generation attempt."""
        return cls.get_reader_view(
            db,
            document_id,
            attachment_id,
            current_user,
            background_tasks=background_tasks,
            force_retry=True,
        )
