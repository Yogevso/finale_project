"""Legacy helper shims for non-reader document conversion paths."""

from __future__ import annotations

import html
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def convert_word_to_html(content: bytes) -> str:
    """Convert legacy Word content to HTML when the structured DOCX path is unavailable."""
    try:
        import mammoth
    except ImportError:
        logger.error("mammoth not installed")
        return "<p>Word conversion not available. Please install mammoth.</p>"

    try:
        result = mammoth.convert_to_html(io.BytesIO(content))
        extracted_html = result.value.strip()
        if extracted_html:
            return extracted_html
        return "<p>No content could be extracted from this document.</p>"
    except Exception as exc:  # policy: DEGRADED — conversion falls back to simpler extraction on unexpected parser failures
        logger.error("Word conversion error: %s", exc)
        return convert_word_to_html_fallback(content)


def convert_word_to_html_fallback(content: bytes) -> str:
    """Fallback Word conversion using python-docx for simple paragraph extraction."""
    try:
        from docx import Document
    except ImportError:
        return "<p>Word conversion not available.</p>"

    try:
        document = Document(io.BytesIO(content))
        html_parts: list[str] = []

        for paragraph in document.paragraphs:
            text = paragraph.text.strip()
            if not text:
                continue

            style_name = (
                paragraph.style.name if paragraph.style and paragraph.style.name else ""
            ).lower()
            escaped_text = html.escape(text)
            if "heading 1" in style_name or "title" in style_name:
                html_parts.append(f"<h1>{escaped_text}</h1>")
            elif "heading 2" in style_name:
                html_parts.append(f"<h2>{escaped_text}</h2>")
            elif "heading 3" in style_name:
                html_parts.append(f"<h3>{escaped_text}</h3>")
            else:
                html_parts.append(f"<p>{escaped_text}</p>")

        return "\n".join(html_parts) if html_parts else "<p>No content found.</p>"
    except (
        Exception
    ) as exc:  # policy: DEGRADED — conversion falls back to a safe HTML error fragment
        logger.error("Word fallback conversion error: %s", exc)
        return f"<p>Error converting Word document: {html.escape(str(exc))}</p>"


def convert_text_to_html(content: bytes) -> str:
    """Convert plain text-like content into simple HTML paragraphs."""
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1", errors="replace")

    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n")]
    html_parts: list[str] = []
    for paragraph in paragraphs:
        if not paragraph:
            continue
        html_parts.append(f"<p>{html.escape(paragraph).replace(chr(10), '<br>')}</p>")

    return "\n".join(html_parts) if html_parts else "<p>No content.</p>"


def convert_document_to_html(content: bytes, mime_type: str, filename: str = "") -> Optional[str]:
    """Delegate document-to-HTML selection to the conversion pipeline."""
    from app.conversion import get_document_conversion_pipeline

    return get_document_conversion_pipeline().convert_document_to_html(
        content,
        mime_type,
        filename,
    )


__all__ = [
    "convert_document_to_html",
    "convert_text_to_html",
    "convert_word_to_html",
    "convert_word_to_html_fallback",
]
