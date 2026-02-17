"""Attachment Service - Business logic for file attachments"""

import html
import hashlib
import io
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, List, Optional, Tuple

from fastapi import BackgroundTasks, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models import (
    Attachment,
    AttachmentArtifact,
    AttachmentConversionJob,
    Document,
    User,
    UserRole,
    Version,
    VersionBumpType,
)

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
    PREVIEW_STATUS_PENDING = "pending"
    PREVIEW_STATUS_PROCESSING = "processing"
    PREVIEW_STATUS_READY = "ready"
    PREVIEW_STATUS_FAILED = "failed"
    READER_STATUS_PENDING = "pending"
    READER_STATUS_PROCESSING = "processing"
    READER_STATUS_READY = "ready"
    READER_STATUS_FAILED = "failed"
    ARTIFACT_KIND_PREVIEW_PDF = "preview_pdf"
    ARTIFACT_KIND_READER_HTML = "reader_html"
    OFFICE_MIME_TYPES = {
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
    WORD_MIME_TYPES = {
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    OFFICE_EXTENSIONS = {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}
    WORD_EXTENSIONS = {".doc", ".docx"}
    TEXT_MIME_TYPES = {
        "text/plain",
        "text/markdown",
        "text/csv",
        "application/json",
    }
    HTML_MIME_TYPES = {"text/html"}
    CONVERSION_ERROR_MARKERS = (
        "conversion not available",
        "error converting",
        "word conversion not available",
    )

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
    def _get_artifact_record(
        db: Session, attachment_id: int, kind: str
    ) -> Optional[AttachmentArtifact]:
        return (
            db.query(AttachmentArtifact)
            .filter(
                AttachmentArtifact.attachment_id == attachment_id,
                AttachmentArtifact.kind == kind,
            )
            .first()
        )

    @staticmethod
    def _apply_preview_artifact_to_attachment(
        attachment: Attachment, artifact: Optional[AttachmentArtifact]
    ) -> None:
        if not artifact:
            return
        attachment.preview_pdf_status = artifact.status
        attachment.preview_pdf_storage_key = artifact.storage_key
        attachment.preview_pdf_mime_type = artifact.mime_type
        attachment.preview_pdf_size_bytes = artifact.size_bytes
        attachment.preview_pdf_sha256 = artifact.sha256
        attachment.preview_pdf_error = artifact.error
        attachment.preview_pdf_generated_at = artifact.generated_at

    @staticmethod
    def _apply_reader_artifact_to_attachment(
        attachment: Attachment, artifact: Optional[AttachmentArtifact]
    ) -> None:
        if not artifact:
            return
        attachment.reader_html_status = artifact.status
        attachment.reader_html_content = artifact.content_text
        attachment.reader_toc_json = artifact.content_json
        attachment.reader_toc_source = artifact.source
        attachment.reader_html_error = artifact.error
        attachment.reader_html_generated_at = artifact.generated_at

    @staticmethod
    def _apply_existing_artifacts_to_attachment(db: Session, attachment: Attachment) -> None:
        preview_artifact = AttachmentService._get_artifact_record(
            db, attachment.id, AttachmentService.ARTIFACT_KIND_PREVIEW_PDF
        )
        reader_artifact = AttachmentService._get_artifact_record(
            db, attachment.id, AttachmentService.ARTIFACT_KIND_READER_HTML
        )
        AttachmentService._apply_preview_artifact_to_attachment(attachment, preview_artifact)
        AttachmentService._apply_reader_artifact_to_attachment(attachment, reader_artifact)

    @staticmethod
    def _ensure_artifact_rows(
        db: Session,
        attachment: Attachment,
        *,
        persist: bool = False,
    ) -> tuple[AttachmentArtifact, AttachmentArtifact]:
        """Backfill artifact rows from legacy attachment columns when needed."""
        preview_artifact = AttachmentService._get_artifact_record(
            db, attachment.id, AttachmentService.ARTIFACT_KIND_PREVIEW_PDF
        )
        if not preview_artifact:
            preview_artifact = AttachmentArtifact(
                attachment_id=attachment.id,
                kind=AttachmentService.ARTIFACT_KIND_PREVIEW_PDF,
                status=attachment.preview_pdf_status
                or (
                    AttachmentService.PREVIEW_STATUS_READY
                    if (attachment.mime_type or "").lower().startswith("application/pdf")
                    else AttachmentService.PREVIEW_STATUS_PENDING
                ),
                mime_type=attachment.preview_pdf_mime_type
                or (
                    "application/pdf"
                    if (attachment.mime_type or "").lower().startswith("application/pdf")
                    else None
                ),
                storage_key=attachment.preview_pdf_storage_key
                or (
                    (attachment.storage_key or attachment.storage_path)
                    if (attachment.mime_type or "").lower().startswith("application/pdf")
                    else None
                ),
                size_bytes=attachment.preview_pdf_size_bytes
                or attachment.size_bytes
                or attachment.file_size,
                sha256=attachment.preview_pdf_sha256 or attachment.sha256,
                error=attachment.preview_pdf_error,
                generated_at=attachment.preview_pdf_generated_at,
            )
            db.add(preview_artifact)

        reader_artifact = AttachmentService._get_artifact_record(
            db, attachment.id, AttachmentService.ARTIFACT_KIND_READER_HTML
        )
        if not reader_artifact:
            reader_artifact = AttachmentArtifact(
                attachment_id=attachment.id,
                kind=AttachmentService.ARTIFACT_KIND_READER_HTML,
                status=attachment.reader_html_status or AttachmentService.READER_STATUS_PENDING,
                content_text=attachment.reader_html_content,
                content_json=attachment.reader_toc_json,
                source=attachment.reader_toc_source,
                error=attachment.reader_html_error,
                generated_at=attachment.reader_html_generated_at,
            )
            db.add(reader_artifact)

        # Keep legacy columns synchronized from artifact records for API compatibility.
        AttachmentService._apply_preview_artifact_to_attachment(attachment, preview_artifact)
        AttachmentService._apply_reader_artifact_to_attachment(attachment, reader_artifact)

        if persist:
            db.commit()
            db.refresh(attachment)
            db.refresh(preview_artifact)
            db.refresh(reader_artifact)

        return preview_artifact, reader_artifact

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
        attachments = (
            db.query(Attachment)
            .filter(Attachment.document_id == document_id)
            .order_by(Attachment.uploaded_at.desc())
            .all()
        )
        for attachment in attachments:
            AttachmentService._apply_existing_artifacts_to_attachment(db, attachment)
        return attachments

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

        AttachmentService._apply_existing_artifacts_to_attachment(db, attachment)
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
        allowed_extensions = {
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".txt",
            ".md",
            ".html",
            ".htm",
            ".json",
            ".csv",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".webp",
        }

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
            preview_pdf_status=(
                AttachmentService.PREVIEW_STATUS_READY
                if content_type.lower().startswith("application/pdf")
                else AttachmentService.PREVIEW_STATUS_PENDING
            ),
            preview_pdf_storage_key=(
                storage_path if content_type.lower().startswith("application/pdf") else None
            ),
            preview_pdf_mime_type=(
                "application/pdf" if content_type.lower().startswith("application/pdf") else None
            ),
            preview_pdf_size_bytes=(
                file_size if content_type.lower().startswith("application/pdf") else None
            ),
            preview_pdf_sha256=(
                checksum_sha256 if content_type.lower().startswith("application/pdf") else None
            ),
            preview_pdf_generated_at=(
                datetime.utcnow() if content_type.lower().startswith("application/pdf") else None
            ),
            reader_html_status=AttachmentService.READER_STATUS_PENDING,
            uploaded_by=current_user.id,
        )

        db.add(attachment)
        db.commit()
        db.refresh(attachment)
        AttachmentService._ensure_artifact_rows(db, attachment, persist=True)

        if (attachment.mime_type or "").lower().startswith("application/pdf"):
            AttachmentService.schedule_reader_artifact_generation(
                attachment.id, background_tasks=background_tasks
            )
        else:
            AttachmentService.schedule_preview_pdf_generation(
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
    def enqueue_conversion(
        attachment_id: int,
        *,
        background_tasks: Optional[BackgroundTasks] = None,
        force: bool = False,
    ) -> None:
        """Enqueue async generation of preview_pdf for the given attachment."""
        from app.services.conversion_jobs import enqueue_conversion as enqueue_conversion_job

        enqueue_conversion_job(
            attachment_id,
            background_tasks=background_tasks,
            force=force,
        )

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

    @staticmethod
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
                AttachmentService._apply_preview_artifact_to_attachment(attachment, preview_artifact)
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
                AttachmentService._apply_preview_artifact_to_attachment(attachment, preview_artifact)
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
                AttachmentService._apply_preview_artifact_to_attachment(attachment, preview_artifact)
                AttachmentService._apply_reader_artifact_to_attachment(attachment, reader_artifact)
                db.commit()
        finally:
            db.close()

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
    def _upload_artifact_bytes(
        *,
        document_id: int,
        attachment_id: int,
        content: bytes,
        content_type: str,
        suffix: str = ".pdf",
    ) -> str:
        artifact_filename = f"attachment_{attachment_id}_artifact{suffix}"
        storage = get_storage_backend()
        return storage.upload(
            io.BytesIO(content),
            f"doc_{document_id}/{artifact_filename}",
            content_type,
        )

    @staticmethod
    def _sanitize_filename_for_temp(original_filename: str, fallback_ext: str = "") -> str:
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", (original_filename or "").strip()) or "source"
        stem, ext = os.path.splitext(safe)
        ext = (ext or fallback_ext or "").lower()
        if fallback_ext and ext != fallback_ext:
            ext = fallback_ext
        return f"{stem or 'source'}{ext}"

    @staticmethod
    def _is_office_source(mime_type: str, filename: str) -> bool:
        normalized_mime = (mime_type or "").lower()
        suffix = Path(filename or "").suffix.lower()
        return (
            normalized_mime in AttachmentService.OFFICE_MIME_TYPES
            or suffix in AttachmentService.OFFICE_EXTENSIONS
        )

    @staticmethod
    def _is_word_source(mime_type: str, filename: str) -> bool:
        normalized_mime = (mime_type or "").lower()
        suffix = Path(filename or "").suffix.lower()
        return (
            normalized_mime in AttachmentService.WORD_MIME_TYPES
            or suffix in AttachmentService.WORD_EXTENSIONS
        )

    @staticmethod
    def _is_conversion_error_html(html_content: str) -> bool:
        normalized = (html_content or "").strip().lower()
        if not normalized:
            return True
        return any(marker in normalized for marker in AttachmentService.CONVERSION_ERROR_MARKERS)

    @staticmethod
    def _resolve_soffice_binary() -> Optional[str]:
        configured = (
            (settings.LIBREOFFICE_BIN or "").strip()
            or (os.getenv("LIBREOFFICE_BIN") or "").strip()
            or (os.getenv("SOFFICE_PATH") or "").strip()
        )
        candidates = [
            configured,
            shutil.which("soffice") or "",
            shutil.which("libreoffice") or "",
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",
            "/Applications/LibreOffice.app/Contents/MacOS/soffice.bin",
            "/opt/homebrew/bin/soffice",
            "/usr/local/bin/soffice",
            "/usr/bin/soffice",
            "/snap/bin/libreoffice",
            "/usr/lib/libreoffice/program/soffice",
            "/usr/lib64/libreoffice/program/soffice",
        ]
        seen: set[str] = set()
        for candidate in candidates:
            path = (candidate or "").strip()
            if not path or path in seen:
                continue
            seen.add(path)
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        return None

    @staticmethod
    def _convert_word_to_pdf_fallback_bytes(content: bytes, *, filename: str) -> bytes:
        from app.utils.document_converter import convert_word_to_html

        html_content = (convert_word_to_html(content) or "").strip()
        if AttachmentService._is_conversion_error_html(html_content):
            raise ValueError(
                "LibreOffice headless is required for Office conversion (Word fallback unavailable)"
            )
        return AttachmentService._convert_html_to_pdf_bytes(html_content, title=filename)

    @staticmethod
    def _convert_office_to_pdf_bytes(content: bytes, *, filename: str, mime_type: str = "") -> bytes:
        soffice = AttachmentService._resolve_soffice_binary()
        if not soffice:
            if AttachmentService._is_word_source(mime_type, filename):
                logger.warning(
                    "LibreOffice not found; using Word fallback conversion for preview PDF (file=%s)",
                    filename,
                )
                return AttachmentService._convert_word_to_pdf_fallback_bytes(
                    content, filename=filename
                )
            raise ValueError(
                "LibreOffice headless is required for Office conversion. "
                "Install LibreOffice or set LIBREOFFICE_BIN."
            )

        src_ext = Path(filename or "").suffix.lower() or ".bin"
        safe_name = AttachmentService._sanitize_filename_for_temp(filename, fallback_ext=src_ext)

        with tempfile.TemporaryDirectory(prefix="preview_pdf_office_") as tmp_dir:
            input_dir = Path(tmp_dir) / "input"
            out_dir = Path(tmp_dir) / "output"
            input_dir.mkdir(parents=True, exist_ok=True)
            out_dir.mkdir(parents=True, exist_ok=True)

            src_path = input_dir / safe_name
            src_path.write_bytes(content)

            command = [
                soffice,
                "--headless",
                "--nologo",
                "--nofirststartwizard",
                "--norestore",
                "--convert-to",
                "pdf",
                "--outdir",
                str(out_dir),
                str(src_path),
            ]

            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
            if proc.returncode != 0:
                stderr = (proc.stderr or "").strip()
                stdout = (proc.stdout or "").strip()
                detail = stderr or stdout or "unknown LibreOffice error"
                if AttachmentService._is_word_source(mime_type, filename):
                    logger.warning(
                        "LibreOffice conversion failed for Word file; falling back to HTML pipeline "
                        "(file=%s, error=%s)",
                        filename,
                        detail,
                    )
                    return AttachmentService._convert_word_to_pdf_fallback_bytes(
                        content, filename=filename
                    )
                raise ValueError(f"LibreOffice conversion failed: {detail}")

            expected_pdf = out_dir / f"{src_path.stem}.pdf"
            if expected_pdf.exists():
                return expected_pdf.read_bytes()

            any_pdf = sorted(out_dir.glob("*.pdf"))
            if any_pdf:
                return any_pdf[0].read_bytes()

            raise ValueError("LibreOffice conversion failed: no PDF output produced")

    @staticmethod
    def _convert_html_to_pdf_bytes(html_content: str, *, title: str = "Document") -> bytes:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            # Keep preview generation resilient in minimal dev environments.
            text_fallback = re.sub(r"<[^>]+>", " ", html_content or "")
            normalized = re.sub(r"\s+", " ", text_fallback).strip() or "Preview unavailable."
            return AttachmentService._convert_text_to_pdf_bytes(
                normalized.encode("utf-8", errors="replace"),
                title=title,
            )

        soup = BeautifulSoup(html_content or "", "html.parser")
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
            title=title,
        )

        styles = getSampleStyleSheet()
        body_style = styles["BodyText"]
        heading_styles = {
            "h1": ParagraphStyle(
                "h1_style", parent=styles["Heading1"], fontSize=18, leading=22, spaceAfter=10
            ),
            "h2": ParagraphStyle(
                "h2_style", parent=styles["Heading2"], fontSize=15, leading=19, spaceAfter=8
            ),
            "h3": ParagraphStyle(
                "h3_style", parent=styles["Heading3"], fontSize=13, leading=16, spaceAfter=7
            ),
            "h4": ParagraphStyle(
                "h4_style", parent=styles["Heading4"], fontSize=12, leading=15, spaceAfter=6
            ),
            "h5": ParagraphStyle(
                "h5_style", parent=styles["Heading5"], fontSize=11, leading=14, spaceAfter=5
            ),
            "h6": ParagraphStyle(
                "h6_style", parent=styles["Heading6"], fontSize=10, leading=13, spaceAfter=4
            ),
        }

        story = []
        roots = list((soup.body or soup).children)
        for node in roots:
            if not getattr(node, "name", None):
                continue
            tag = node.name.lower()
            text = " ".join(node.stripped_strings)
            if tag in heading_styles and text:
                story.append(Paragraph(html.escape(text, quote=True), heading_styles[tag]))
                story.append(Spacer(1, 6))
                continue
            if tag in {"p", "div", "section", "article"} and text:
                story.append(Paragraph(html.escape(text, quote=True), body_style))
                story.append(Spacer(1, 6))
                continue
            if tag in {"ul", "ol"}:
                ordered = tag == "ol"
                for idx, li in enumerate(node.find_all("li", recursive=False), start=1):
                    li_text = " ".join(li.stripped_strings)
                    if not li_text:
                        continue
                    prefix = f"{idx}. " if ordered else "• "
                    story.append(
                        Paragraph(html.escape(f"{prefix}{li_text}", quote=True), body_style)
                    )
                story.append(Spacer(1, 6))
                continue
            if tag == "table":
                rows = []
                for tr in node.find_all("tr"):
                    cells = tr.find_all(["th", "td"])
                    if not cells:
                        continue
                    row = [" ".join(cell.stripped_strings) for cell in cells]
                    rows.append(row)
                if rows:
                    max_cols = max(len(r) for r in rows)
                    normalized_rows = [r + [""] * (max_cols - len(r)) for r in rows]
                    table = Table(normalized_rows, repeatRows=1 if len(normalized_rows) > 1 else 0)
                    table.setStyle(
                        TableStyle(
                            [
                                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
                                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ]
                        )
                    )
                    story.append(table)
                    story.append(Spacer(1, 8))
                continue
            if tag == "hr":
                story.append(Spacer(1, 14))
                continue
            if text:
                story.append(Paragraph(html.escape(text, quote=True), body_style))
                story.append(Spacer(1, 6))

        if not story:
            fallback_text = " ".join((soup.get_text(" ", strip=True) or "").split())
            story.append(
                Paragraph(
                    html.escape(fallback_text or "Preview unavailable.", quote=True), body_style
                )
            )

        doc.build(story)
        return buffer.getvalue()

    @staticmethod
    def _convert_image_to_pdf_bytes(content: bytes, *, title: str = "Image Preview") -> bytes:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas

        buffer = io.BytesIO()
        page_width, page_height = A4
        pdf = canvas.Canvas(buffer, pagesize=A4)
        pdf.setTitle(title)

        image = ImageReader(io.BytesIO(content))
        image_width, image_height = image.getSize()

        margin = 36.0
        max_width = page_width - 2 * margin
        max_height = page_height - 2 * margin
        scale = min(max_width / float(image_width), max_height / float(image_height), 1.0)
        render_width = float(image_width) * scale
        render_height = float(image_height) * scale
        x = (page_width - render_width) / 2.0
        y = (page_height - render_height) / 2.0

        pdf.drawImage(
            image,
            x,
            y,
            width=render_width,
            height=render_height,
            preserveAspectRatio=True,
            mask="auto",
        )
        pdf.showPage()
        pdf.save()
        return buffer.getvalue()

    @staticmethod
    def _convert_text_to_pdf_bytes(content: bytes, *, title: str = "Text Preview") -> bytes:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        text = content.decode("utf-8", errors="replace")
        lines = text.splitlines() or [text]

        buffer = io.BytesIO()
        page_width, page_height = A4
        left_margin = 40
        top_margin = 44
        bottom_margin = 36
        line_height = 14

        pdf = canvas.Canvas(buffer, pagesize=A4)
        pdf.setTitle(title)
        pdf.setFont("Helvetica", 10)

        y = page_height - top_margin
        max_chars_per_line = max(40, int((page_width - left_margin * 2) / 5.6))

        for raw_line in lines:
            line = raw_line or ""
            wrapped = [line[i : i + max_chars_per_line] for i in range(0, len(line), max_chars_per_line)]
            if not wrapped:
                wrapped = [""]

            for segment in wrapped:
                if y <= bottom_margin:
                    pdf.showPage()
                    pdf.setFont("Helvetica", 10)
                    y = page_height - top_margin
                pdf.drawString(left_margin, y, segment)
                y -= line_height

        pdf.showPage()
        pdf.save()
        return buffer.getvalue()

    @staticmethod
    def _convert_non_pdf_to_preview_pdf(
        *, content: bytes, mime_type: str, filename: str
    ) -> bytes:
        normalized_mime = (mime_type or "").lower()
        suffix = Path(filename or "").suffix.lower()

        if normalized_mime.startswith("image/"):
            return AttachmentService._convert_image_to_pdf_bytes(content, title=filename)

        if AttachmentService._is_office_source(normalized_mime, filename):
            return AttachmentService._convert_office_to_pdf_bytes(
                content,
                filename=filename,
                mime_type=normalized_mime,
            )

        if normalized_mime in AttachmentService.HTML_MIME_TYPES or suffix in {".html", ".htm"}:
            html_content = content.decode("utf-8", errors="replace")
            if not html_content.strip():
                raise ValueError("HTML conversion produced empty output")
            return AttachmentService._convert_html_to_pdf_bytes(html_content, title=filename)

        if normalized_mime in AttachmentService.TEXT_MIME_TYPES or suffix in {
            ".txt",
            ".md",
            ".csv",
            ".json",
        }:
            return AttachmentService._convert_text_to_pdf_bytes(content, title=filename)

        from app.utils.document_converter import convert_document_to_html

        html_content = convert_document_to_html(content, mime_type, filename) or ""
        normalized_html = html_content.strip()
        if not normalized_html:
            raise ValueError("Content conversion produced empty output")

        if AttachmentService._is_conversion_error_html(normalized_html):
            raise ValueError(normalized_html)

        return AttachmentService._convert_html_to_pdf_bytes(normalized_html, title=filename)

    @staticmethod
    def _load_preview_pdf_bytes_for_attachment(attachment: Attachment) -> bytes:
        preview_key = (attachment.preview_pdf_storage_key or "").strip()
        if preview_key:
            local_path = AttachmentService._resolve_local_attachment_path(
                attachment, attachment.document_id
            )
            if preview_key == (attachment.storage_key or attachment.storage_path or "") and local_path:
                with open(local_path, "rb") as file_obj:
                    return file_obj.read()

            if os.path.exists(preview_key):
                with open(preview_key, "rb") as file_obj:
                    return file_obj.read()

            storage = get_storage_backend()
            return storage.download(preview_key)

        # For legacy PDF rows, fall back to original bytes.
        return AttachmentService._load_original_bytes_for_attachment(attachment)

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

            if not (preview_artifact.mime_type or "application/pdf").lower().startswith(
                "application/pdf"
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
        elif (
            (not reader_artifact.status)
            or (
                reader_artifact.status == AttachmentService.READER_STATUS_PENDING
                and not reader_artifact.content_text
            )
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
        current_user: User,
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
            if (
                preview_ref
                and preview_ref not in {storage_ref, attachment.storage_path}
            ):
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

    @staticmethod
    def open_preview_stream(
        db: Session, document_id: int, attachment_id: int, current_user: User
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
            return attachment, AttachmentService._stream_file(local_path), "application/pdf", int(size)

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
