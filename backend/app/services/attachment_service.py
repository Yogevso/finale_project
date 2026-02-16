"""Attachment Service - Business logic for file attachments"""

import hashlib
import io
import json
import logging
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, List, Optional, Tuple

from fastapi import BackgroundTasks, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
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
    STREAM_CHUNK_SIZE = 1024 * 1024
    READER_STATUS_PENDING = "pending"
    READER_STATUS_PROCESSING = "processing"
    READER_STATUS_READY = "ready"
    READER_STATUS_FAILED = "failed"

    @staticmethod
    def get_upload_dir() -> Path:
        """Get upload directory path"""
        upload_dir = (
            Path(settings.UPLOAD_DIR) if hasattr(settings, "UPLOAD_DIR") else Path("data/uploads")
        )
        upload_dir.mkdir(parents=True, exist_ok=True)
        return upload_dir

    @staticmethod
    def _parse_semver(
        raw_value: Optional[str], fallback_version_number: int
    ) -> Tuple[int, int, int]:
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
    def _chunk_bytes(data: bytes, chunk_size: int = STREAM_CHUNK_SIZE) -> Iterator[bytes]:
        offset = 0
        while offset < len(data):
            next_offset = offset + chunk_size
            yield data[offset:next_offset]
            offset = next_offset

    @staticmethod
    def _stream_file(file_path: str, chunk_size: int = STREAM_CHUNK_SIZE) -> Iterator[bytes]:
        with open(file_path, "rb") as file_obj:
            while True:
                chunk = file_obj.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    @staticmethod
    def _resolve_local_attachment_path(attachment: Attachment, document_id: int) -> Optional[str]:
        storage_ref = attachment.storage_key or attachment.storage_path

        # Try storage key/path as-is first (might be an absolute path).
        if storage_ref and os.path.exists(storage_ref):
            return storage_ref

        upload_dir = AttachmentService.get_upload_dir()

        if storage_ref:
            # Try key relative to uploads directory.
            possible_path = upload_dir / storage_ref
            if possible_path.exists():
                return str(possible_path)

            # Try document-scoped subdirectory layout.
            doc_subdir = upload_dir / str(document_id) / storage_ref
            if doc_subdir.exists():
                return str(doc_subdir)

        # Legacy fallback using generated filename.
        possible_path = upload_dir / attachment.filename
        if possible_path.exists():
            return str(possible_path)

        return None

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
        background_tasks: Optional[BackgroundTasks] = None,
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

        if (
            content_type not in AttachmentService.ALLOWED_TYPES
            and file_ext not in allowed_extensions
        ):
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
            background_tasks=background_tasks,
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
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> Attachment:
        """Create attachment from raw bytes (optional HTML conversion).

        The uploaded bytes are stored exactly as received; conversion artifacts
        are generated separately and never replace the original binary.
        """
        # Validate file size
        file_size = len(content)
        if file_size > AttachmentService.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Max size: {AttachmentService.MAX_FILE_SIZE // (1024 * 1024)}MB",
            )
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
            size_bytes=file_size,
            mime_type=content_type,
            storage_path=storage_path,
            storage_key=storage_path,
            sha256=checksum_sha256,
            reader_html_status=(
                AttachmentService.READER_STATUS_PENDING
                if content_type.lower().startswith("application/pdf")
                else None
            ),
            uploaded_by=current_user.id,
        )

        db.add(attachment)
        db.commit()
        db.refresh(attachment)

        if (attachment.mime_type or "").lower().startswith("application/pdf"):
            AttachmentService.schedule_reader_artifact_generation(
                attachment.id, background_tasks=background_tasks
            )

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

    @staticmethod
    def _load_original_bytes_for_attachment(attachment: Attachment) -> bytes:
        local_path = AttachmentService._resolve_local_attachment_path(
            attachment, attachment.document_id
        )
        if local_path:
            with open(local_path, "rb") as file_obj:
                return file_obj.read()

        storage_refs = [attachment.storage_key, attachment.storage_path]
        for storage_ref in storage_refs:
            if not storage_ref:
                continue
            try:
                storage = get_storage_backend()
                return storage.download(storage_ref)
            except Exception as exc:
                logger.warning(
                    "Failed loading attachment bytes from storage (attachment=%s, ref=%s): %s",
                    attachment.id,
                    storage_ref,
                    exc,
                )

        raise FileNotFoundError("Original attachment bytes not found")

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
    def _get_stored_reader_toc_items(attachment: Attachment) -> list[dict[str, Any]]:
        raw_json = attachment.reader_toc_json
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
            if not (attachment.mime_type or "").lower().startswith("application/pdf"):
                return
            if (
                not force
                and attachment.reader_html_status == AttachmentService.READER_STATUS_READY
                and attachment.reader_html_content
            ):
                return

            attachment.reader_html_status = AttachmentService.READER_STATUS_PROCESSING
            attachment.reader_html_error = None
            db.commit()

            from app.utils.document_converter import convert_pdf_to_reader_artifact

            pdf_bytes = AttachmentService._load_original_bytes_for_attachment(attachment)
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
                attachment.reader_html_status = AttachmentService.READER_STATUS_FAILED
                attachment.reader_html_content = None
                attachment.reader_toc_json = None
                attachment.reader_toc_source = None
                attachment.reader_html_error = (
                    "Failed to generate Reader View artifact"
                    if not html_content and not artifact_error
                    else (artifact_error or html_content)
                )
                attachment.reader_html_generated_at = datetime.utcnow()
                db.commit()
                return

            attachment.reader_html_status = AttachmentService.READER_STATUS_READY
            attachment.reader_html_content = html_content
            attachment.reader_toc_json = json.dumps(toc_items)
            attachment.reader_toc_source = toc_source
            attachment.reader_html_error = None
            attachment.reader_html_generated_at = datetime.utcnow()
            db.commit()
        except Exception as exc:
            logger.exception("Reader artifact generation failed for attachment %s", attachment_id)
            attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
            if attachment:
                attachment.reader_html_status = AttachmentService.READER_STATUS_FAILED
                attachment.reader_toc_json = None
                attachment.reader_toc_source = None
                attachment.reader_html_error = str(exc)
                attachment.reader_html_generated_at = datetime.utcnow()
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
        if not (attachment.mime_type or "").lower().startswith("application/pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reader View is only available for PDF attachments",
            )

        if not attachment.reader_html_status:
            attachment.reader_html_status = AttachmentService.READER_STATUS_PENDING
            db.commit()
            db.refresh(attachment)

        if force_retry:
            attachment.reader_html_status = AttachmentService.READER_STATUS_PENDING
            attachment.reader_html_error = None
            attachment.reader_html_content = None
            attachment.reader_toc_json = None
            attachment.reader_toc_source = None
            attachment.reader_html_generated_at = None
            db.commit()
            db.refresh(attachment)

        if (
            attachment.reader_html_status == AttachmentService.READER_STATUS_PENDING
            and not attachment.reader_html_content
        ):
            AttachmentService.schedule_reader_artifact_generation(
                attachment.id,
                background_tasks=background_tasks,
                force=force_retry,
            )

        toc_items = AttachmentService._get_stored_reader_toc_items(attachment)
        return {
            "attachment_id": attachment.id,
            "status": attachment.reader_html_status,
            "html_content": attachment.reader_html_content,
            "toc_items": toc_items,
            "toc_source": attachment.reader_toc_source,
            "error": attachment.reader_html_error,
            "generated_at": attachment.reader_html_generated_at,
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
        current_user: User,
    ) -> dict:
        """Extract PDF outline/bookmarks for an attachment preview TOC."""
        attachment = AttachmentService.get_attachment(db, document_id, attachment_id, current_user)
        if not (attachment.mime_type or "").lower().startswith("application/pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Outline is only available for PDF attachments",
            )

        stored_toc_items = AttachmentService._get_stored_reader_toc_items(attachment)
        if stored_toc_items:
            return {
                "attachment_id": attachment.id,
                "has_outline": True,
                "items": stored_toc_items,
                "source": attachment.reader_toc_source or "outline",
                "error": None,
            }

        try:
            from app.utils.document_converter import extract_pdf_toc

            pdf_bytes = AttachmentService._load_original_bytes_for_attachment(attachment)
            toc_payload = extract_pdf_toc(pdf_bytes)
            normalized_items = AttachmentService._normalize_toc_items(
                toc_payload.get("toc_items") or []
            )

            return {
                "attachment_id": attachment.id,
                "has_outline": bool(normalized_items),
                "items": normalized_items,
                "source": toc_payload.get("toc_source") or "none",
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
        try:
            storage = get_storage_backend()
            storage.delete(storage_ref)
            logger.info(f"Deleted attachment from storage: {storage_ref}")
            if attachment.storage_path != storage_ref:
                storage.delete(attachment.storage_path)
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
        db: Session, document_id: int, attachment_id: int, current_user: User
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
