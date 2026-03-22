"""HTML to DOCX conversion helpers."""

from __future__ import annotations

import io
from typing import Any


def _html2docx_document(html: str) -> Any:
    """
    Convert HTML to a python-docx Document.
    Uses html2docx if available.
    """
    try:
        from html2docx import html2docx  # type: ignore

        doc = html2docx(html)
        return doc
    except Exception:
        # Fallback for alternate API style
        try:
            from html2docx import HTML2Docx  # type: ignore

            parser = HTML2Docx()
            doc = parser.parse_html_string(html)
            return doc
        except Exception as exc:
            raise RuntimeError("html2docx conversion failed") from exc


def html_to_docx_bytes(html: str) -> bytes:
    """Convert HTML string to DOCX bytes."""
    from app.utils.sanitization import sanitize_html_content

    safe_html = sanitize_html_content(html) or ""
    doc = _html2docx_document(safe_html)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.read()
