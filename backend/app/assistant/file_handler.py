"""Handle file uploads for the AI assistant chat."""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

import pdfplumber
from fastapi import UploadFile

from app.assistant.rag.chunker import DocumentChunker
from app.config import settings
from app.models import AssistantUploadedFile

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("data/uploads/assistant")

ALLOWED_EXTENSIONS: dict[str, str] = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".md": "text/markdown",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class AssistantFileHandler:
    """Save, validate, and extract text from assistant uploads."""

    async def save_upload(
        self,
        file: UploadFile,
        user_id: int,
        db,
    ) -> AssistantUploadedFile:
        """Validate, save file to disk, extract text, and create DB record."""
        original = file.filename or "unknown"
        ext = Path(original).suffix.lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"File type '{ext}' not allowed. "
                f"Accepted: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        data = await file.read()
        if len(data) > MAX_FILE_SIZE:
            raise ValueError(f"File too large ({len(data)} bytes). Max is {MAX_FILE_SIZE} bytes.")

        # Generate unique filename
        uid = uuid.uuid4().hex[:16]
        safe_name = f"{uid}{ext}"

        # Ensure upload directory exists
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        dest = UPLOAD_DIR / safe_name
        dest.write_bytes(data)

        # Extract text
        extracted = self._extract_text(data, ext, str(dest))

        record = AssistantUploadedFile(
            user_id=user_id,
            filename=safe_name,
            original_filename=original,
            mime_type=ALLOWED_EXTENSIONS.get(ext, "application/octet-stream"),
            file_size=len(data),
            storage_path=str(dest),
            extracted_text=extracted,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def _extract_text(self, data: bytes, ext: str, path: str) -> str | None:
        """Extract plain text from file bytes based on extension."""
        try:
            if ext == ".txt" or ext == ".csv" or ext == ".md":
                return data.decode("utf-8", errors="replace")[:50000]

            if ext == ".pdf":
                return self._extract_pdf(path)

            if ext == ".docx":
                return self._extract_docx(data)

            if ext == ".pptx":
                return self._extract_pptx(data)

        except Exception as exc:
            logger.warning("Text extraction failed for %s: %s", path, exc)
            return None
        return None

    def _extract_pdf(self, path: str) -> str:
        """Extract text from PDF using pdfplumber."""
        pages: list[str] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages[:100]:  # cap at 100 pages
                text = page.extract_text()
                if text:
                    pages.append(text)
        return "\n\n".join(pages)[:50000]

    def _extract_docx(self, data: bytes) -> str:
        """Extract text from DOCX via existing extractor."""
        from app.conversion.docx_extractor import DocxExtractor

        extractor = DocxExtractor()
        result = extractor.extract_bytes(data, source_name="upload.docx")
        if result.html:
            return DocumentChunker.strip_html(result.html)[:50000]
        return ""

    def _extract_pptx(self, data: bytes) -> str:
        """Extract text from PPTX via existing extractor."""
        from app.conversion.pptx_extractor import PptxExtractor

        extractor = PptxExtractor()
        result = extractor.extract_bytes(data, source_name="upload.pptx")
        if result.html:
            return DocumentChunker.strip_html(result.html)[:50000]
        return ""

    def get_file(self, file_id: int, user_id: int, db) -> AssistantUploadedFile | None:
        """Get a file record, scoped to the owning user."""
        return (
            db.query(AssistantUploadedFile)
            .filter(
                AssistantUploadedFile.id == file_id,
                AssistantUploadedFile.user_id == user_id,
            )
            .first()
        )
