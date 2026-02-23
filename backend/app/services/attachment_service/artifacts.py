"""Artifact conversion and byte handling helpers."""

from __future__ import annotations

import html
import io
import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from app.config import settings
from app.models import Attachment

from .common import AttachmentServiceCommonMixin, get_storage_backend

logger = logging.getLogger(__name__)

AttachmentService = None  # Assigned by package facade at import time.


class AttachmentServiceArtifactsMixin(AttachmentServiceCommonMixin):
    """Storage and conversion internals used by preview/reader flows."""

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
    def _convert_office_to_pdf_bytes(
        content: bytes, *, filename: str, mime_type: str = ""
    ) -> bytes:
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
            wrapped = [
                line[i : i + max_chars_per_line] for i in range(0, len(line), max_chars_per_line)
            ]
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
    def _convert_non_pdf_to_preview_pdf(*, content: bytes, mime_type: str, filename: str) -> bytes:
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
            if (
                preview_key == (attachment.storage_key or attachment.storage_path or "")
                and local_path
            ):
                with open(local_path, "rb") as file_obj:
                    return file_obj.read()

            if os.path.exists(preview_key):
                with open(preview_key, "rb") as file_obj:
                    return file_obj.read()

            storage = get_storage_backend()
            return storage.download(preview_key)

        # For legacy PDF rows, fall back to original bytes.
        return AttachmentService._load_original_bytes_for_attachment(attachment)
