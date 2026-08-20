"""Build a version's table of contents from the bytes it was converted from.

``convert_document_to_html`` returns a string, so by the time a version row is
written the structure the source declared is already gone. Rather than widen that
contract, this reads the structure from the same bytes, choosing whichever source
the format actually declares:

- DOCX states its contents outright, on the page Word generates, with the number,
  title and page of every heading.
- PDF states a bookmark outline, which is authoritative but often shallow, so
  detected headings fill in below it.

Anything else returns nothing, and the caller stores no table of contents rather
than an invented one.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_PDF_MIME = "application/pdf"


def build_version_toc(content: bytes, mime_type: str, filename: str = "") -> list[dict[str, Any]]:
    """Return TOC entries for ``content``, or an empty list when it declares none."""
    kind = _resolve_kind(mime_type, filename)
    if kind is None or not content:
        return []

    try:
        if kind == "docx":
            return _docx_toc(content)
        return _pdf_toc(content)
    except Exception:  # policy: DEGRADED — an absent contents page must not fail an upload
        logger.warning("Table of contents unavailable for %s", filename or kind, exc_info=True)
        return []


def _resolve_kind(mime_type: str, filename: str) -> str | None:
    normalized = (mime_type or "").lower()
    suffix = (filename or "").lower().rsplit(".", 1)[-1] if "." in (filename or "") else ""
    if normalized == _DOCX_MIME or suffix == "docx":
        return "docx"
    if normalized == _PDF_MIME or suffix == "pdf":
        return "pdf"
    return None


def _docx_toc(content: bytes) -> list[dict[str, Any]]:
    from app.conversion.document_toc import build_toc_from_docx_structure
    from app.conversion.docx_structure import extract_docx_structure

    structure = extract_docx_structure(content)
    if structure.error:
        return []
    return build_toc_from_docx_structure(structure)


def _pdf_toc(content: bytes) -> list[dict[str, Any]]:
    from app.conversion.document_toc import build_toc_from_layout
    from app.conversion.pdf_layout import extract_layout_document

    layout = extract_layout_document(content)
    if layout.error:
        return []
    return build_toc_from_layout(layout)
