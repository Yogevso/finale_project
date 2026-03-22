"""Shared constants and core attachment retrieval helpers."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Iterator, List, Optional

from fastapi import BackgroundTasks, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.domain.value_objects import SemanticVersion
from app.models import Attachment, AttachmentArtifact, Document, DocumentVisibility, User, UserRole
from app.services.permissions import (
    Permission,
    can_view_document,
    has_permission,
    is_internal_user,
)

logger = logging.getLogger(__name__)


def get_storage_backend():
    """Lazy import to avoid boto3 dependency when not using S3"""
    from app.services.storage_service import get_storage_backend as _get_backend

    return _get_backend()


class AttachmentServiceCommonMixin:
    """Core constants and shared attachment lookup logic."""

    # Allowed MIME types
    ALLOWED_TYPES = {
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/pdf",
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
    STRUCTURED_READER_MIME_TYPES = {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/pdf",
    }
    OFFICE_EXTENSIONS = {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}
    WORD_EXTENSIONS = {".doc", ".docx"}
    STRUCTURED_READER_EXTENSIONS = {".docx", ".pptx", ".pdf"}
    TEXT_MIME_TYPES = {
        "text/plain",
        "text/markdown",
        "text/csv",
        "application/json",
    }
    HTML_MIME_TYPES = {"text/html"}

    # AD-017: magic byte signatures for content-based validation
    _MAGIC_SIGNATURES: dict[str, list[bytes]] = {
        ".png": [b"\x89PNG\r\n\x1a\n"],
        ".jpg": [b"\xff\xd8\xff"],
        ".jpeg": [b"\xff\xd8\xff"],
        ".gif": [b"GIF87a", b"GIF89a"],
        ".webp": [b"RIFF"],  # RIFF....WEBP — additional WEBP check at offset 8 below
        # Office Open XML / ZIP-based formats share the ZIP header
        ".docx": [b"PK\x03\x04"],
        ".xlsx": [b"PK\x03\x04"],
        ".pptx": [b"PK\x03\x04"],
        # Legacy Office formats use OLE2 compound document header
        ".doc": [b"\xd0\xcf\x11\xe0"],
        ".xls": [b"\xd0\xcf\x11\xe0"],
        ".ppt": [b"\xd0\xcf\x11\xe0"],
        # PDF
        ".pdf": [b"%PDF"],
    }

    @classmethod
    def _validate_magic_bytes(cls, content: bytes, original_filename: str, content_type: str) -> None:
        """Reject uploads whose magic bytes contradict the file extension.

        Files with a known extension must have matching magic bytes.
        Text-ish formats (.txt, .md, .csv, .json, .html) have no signature check.
        """
        file_ext = Path(original_filename).suffix.lower()
        sigs = cls._MAGIC_SIGNATURES.get(file_ext)
        if sigs is None:
            return
        if len(content) < 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too small to be a valid {file_ext} file: {original_filename}",
            )
        if not any(content[:len(sig)] == sig for sig in sigs):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File content does not match extension {file_ext}: {original_filename}",
            )
        # WebP: RIFF header is shared with AVI/WAV, verify "WEBP" at offset 8
        if file_ext == ".webp":
            if len(content) < 12 or content[8:12] != b"WEBP":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File content does not match extension {file_ext}: {original_filename}",
                )

    @classmethod
    def get_upload_dir(cls) -> Path:
        """Get upload directory path"""
        upload_dir = (
            Path(settings.UPLOAD_DIR) if hasattr(settings, "UPLOAD_DIR") else Path("data/uploads")
        )
        upload_dir.mkdir(parents=True, exist_ok=True)
        return upload_dir

    @classmethod
    def _supports_structured_reader_artifact(cls, mime_type: str, filename: str) -> bool:
        normalized_mime = (mime_type or "").lower()
        suffix = Path(filename or "").suffix.lower()
        return (
            normalized_mime in cls.STRUCTURED_READER_MIME_TYPES
            or suffix in cls.STRUCTURED_READER_EXTENSIONS
        )

    @staticmethod
    def _next_patch_semver(raw_value: Optional[str], fallback_version_number: int) -> str:
        return str(
            SemanticVersion.from_raw(raw_value, fallback_version_number).bump_patch()
        )

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

    @classmethod
    def _apply_existing_artifacts_to_attachment(cls, db: Session, attachment: Attachment) -> None:
        cls._apply_existing_artifacts_to_attachments(db, [attachment])

    @classmethod
    def _apply_existing_artifacts_to_attachments(
        cls, db: Session, attachments: List[Attachment]
    ) -> None:
        if not attachments:
            return

        attachment_ids = [attachment.id for attachment in attachments]
        artifacts = (
            db.query(AttachmentArtifact)
            .filter(AttachmentArtifact.attachment_id.in_(attachment_ids))
            .all()
        )

        artifact_map: dict[int, dict[str, AttachmentArtifact]] = {}
        for artifact in artifacts:
            artifact_map.setdefault(artifact.attachment_id, {})[artifact.kind] = artifact

        for attachment in attachments:
            by_kind = artifact_map.get(attachment.id, {})
            cls._apply_reader_artifact_to_attachment(
                attachment, by_kind.get(cls.ARTIFACT_KIND_READER_HTML)
            )

    @classmethod
    def _ensure_artifact_rows(
        cls,
        db: Session,
        attachment: Attachment,
        *,
        persist: bool = False,
    ) -> AttachmentArtifact:
        """Backfill reader artifact rows from attachment columns when needed."""
        reader_artifact = cls._get_artifact_record(db, attachment.id, cls.ARTIFACT_KIND_READER_HTML)
        if not reader_artifact:
            reader_artifact = AttachmentArtifact(
                attachment_id=attachment.id,
                kind=cls.ARTIFACT_KIND_READER_HTML,
                status=attachment.reader_html_status or cls.READER_STATUS_PENDING,
                content_text=attachment.reader_html_content,
                content_json=attachment.reader_toc_json,
                source=attachment.reader_toc_source,
                error=attachment.reader_html_error,
                generated_at=attachment.reader_html_generated_at,
            )
            db.add(reader_artifact)

        cls._apply_reader_artifact_to_attachment(attachment, reader_artifact)

        if persist:
            db.commit()
            db.refresh(attachment)
            db.refresh(reader_artifact)

        return reader_artifact

    @classmethod
    def _chunk_bytes(cls, data: bytes, chunk_size: Optional[int] = None) -> Iterator[bytes]:
        resolved_chunk_size = chunk_size or cls.STREAM_CHUNK_SIZE
        offset = 0
        while offset < len(data):
            next_offset = offset + resolved_chunk_size
            yield data[offset:next_offset]
            offset = next_offset

    @classmethod
    def _stream_file(cls, file_path: str, chunk_size: Optional[int] = None) -> Iterator[bytes]:
        resolved_chunk_size = chunk_size or cls.STREAM_CHUNK_SIZE
        with open(file_path, "rb") as file_obj:
            while True:
                chunk = file_obj.read(resolved_chunk_size)
                if not chunk:
                    break
                yield chunk

    @classmethod
    def _resolve_local_attachment_path(
        cls, attachment: Attachment, document_id: int
    ) -> Optional[str]:
        storage_ref = attachment.storage_key or attachment.storage_path

        # Try storage key/path as-is first (might be an absolute path).
        if storage_ref and os.path.exists(storage_ref):
            return storage_ref

        upload_dir = cls.get_upload_dir()

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
    def _enforce_attachment_access(document: Document, current_user: Optional[User]) -> None:
        """Enforce attachment access constraints through one code path."""
        if current_user is None:
            # Anonymous/public flows are governed by caller-specific route rules.
            # Defence-in-depth: only PUBLIC documents should be accessible without auth.
            if document.visibility != DocumentVisibility.PUBLIC:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Authentication required to access this document's attachments",
                )
            return

        if not can_view_document(current_user, document):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this document",
            )

        # Internal users are tenant-scoped unless explicitly global.
        if is_internal_user(current_user) and current_user.role != UserRole.SYSTEM_ADMIN:
            if (
                document.tenant_id is not None
                and current_user.tenant_id is not None
                and document.tenant_id != current_user.tenant_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to access attachments for this tenant",
                )

        if not has_permission(current_user, Permission.DOWNLOAD_ATTACHMENTS):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access attachments",
            )

    @classmethod
    def _get_document_for_attachment_access(
        cls,
        db: Session,
        document_id: int,
        current_user: Optional[User],
    ) -> Document:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        cls._enforce_attachment_access(document, current_user)
        return document

    @classmethod
    def get_attachments(cls, db: Session, document_id: int, current_user: User) -> List[Attachment]:
        """Get all attachments for a document"""
        cls._get_document_for_attachment_access(db, document_id, current_user)
        attachments = (
            db.query(Attachment)
            .filter(Attachment.document_id == document_id)
            .order_by(Attachment.uploaded_at.desc())
            .all()
        )
        cls._apply_existing_artifacts_to_attachments(db, attachments)
        return attachments

    @classmethod
    def get_attachment(
        cls,
        db: Session,
        document_id: int,
        attachment_id: int,
        current_user: Optional[User] = None,
    ) -> Attachment:
        """Get a specific attachment"""
        cls._get_document_for_attachment_access(db, document_id, current_user)

        attachment = (
            db.query(Attachment)
            .filter(Attachment.id == attachment_id, Attachment.document_id == document_id)
            .first()
        )

        if not attachment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found"
            )

        cls._apply_existing_artifacts_to_attachment(db, attachment)
        return attachment

    @classmethod
    async def upload_attachment(
        cls,
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
            content_type not in cls.ALLOWED_TYPES
            and file_ext not in allowed_extensions
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed: {content_type}",
            )

        # Read file content
        content = await file.read()

        # AD-017: validate uploaded file magic bytes match the declared type
        cls._validate_magic_bytes(content, file_ext, original_filename)

        attachment = cls.create_attachment_from_bytes(
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
