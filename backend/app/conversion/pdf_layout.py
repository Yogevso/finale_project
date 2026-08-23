"""Layout-preserving PDF extraction.

``pdf_to_docx`` reads span coordinates, uses them to sort blocks into reading
order and then discards them: the DOCX it produces is a flow document, so page
boundaries, positions, fonts and weights cannot be recovered downstream. This
module is the parallel path that keeps that information.

It produces a :class:`LayoutDocument` whose nodes carry *both* halves of the
problem at once — semantic fields (type, level, text) for the document model and
the table of contents, and layout fields (page, bbox, font signature) for
high-fidelity rendering. One node, one stable id, used by both.

Two properties of real Intel documents drive the design:

- A section heading is split across spans on the same line, with the number far
  to the left of the title ("2" at x=76, "Key Known Issues" at x=141). Joining
  spans without regard to the gap yields "2Key Known Issues" and destroys the
  numbering signal entirely, so joining is gap-aware.
- The running header repeats the *current chapter's* title, so its text changes
  every few pages. Detecting chrome by repeated text misses it; it is detected
  by a repeated font signature and position instead, and the text it carries is
  kept, because it maps every page to the section that owns it.
"""

from __future__ import annotations

import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# A subset-embedded font is exposed as "ORIAAM+Verdana"; the tag is not identity.
_SUBSET_PREFIX = re.compile(r"^[A-Z]{6}\+")
# PyMuPDF span flag bits.
_FLAG_ITALIC = 1 << 1
_FLAG_BOLD = 1 << 4
# Gap between two spans, as a fraction of font size, that means "there was space
# here" rather than "these characters are adjacent".
_WORD_GAP_RATIO = 0.25
# Band at the top/bottom of a page where running headers and footers live. The
# Intel template puts its running header at y~86, below a 72pt margin.
_CHROME_TOP_BAND_PT = 110.0
_CHROME_BOTTOM_BAND_PT = 72.0
# Two lines whose baselines differ by less than this are one visual line that
# PyMuPDF happened to split, e.g. a heading number and its title.
_BASELINE_TOLERANCE_PT = 2.0
# A position+font signature seen on at least this fraction of pages is chrome.
_CHROME_PAGE_RATIO = 0.5
# Minimum pages before repetition means anything.
_MIN_PAGES_FOR_CHROME = 4
# How far below the outermost repeated line still counts as the same chrome.
_CHROME_EDGE_TOLERANCE_PT = 10.0
# A heading must be at least this much larger than body text.
_HEADING_SIZE_RATIO = 1.25
# Headings are short; longer runs set large are pull quotes or cover copy.
_MAX_HEADING_CHARS = 140
# Leading number in a heading: "2", "1.1", "3.2.4".
_HEADING_NUMBER_RE = re.compile(r"^(\d+(?:\.\d+)*)\s+(\S.*)$")


@dataclass(slots=True)
class LayoutSpan:
    """A run of text with one font, as the PDF stores it."""

    text: str
    bbox: tuple[float, float, float, float]
    font_family: str
    font_size: float
    bold: bool
    italic: bool
    # sRGB packed into an int, as PyMuPDF reports it. Carried because a renderer
    # reading colour from the PDF separately would be a second extraction whose
    # spans could disagree with these.
    color: int = 0

    @property
    def signature(self) -> tuple[str, float, bool, bool]:
        return (self.font_family, round(self.font_size, 1), self.bold, self.italic)


@dataclass(slots=True)
class LayoutNode:
    """A semantic node that also knows where it sits on the page."""

    id: str
    type: str  # "heading" | "paragraph" | "running-header" | "running-footer"
    page: int
    bbox: tuple[float, float, float, float]
    text: str
    spans: list[LayoutSpan] = field(default_factory=list)
    level: int | None = None
    number: str | None = None
    font_family: str = ""
    font_size: float = 0.0
    bold: bool = False
    italic: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "type": self.type,
            "page": self.page,
            "bbox": list(self.bbox),
            "text": self.text,
            "font": {
                "family": self.font_family,
                "size": self.font_size,
                "bold": self.bold,
                "italic": self.italic,
            },
        }
        if self.level is not None:
            payload["level"] = self.level
        if self.number:
            payload["number"] = self.number
        return payload


@dataclass(slots=True)
class LayoutPage:
    """Page geometry, kept so rendering can reproduce real page boundaries."""

    number: int
    width: float
    height: float
    rotation: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "width": self.width,
            "height": self.height,
            "rotation": self.rotation,
        }


@dataclass(slots=True)
class OutlineEntry:
    """One entry of the PDF's own bookmark tree — the authoritative structure."""

    level: int
    title: str
    page: int

    def to_dict(self) -> dict[str, Any]:
        return {"level": self.level, "title": self.title, "page": self.page}


@dataclass(slots=True)
class LayoutDocument:
    """Everything the PDF holds, before anything is thrown away."""

    pages: list[LayoutPage] = field(default_factory=list)
    nodes: list[LayoutNode] = field(default_factory=list)
    outline: list[OutlineEntry] = field(default_factory=list)
    body_font_family: str = ""
    body_font_size: float = 0.0
    warnings: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def headings(self) -> list[LayoutNode]:
        return [node for node in self.nodes if node.type == "heading"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "pages": [page.to_dict() for page in self.pages],
            "nodes": [node.to_dict() for node in self.nodes],
            "outline": [entry.to_dict() for entry in self.outline],
            "body_font": {"family": self.body_font_family, "size": self.body_font_size},
            "warnings": list(self.warnings),
        }


def _normalize_font(name: str | None) -> str:
    return _SUBSET_PREFIX.sub("", (name or "").strip()) or "unknown"


def _span_from_raw(raw: dict[str, Any]) -> LayoutSpan | None:
    text = raw.get("text", "")
    if not text.strip():
        return None

    family = _normalize_font(raw.get("font"))
    flags = int(raw.get("flags", 0))
    lowered = family.lower()
    return LayoutSpan(
        text=text,
        bbox=tuple(float(value) for value in raw["bbox"]),  # type: ignore[arg-type]
        font_family=family,
        font_size=float(raw.get("size", 0.0)),
        bold=bool(flags & _FLAG_BOLD) or "bold" in lowered,
        italic=bool(flags & _FLAG_ITALIC) or "italic" in lowered or "oblique" in lowered,
        color=int(raw.get("color", 0) or 0),
    )


def join_spans(spans: list[LayoutSpan]) -> str:
    """Join spans into text, restoring the spaces their x-gaps stand for.

    Section headings place the number and the title in separate spans on one
    line. Concatenating them directly produces "2Key Known Issues", which no
    numbering rule can then recognise.
    """
    if not spans:
        return ""

    parts = [spans[0].text]
    for previous, current in zip(spans, spans[1:], strict=False):
        gap = current.bbox[0] - previous.bbox[2]
        threshold = max(current.font_size, previous.font_size) * _WORD_GAP_RATIO
        needs_space = gap > threshold and not previous.text.endswith(" ")
        parts.append(" " if needs_space else "")
        parts.append(current.text)
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def _collect_lines(page: Any) -> list[list[LayoutSpan]]:
    """Return the page's lines, each as its ordered list of spans."""
    try:
        raw = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE, sort=True)
    except Exception:  # policy: DEGRADED — fall back to unsorted extraction
        raw = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)

    lines: list[list[LayoutSpan]] = []
    for block in raw.get("blocks", []):
        for line in block.get("lines", []):
            spans = [
                span
                for span in (_span_from_raw(item) for item in line.get("spans", []))
                if span is not None
            ]
            if spans:
                lines.append(sorted(spans, key=lambda item: item.bbox[0]))
    return _merge_baselines(lines)


def _merge_baselines(lines: list[list[LayoutSpan]]) -> list[list[LayoutSpan]]:
    """Rejoin lines that PyMuPDF split but that render as one.

    A numbered heading is emitted as two lines - the number, then the title far
    to its right - even though both sit on the same baseline. Left apart, the
    numbering signal is unrecoverable.
    """
    merged: list[list[LayoutSpan]] = []
    for spans in sorted(lines, key=lambda item: (item[0].bbox[1], item[0].bbox[0])):
        baseline = spans[0].bbox[3]
        size = _dominant_span(spans).font_size
        if merged:
            previous = merged[-1]
            same_baseline = abs(previous[0].bbox[3] - baseline) <= _BASELINE_TOLERANCE_PT
            same_size = abs(_dominant_span(previous).font_size - size) < 0.6
            if same_baseline and same_size:
                merged[-1] = sorted(previous + spans, key=lambda item: item.bbox[0])
                continue
        merged.append(spans)
    return merged


def _line_bbox(spans: list[LayoutSpan]) -> tuple[float, float, float, float]:
    return (
        min(span.bbox[0] for span in spans),
        min(span.bbox[1] for span in spans),
        max(span.bbox[2] for span in spans),
        max(span.bbox[3] for span in spans),
    )


def _dominant_span(spans: list[LayoutSpan]) -> LayoutSpan:
    """The span that characterises a line: the largest, then the longest."""
    return max(spans, key=lambda span: (round(span.font_size, 1), len(span.text)))


def _detect_body_font(pages_lines: list[list[list[LayoutSpan]]]) -> tuple[str, float]:
    """The most-used family and size are the body text by definition."""
    usage: Counter[tuple[str, float]] = Counter()
    for lines in pages_lines:
        for spans in lines:
            for span in spans:
                usage[(span.font_family, round(span.font_size, 1))] += len(span.text)
    if not usage:
        return ("unknown", 0.0)
    (family, size), _ = usage.most_common(1)[0]
    return (family, size)


def _detect_chrome(
    pages_lines: list[list[list[LayoutSpan]]],
    pages: list[LayoutPage],
) -> set[tuple[int, int]]:
    """Find running headers and footers by repeated *placement*, not text.

    A running header carries the current chapter's title, so its text changes
    every few pages. What stays constant is the font signature and the position,
    which is what this matches on.
    """
    if len(pages_lines) < _MIN_PAGES_FOR_CHROME:
        return set()

    placements: dict[tuple[Any, ...], set[int]] = defaultdict(set)
    located: dict[tuple[Any, ...], list[tuple[int, int]]] = defaultdict(list)

    for page_index, lines in enumerate(pages_lines):
        height = pages[page_index].height
        for line_index, spans in enumerate(lines):
            bbox = _line_bbox(spans)
            in_top = bbox[1] < _CHROME_TOP_BAND_PT
            in_bottom = bbox[3] > height - _CHROME_BOTTOM_BAND_PT
            if not (in_top or in_bottom):
                continue

            # x is deliberately excluded: two-sided layouts alternate the header
            # between the left and right margin, so keying on it splits one
            # header into two placements that each miss the threshold.
            key = (
                "top" if in_top else "bottom",
                _dominant_span(spans).signature,
                round(bbox[1] / 5) * 5 if in_top else round((height - bbox[3]) / 5) * 5,
            )
            placements[key].add(page_index)
            located[key].append((page_index, line_index))

    threshold = max(_MIN_PAGES_FOR_CHROME, int(len(pages_lines) * _CHROME_PAGE_RATIO))
    repeated = {key for key, pages_seen in placements.items() if len(pages_seen) >= threshold}
    if not repeated:
        return set()

    # Content can also repeat inside the band - a table header row continued
    # across pages does. Page chrome is the *outermost* repeated line, so only
    # the band edge counts; anything below it is content that happens to repeat.
    chrome: set[tuple[int, int]] = set()
    for band in ("top", "bottom"):
        offsets = [key[2] for key in repeated if key[0] == band]
        if not offsets:
            continue
        edge = min(offsets)
        for key in repeated:
            if key[0] == band and key[2] - edge <= _CHROME_EDGE_TOLERANCE_PT:
                chrome.update(located[key])
    return chrome


def _read_outline(doc: Any, warnings: list[str]) -> list[OutlineEntry]:
    """The PDF's own bookmarks: the most reliable structure a PDF ever carries."""
    try:
        raw = doc.get_toc(simple=True)
    except Exception as exc:  # policy: DEGRADED — a missing outline is not an error
        warnings.append(f"PDF outline unavailable: {exc}")
        return []

    entries: list[OutlineEntry] = []
    for item in raw or []:
        try:
            level, title, page = int(item[0]), str(item[1]).strip(), int(item[2])
        except (TypeError, ValueError, IndexError):
            continue
        if title:
            entries.append(OutlineEntry(level=max(1, level), title=title, page=max(1, page)))
    return entries


def extract_layout_document(pdf_bytes: bytes, *, max_pages: int | None = None) -> LayoutDocument:
    """Build a :class:`LayoutDocument` from raw PDF bytes."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:  # policy: FAIL_FAST — an unreadable PDF is a stable error
        document = LayoutDocument()
        document.error = f"Failed to open PDF: {exc}"
        return document

    try:
        return extract_layout_from_document(doc, max_pages=max_pages)
    finally:
        doc.close()


def extract_layout_from_document(doc: Any, *, max_pages: int | None = None) -> LayoutDocument:
    """Extract from a document the caller already has open.

    ``pdf_fidelity`` holds the document open for the page backgrounds and the
    embedded font programs, and renders the text from these nodes. Going back to
    the bytes for a second extraction would parse the file twice and produce a
    second set of ids that the first set has no reason to agree with.

    Ownership stays with the caller: this does not close ``doc``.
    """
    document = LayoutDocument()
    page_count = len(doc)
    if page_count == 0:
        document.error = "PDF has no pages"
        return document

    # Reading stops where rendering does, so a caller that renders a prefix of a
    # very long PDF does not pay for extracting the rest.
    limit = page_count if max_pages is None else max(1, min(page_count, max_pages))

    document.pages = [
        LayoutPage(
            number=index + 1,
            width=float(doc[index].rect.width),
            height=float(doc[index].rect.height),
            rotation=int(doc[index].rotation),
        )
        for index in range(limit)
    ]
    document.outline = [
        entry for entry in _read_outline(doc, document.warnings) if entry.page <= limit
    ]
    pages_lines = [_collect_lines(doc[index]) for index in range(limit)]

    family, size = _detect_body_font(pages_lines)
    document.body_font_family = family
    document.body_font_size = size
    chrome = _detect_chrome(pages_lines, document.pages)

    for page_index, lines in enumerate(pages_lines):
        for line_index, spans in enumerate(lines):
            text = join_spans(spans)
            if not text:
                continue

            dominant = _dominant_span(spans)
            bbox = _line_bbox(spans)
            placement = chrome and (page_index, line_index) in chrome
            node_type = "paragraph"
            if placement:
                node_type = "running-header" if bbox[1] < _CHROME_TOP_BAND_PT else "running-footer"

            node = LayoutNode(
                id=f"n{page_index + 1}-{line_index}",
                type=node_type,
                page=page_index + 1,
                bbox=bbox,
                text=text,
                spans=spans,
                font_family=dominant.font_family,
                font_size=round(dominant.font_size, 1),
                bold=dominant.bold,
                italic=dominant.italic,
            )

            match = _HEADING_NUMBER_RE.match(text)
            if match:
                node.number = match.group(1)

            document.nodes.append(node)

    _classify_headings(document)
    return document


def _classify_headings(document: LayoutDocument) -> None:
    """Promote body lines to headings using the whole font signature.

    Size alone is not enough: an inline "Note:" run set in 10pt bold above 9pt
    body text is emphasis, not a section. A heading is set in a signature that
    the body never uses, is short, and is not page chrome.
    """
    body_size = document.body_font_size or 0.0
    if body_size <= 0:
        return

    minimum = body_size * _HEADING_SIZE_RATIO

    def is_uniform(node: LayoutNode) -> bool:
        """Every span on the line is heading-sized.

        An inline run like "Note:" is set larger and bolder than the body text
        that continues on the same line. Requiring the whole line rules it out
        without needing a rule about the word "Note".
        """
        return bool(node.spans) and all(
            span.font_size >= minimum for span in node.spans if span.text.strip()
        )

    candidates = [
        node
        for node in document.nodes
        if node.type == "paragraph"
        and node.font_size >= minimum
        and len(node.text) <= _MAX_HEADING_CHARS
        and is_uniform(node)
        and any(character.isalnum() for character in node.text)
    ]
    if not candidates:
        return

    # Rank the distinct signatures by size; larger type means a shallower level.
    sizes = sorted({node.font_size for node in candidates}, reverse=True)
    level_of = {size: index + 1 for index, size in enumerate(sizes)}

    for node in candidates:
        node.type = "heading"
        node.level = level_of[node.font_size]
        if node.number:
            stripped = _HEADING_NUMBER_RE.match(node.text)
            if stripped:
                node.text = stripped.group(2).strip()

    _anchor_levels_to_outline(document)
    _demote_cover_headings(document)


def _normalize_title(value: str) -> str:
    """Compare titles without their numbering or punctuation noise."""
    without_number = _HEADING_NUMBER_RE.sub(r"\2", value.strip())
    return re.sub(r"[^a-z0-9]+", " ", without_number.lower()).strip()


def _anchor_levels_to_outline(document: LayoutDocument) -> None:
    """Let the PDF's own bookmarks set the levels they cover.

    Font size only tells you which headings are *bigger*, not how deep they sit.
    Where the outline names a heading, its level is authoritative; the remaining
    headings keep their size-derived rank, shifted below the deepest anchor so
    they can never outrank a heading the document itself declared.
    """
    if not document.outline:
        return

    by_title: dict[str, list[OutlineEntry]] = defaultdict(list)
    for entry in document.outline:
        by_title[_normalize_title(entry.title)].append(entry)

    anchored: set[int] = set()
    for index, node in enumerate(document.nodes):
        if node.type != "heading":
            continue
        for entry in by_title.get(_normalize_title(node.text), []):
            if abs(entry.page - node.page) <= 1:
                node.level = entry.level
                anchored.add(index)
                break

    if not anchored:
        return

    deepest = max(document.nodes[index].level or 1 for index in anchored)
    for index, node in enumerate(document.nodes):
        if node.type == "heading" and index not in anchored and node.level is not None:
            node.level = max(node.level, deepest + 1)


def _demote_cover_headings(document: LayoutDocument) -> None:
    """A cover page is not a section.

    Its large type is the document title and its edition metadata - "User Guide",
    "Revision 0.6", "May 2022". Treating those as sections pollutes the table of
    contents with entries that lead nowhere.
    """
    covered = {_normalize_title(entry.title) for entry in document.outline if entry.page == 1}
    for node in document.nodes:
        if node.type != "heading" or node.page != 1:
            continue
        node.level = None
        # A cover title is routinely set across two or three lines, so an exact
        # match against the outline's single-string title would drop all of it.
        normalized = _normalize_title(node.text)
        belongs = not covered or any(
            normalized == title or (len(normalized) > 3 and normalized in title)
            for title in covered
        )
        node.type = "title" if belongs else "paragraph"
