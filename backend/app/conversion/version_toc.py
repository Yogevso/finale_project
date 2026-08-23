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
import re
from html.parser import HTMLParser
from typing import Any

logger = logging.getLogger(__name__)

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_PDF_MIME = "application/pdf"
# A heading tag, h1 through h6.
_HEADING_TAG_RE = re.compile(r"^h[1-6]$", re.I)
# A leading section number: "2", "1.1", "3.2.4".
_NUMBER_PREFIX_RE = re.compile(r"^(\d+(?:\.\d+)*)\s+\S")


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


def derive_version_toc(
    html: str | None,
    previous_toc: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Rebuild the contents from edited HTML, keeping what the source declared.

    An edit produces HTML, not the original file, so the contents cannot be read
    from a DOCX contents page again. Carrying the previous list forward unchanged
    would be wrong the moment a heading is added, renamed or removed; recomputing
    from scratch would throw away the page numbers, which HTML never holds.

    So the headings come from the new HTML and the pages come from the previous
    entries, matched on the anchor id that both share. A heading Word numbered
    keeps its number: the number lives only in the old title, and an editor who
    renames "Release Kit Summary" to "Release Kit Summary+draft" means to keep
    being section 1.
    """
    headings = _parse_headings(html or "")
    if not headings:
        return []

    previous_by_anchor: dict[str, dict[str, Any]] = {}
    for entry in previous_toc or []:
        anchor = str(entry.get("anchor_id") or "").strip()
        if anchor:
            previous_by_anchor[anchor] = entry

    items: list[dict[str, Any]] = []
    for anchor, level, text in headings:
        previous = previous_by_anchor.get(anchor) or {}
        page = previous.get("page")
        title = _restore_numbering(text, str(previous.get("title") or ""))
        items.append(
            {
                "id": f"toc-{len(items)}",
                "title": title,
                "level": level,
                "page": page if isinstance(page, int) and page > 0 else len(items) + 1,
                "page_start": page if isinstance(page, int) and page > 0 else len(items) + 1,
                "page_end": None,
                "anchor_id": anchor or None,
            }
        )
    return items


def _restore_numbering(text: str, previous_title: str) -> str:
    """Re-attach the section number an edited heading no longer carries."""
    text = text.strip()
    if not text or _NUMBER_PREFIX_RE.match(text):
        return text
    match = _NUMBER_PREFIX_RE.match(previous_title.strip())
    return f"{match.group(1)} {text}" if match else text


class _HeadingCollector(HTMLParser):
    """Collect ``(anchor id, level, text)`` for every heading in document order."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[tuple[str, int, str]] = []
        self._level: int | None = None
        self._anchor = ""
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._level is not None or not _HEADING_TAG_RE.match(tag):
            return
        self._level = int(tag[1])
        self._anchor = dict(attrs).get("id") or ""
        self._parts = []

    def handle_endtag(self, tag: str) -> None:
        if self._level is None or not _HEADING_TAG_RE.match(tag):
            return
        text = re.sub(r"\s+", " ", "".join(self._parts)).strip()
        if text:
            self.headings.append((self._anchor.strip(), self._level, text))
        self._level = None
        self._anchor = ""
        self._parts = []

    def handle_data(self, data: str) -> None:
        if self._level is not None:
            self._parts.append(data)


def _parse_headings(html: str) -> list[tuple[str, int, str]]:
    collector = _HeadingCollector()
    try:
        collector.feed(html)
    except Exception:  # policy: DEGRADED — unparseable HTML yields no contents
        logger.debug("Heading scan failed", exc_info=True)
        return []
    return collector.headings
