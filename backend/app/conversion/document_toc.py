"""One table of contents, built from what a document declares about itself.

``reader_artifact`` used to number TOC pages like this::

    page_number = getattr(heading, "slide_number", None) or (index + 1)

``slide_number`` belongs to PPTX. For DOCX it is always ``None``, so every entry
fell through to its own ordinal position: the first heading was labelled page 1,
the fifty-seventh page 57. Measured against the Intel release notes, 156 of 158
entries carried a page number the document never claimed - the contents ran to
"page 158" in a document 109 pages long.

The page numbers are not missing. A DOCX contents page states them outright, and
a PDF outline states them per bookmark. This module reads them from there, and
falls back to the ordinal only when a document truly declares nothing.

Output matches ``AttachmentOutlineItem`` so it drops into the existing reader
contract unchanged. ``anchor_id`` carries the stable heading id, which is what
turns navigation into a direct lookup instead of a text search.
"""

from __future__ import annotations

import re
from typing import Any

# Where an entry's page number came from, for diagnostics and for choosing
# between competing sources.
SOURCE_DOCX_CONTENTS = "docx-contents"
SOURCE_PDF_OUTLINE = "pdf-outline"
SOURCE_HEADINGS = "headings"


def _item(
    index: int,
    title: str,
    level: int,
    page: int | None,
    anchor_id: str | None,
    number: str | None = None,
) -> dict[str, Any]:
    resolved_page = page if isinstance(page, int) and page > 0 else index + 1
    # The number is part of how a contents line reads, and folding it into the
    # title surfaces it without widening the response contract.
    display = f"{number} {title}".strip() if number else title.strip()
    return {
        "id": f"toc-{index}",
        "title": display,
        "level": max(1, int(level or 1)),
        "page": resolved_page,
        "page_start": resolved_page,
        "page_end": None,
        "anchor_id": (anchor_id or "").strip() or None,
    }


def build_toc_from_docx_structure(structure: Any) -> list[dict[str, Any]]:
    """Build the TOC from the contents page Word generated.

    Entries already carry their number, title and page, and were linked to a
    heading id when the structure was read, so nothing here needs to guess.
    """
    entries = list(getattr(structure, "toc", []) or [])
    items: list[dict[str, Any]] = []
    for entry in entries:
        title = str(getattr(entry, "title", "") or "").strip()
        if not title:
            continue
        items.append(
            _item(
                index=len(items),
                title=title,
                level=getattr(entry, "level", 1),
                page=getattr(entry, "page", None),
                anchor_id=getattr(entry, "node_id", None),
                number=getattr(entry, "number", None),
            )
        )
    return items


def build_toc_from_layout(document: Any) -> list[dict[str, Any]]:
    """Build the TOC for a PDF, preferring its own outline over detection.

    A PDF outline is authoritative but often shallow - the Intel GCC guide ships
    four level-one bookmarks for twenty pages - so detected headings fill in
    below it. Detected headings are only added where the outline is silent.
    """
    outline = list(getattr(document, "outline", []) or [])
    headings = list(getattr(document, "headings", []) or [])

    items: list[dict[str, Any]] = []
    claimed_pages: set[int] = set()

    for entry in outline:
        title = str(getattr(entry, "title", "") or "").strip()
        if not title:
            continue
        page = int(getattr(entry, "page", 0) or 0)
        anchor = _anchor_for_outline_entry(headings, title, page)
        items.append(
            _item(
                index=len(items),
                title=title,
                level=getattr(entry, "level", 1),
                page=page,
                anchor_id=anchor,
            )
        )
        claimed_pages.add(page)

    for node in headings:
        page = int(getattr(node, "page", 0) or 0)
        title = str(getattr(node, "text", "") or "").strip()
        if not title or page in claimed_pages:
            continue
        items.append(
            _item(
                index=len(items),
                title=title,
                level=getattr(node, "level", 1) or 1,
                page=page,
                anchor_id=getattr(node, "id", None),
                number=getattr(node, "number", None),
            )
        )

    items.sort(key=lambda item: (item["page"], item["level"]))
    for position, item in enumerate(items):
        item["id"] = f"toc-{position}"
    return items


def _anchor_for_outline_entry(headings: list[Any], title: str, page: int) -> str | None:
    """Find the heading node an outline entry names, so the entry can point at it."""

    def normalize(value: str) -> str:
        without_number = re.sub(r"^\d+(?:\.\d+)*\s+", "", value.strip())
        return re.sub(r"[^a-z0-9]+", " ", without_number.lower()).strip()

    target = normalize(title)
    for node in headings:
        node_title = normalize(str(getattr(node, "text", "") or ""))
        if not node_title:
            continue
        same_page = abs(int(getattr(node, "page", 0) or 0) - page) <= 1
        if same_page and (node_title == target or node_title in target):
            return str(getattr(node, "id", "") or "") or None
    return None
