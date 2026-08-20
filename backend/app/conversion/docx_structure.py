"""Document structure extracted from DOCX, alongside the PDF layout model.

DOCX is a flow format: it carries no coordinates and no page boundaries, because
Word computes those when it renders. Asking it for a bounding box is meaningless.
What it does carry, and a PDF usually does not, is a full declaration of its own
structure, and on the Intel release-notes template that declaration is complete:

    Heading 1: 11   toc 1: 11        toc 1  "1\\tRelease Kit Summary\\t10"
    Heading 2: 54   toc 2: 54        toc 2  "1.1\\tRelease Kit Details\\t10"
    Heading 3: 63   toc 3: 63
    Heading 4: 30   toc 4: 30

The ``toc N`` paragraphs are the contents page Word generated, and each holds the
number, the title and the page in tab-separated fields. They are the DOCX
counterpart of a PDF outline, and unlike the four shallow bookmarks the GCC guide
ships, they cover every heading in the document at its true depth.

Two consequences shape this module:

- Heading paragraphs do *not* contain their own numbers. Word draws those from
  the numbering definition at render time, so ``paragraph.text`` yields "Release
  Kit Summary", never "1 Release Kit Summary". The numbering exists literally
  only in the contents entries, which is why they lead.
- The contents entries are body paragraphs. Left in the content they render as a
  wall of dotted leader lines, which is what the frontend currently tries to
  strip back out by guesswork. Lifting them into the structure removes the guess.
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from docx import Document as DocxDocument

logger = logging.getLogger(__name__)

# "Heading 3" / "heading3"; the trailing digit is the level Word assigned.
_HEADING_STYLE_RE = re.compile(r"^heading\s*([1-9])$")
# "toc 3" / "toc3": one line of the generated contents page, at that depth.
_TOC_STYLE_RE = re.compile(r"^toc\s*([1-9])$")
# A leading section number: "2", "1.1", "3.2.4".
_NUMBER_RE = re.compile(r"^\d+(?:\.\d+)*$")
# Dotted leaders sit between a contents title and its page number.
_LEADER_RE = re.compile(r"[.…]{2,}")


@dataclass(slots=True)
class TocEntry:
    """One line of the document's own contents page."""

    level: int
    title: str
    number: str | None = None
    page: int | None = None
    node_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "title": self.title,
            "number": self.number,
            "page": self.page,
            "node_id": self.node_id,
        }


@dataclass(slots=True)
class StructureNode:
    """A heading in the body, addressable by a stable id."""

    id: str
    type: str  # "heading"
    level: int
    text: str
    style: str
    index: int
    number: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "level": self.level,
            "text": self.text,
            "number": self.number,
        }


@dataclass(slots=True)
class DocumentStructure:
    """Headings and contents, separated from the rendered body."""

    nodes: list[StructureNode] = field(default_factory=list)
    toc: list[TocEntry] = field(default_factory=list)
    toc_paragraph_indexes: set[int] = field(default_factory=set)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def headings(self) -> list[StructureNode]:
        return [node for node in self.nodes if node.type == "heading"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "toc": [entry.to_dict() for entry in self.toc],
            "warnings": list(self.warnings),
        }


def _style_name(paragraph: Any) -> str:
    style = getattr(paragraph, "style", None)
    return ((getattr(style, "name", None) or "").strip()).lower()


def normalize_title(value: str) -> str:
    """Compare titles without numbering, leaders or punctuation noise."""
    without_leaders = _LEADER_RE.sub(" ", value)
    without_number = re.sub(r"^\d+(?:\.\d+)*\s+", "", without_leaders.strip())
    return re.sub(r"[^a-z0-9]+", " ", without_number.lower()).strip()


def parse_toc_line(text: str) -> tuple[str | None, str, int | None]:
    """Split a contents line into its number, title and page.

    Word writes the three as tab-separated fields, but a document edited by hand
    may use dotted leaders instead, so both are accepted.
    """
    fields = [part.strip() for part in text.split("\t") if part.strip()]
    if len(fields) < 2:
        fields = [part.strip() for part in _LEADER_RE.split(text) if part.strip()]

    number: str | None = None
    page: int | None = None

    if fields and _NUMBER_RE.match(fields[0]):
        number = fields[0]
        fields = fields[1:]
    if fields and fields[-1].isdigit():
        page = int(fields[-1])
        fields = fields[:-1]

    title = " ".join(fields).strip()
    if number is None:
        match = re.match(r"^(\d+(?:\.\d+)*)\s+(\S.*)$", title)
        if match:
            number, title = match.group(1), match.group(2).strip()
    return number, title.strip(), page


def extract_docx_structure(docx_bytes: bytes) -> DocumentStructure:
    """Build a :class:`DocumentStructure` from raw DOCX bytes."""
    structure = DocumentStructure()
    try:
        document = DocxDocument(io.BytesIO(docx_bytes))
    except Exception as exc:  # policy: FAIL_FAST — an unreadable DOCX is a stable error
        structure.error = f"Failed to open DOCX: {exc}"
        return structure

    seen_ids: dict[str, int] = {}

    for index, paragraph in enumerate(document.paragraphs):
        text = paragraph.text.strip()
        if not text:
            continue
        style = _style_name(paragraph)

        toc_match = _TOC_STYLE_RE.match(style)
        if toc_match is not None:
            number, title, page = parse_toc_line(text)
            if title:
                structure.toc.append(
                    TocEntry(level=int(toc_match.group(1)), title=title, number=number, page=page)
                )
            structure.toc_paragraph_indexes.add(index)
            continue

        heading_match = _HEADING_STYLE_RE.match(style)
        if heading_match is None:
            continue

        node_id = _stable_id(text, seen_ids)
        structure.nodes.append(
            StructureNode(
                id=node_id,
                type="heading",
                level=int(heading_match.group(1)),
                text=text,
                style=style,
                index=index,
            )
        )

    _link_toc_to_nodes(structure)
    return structure


def _stable_id(text: str, seen: dict[str, int]) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "section"
    base = f"heading-{slug}"
    seen[base] = seen.get(base, 0) + 1
    return base if seen[base] == 1 else f"{base}-{seen[base]}"


def _link_toc_to_nodes(structure: DocumentStructure) -> None:
    """Point every contents entry at the heading it names.

    Matching walks forward through the headings so that repeated titles - which
    Intel templates use freely, e.g. "Important Notes" under several chapters -
    bind to successive headings rather than all collapsing onto the first.
    """
    by_title: dict[str, list[StructureNode]] = {}
    for node in structure.headings:
        by_title.setdefault(normalize_title(node.text), []).append(node)

    consumed: dict[str, int] = {}
    for entry in structure.toc:
        key = normalize_title(entry.title)
        candidates = by_title.get(key, [])
        position = consumed.get(key, 0)

        match = None
        for offset in range(position, len(candidates)):
            if candidates[offset].level == entry.level:
                match = candidates[offset]
                consumed[key] = offset + 1
                break
        if match is None and position < len(candidates):
            match = candidates[position]
            consumed[key] = position + 1

        if match is not None:
            entry.node_id = match.id
            if entry.number and not match.number:
                # Word renders heading numbers from the numbering definition, so
                # the literal number survives only in the contents entry.
                match.number = entry.number
