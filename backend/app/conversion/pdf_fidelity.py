"""PDF-to-HTML fidelity converter.

The structured reader pipeline (PDF -> DOCX -> reader artifact) recovers
*meaning* — headings, tables, paragraphs — but necessarily discards page
geometry, brand colour and typography, because DOCX is a reflowable format.
For specification PDFs that look wrong: no logo, no cover layout, body serif
where the source is Intel Clear.

This module produces the complementary view: an HTML rendering that keeps the
original page appearance. Each page becomes an SVG of the page's vector and
raster graphics with its text stripped out, and the text is re-placed on top as
real, selectable HTML positioned in container-relative units. Fonts come from
the PDF's own embedded font programs, so branding survives without shipping any
font files.

Compared with rasterising each page, this keeps text selectable and searchable,
stays sharp at any zoom, and is markedly smaller.

The text layer is rendered from ``pdf_layout``'s document model rather than from
a second pass over the PDF. That model already knows which spans form one line,
which lines are headings and which are the running header, so every rendered
line can carry the ``data-node-id`` of the node it came from. A heading in the
table of contents and the heading on the page are then the same node under the
same id, and navigation is a lookup rather than a text search.
"""

from __future__ import annotations

import base64
import html
import io
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import fitz  # PyMuPDF

from app.conversion.document_toc import build_toc_from_layout
from app.conversion.pdf_layout import LayoutNode, LayoutSpan, extract_layout_from_document

logger = logging.getLogger(__name__)

# Font names inside a PDF carry a six-letter subset tag, e.g. "ORIAAM+IntelClear".
_SUBSET_PREFIX = re.compile(r"^[A-Z]{6}\+")
# Text nodes are stripped from the background SVG; the HTML layer replaces them.
_SVG_TEXT_NODES = re.compile(r"<text\b.*?</text>", re.S)
# Guard rails so a pathological PDF cannot exhaust memory or storage.
_MAX_PAGES = 400
_MAX_OUTPUT_BYTES = 48 * 1024 * 1024
# Fonts below this size are almost certainly stubs rather than real programs.
_MIN_FONT_BYTES = 100

_STYLE = """
.pdf-fidelity{background:#f1f5f9;padding:16px 0}
.pdf-fidelity-page{position:relative;margin:0 auto 20px;background:#fff;
  box-shadow:0 2px 10px rgba(15,23,42,.18);max-width:1000px;container-type:inline-size}
.pdf-fidelity-page svg{display:block;width:100%;height:auto}
.pdf-fidelity-text{position:absolute;inset:0;overflow:hidden}
.pdf-fidelity-node{position:absolute}
.pdf-fidelity-text span{position:absolute;white-space:pre;line-height:1;transform-origin:0 0}
"""


@dataclass
class FidelityResult:
    """Result of rendering a PDF as fidelity HTML."""

    html: str = ""
    page_count: int = 0
    font_count: int = 0
    toc_items: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None


def convert_pdf_to_fidelity_html(pdf_bytes: bytes) -> FidelityResult:
    """Render ``pdf_bytes`` as self-contained HTML that mirrors the page layout."""
    result = FidelityResult()
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except (
        Exception
    ) as exc:  # policy: FAIL_FAST — invalid PDF input returns a stable conversion error
        result.error = f"Failed to open PDF: {exc}"
        return result

    try:
        result.page_count = len(doc)
        if result.page_count == 0:
            result.error = "PDF has no pages"
            return result

        page_limit = min(result.page_count, _MAX_PAGES)
        if page_limit < result.page_count:
            result.warnings.append(
                f"Only the first {page_limit} of {result.page_count} pages were rendered."
            )

        fonts = _extract_fonts(doc, result.warnings)
        result.font_count = len(fonts)

        layout = extract_layout_from_document(doc, max_pages=page_limit)
        if layout.error:
            result.error = layout.error
            return result
        result.warnings.extend(layout.warnings)
        # The outline is authoritative but often shallow, so detected headings
        # fill in below it - the same contents the structured reader shows, over
        # ids that exist in this render.
        result.toc_items = build_toc_from_layout(layout)

        nodes_by_page: dict[int, list[LayoutNode]] = defaultdict(list)
        for node in layout.nodes:
            nodes_by_page[node.page].append(node)

        parts = [f"<style>{_STYLE}</style>", _font_face_css(fonts), '<div class="pdf-fidelity">']
        for page_index in range(page_limit):
            parts.append(
                _render_page(
                    doc[page_index],
                    nodes_by_page.get(page_index + 1, []),
                    fonts,
                    result.warnings,
                    page_index,
                )
            )
        parts.append("</div>")

        rendered = "".join(parts)
        if len(rendered.encode("utf-8")) > _MAX_OUTPUT_BYTES:
            result.error = "Rendered page layout exceeds the maximum artifact size."
            return result

        result.html = rendered
        return result
    finally:
        doc.close()


# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------


def _extract_fonts(doc: Any, warnings: list[str]) -> dict[str, tuple[str, str]]:
    """Map a PDF font name to the CSS family and data URI that reproduce it."""
    fonts: dict[str, tuple[str, str]] = {}
    for page_index in range(min(len(doc), _MAX_PAGES)):
        try:
            page_fonts = doc.get_page_fonts(page_index, full=True)
        except Exception:  # policy: DEGRADED — a page that will not parse contributes no fonts
            continue
        for entry in page_fonts:
            xref, ext, base_font = entry[0], entry[1], entry[3]
            key = _SUBSET_PREFIX.sub("", base_font or "")
            if not key or key in fonts or ext in ("n/a", ""):
                continue
            try:
                _name, extracted_ext, _subtype, buffer = doc.extract_font(xref)
            except Exception:  # policy: LOSSY — a font that will not extract falls back to CSS
                continue
            if not buffer or len(buffer) < _MIN_FONT_BYTES:
                continue
            payload, mime = _to_web_font(buffer, extracted_ext)
            if payload is None:
                warnings.append(f"Font {key} could not be embedded; a fallback face is used.")
                fonts[key] = (_fallback_stack(key), "")
                continue
            family = "pdffont_" + re.sub(r"[^A-Za-z0-9]", "", key)[:32]
            encoded = base64.b64encode(payload).decode("ascii")
            fonts[key] = (f"'{family}'", f"data:{mime};base64,{encoded}")
    return fonts


def _to_web_font(buffer: bytes, ext: str) -> tuple[bytes | None, str]:
    """Re-wrap an extracted font as WOFF.

    Browsers reject many font programs lifted straight out of a PDF; a
    fontTools round-trip repairs the tables, and WOFF is smaller than the
    raw TrueType it replaces.

    Composite (Type0/CID) fonts are keyed by glyph id and frequently carry no
    ``cmap`` at all. The browser has no way to map our Unicode text onto those
    glyphs, so embedding one yields either tofu or a silent load failure that
    drops the page to a serif default. Those fonts are rejected here and the
    caller substitutes a name-matched CSS stack instead.
    """
    try:
        from fontTools.ttLib import TTFont

        font = TTFont(io.BytesIO(buffer))
        if "cmap" not in font or not font.getBestCmap():
            return None, ""
        out = io.BytesIO()
        font.flavor = "woff"
        font.save(out)
        return out.getvalue(), "font/woff"
    except Exception:  # policy: DEGRADED — fall back to the raw program when repair fails
        if ext == "ttf":
            return buffer, "font/ttf"
        if ext == "otf":
            return buffer, "font/otf"
        return None, ""


# Generic families used when a PDF font cannot be embedded.
_SERIF_HINTS = ("times", "serif", "georgia", "garamond", "roman", "book")
_MONO_HINTS = ("mono", "courier", "consol")


def _fallback_stack(base_font: str) -> str:
    """Build a CSS stack that approximates a font we could not embed.

    The PDF's own family name goes first — Verdana and Arial are commonly
    installed — followed by a generic that at least preserves serif vs sans.
    """
    family = _SUBSET_PREFIX.sub("", base_font or "").split(",")[0]
    # "Verdana-BoldItalic" -> "Verdana"
    family = re.split(r"[-_](?=[A-Z])", family)[0].strip() or "sans-serif"
    lowered = family.lower()
    if any(hint in lowered for hint in _MONO_HINTS):
        generic = "monospace"
    elif any(hint in lowered for hint in _SERIF_HINTS):
        generic = "Georgia, serif"
    else:
        generic = "'Helvetica Neue', Arial, sans-serif"
    return f"'{family}', {generic}"


def _font_face_css(fonts: dict[str, tuple[str, str]]) -> str:
    if not fonts:
        return ""
    faces = "".join(
        f'@font-face{{font-family:{family};src:url("{uri}");font-display:block}}'
        for family, uri in fonts.values()
        if uri
    )
    return f"<style>{faces}</style>" if faces else ""


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


def _render_page(
    page: Any,
    nodes: list[LayoutNode],
    fonts: dict[str, tuple[str, str]],
    warnings: list[str],
    page_index: int,
) -> str:
    width, height = page.rect.width, page.rect.height
    if width <= 0 or height <= 0:
        return ""

    background = _render_background(page, warnings, page_index)
    text_layer = _render_text_layer(nodes, fonts, width)
    return (
        f'<div class="pdf-fidelity-page" style="aspect-ratio:{width}/{height}"'
        f' data-page="{page_index + 1}">{background}'
        f'<div class="pdf-fidelity-text">{text_layer}</div></div>'
    )


def _render_background(page: Any, warnings: list[str], page_index: int) -> str:
    """Return the page's graphics as SVG, with its text removed."""
    try:
        svg = page.get_svg_image(text_as_path=False)
    except Exception as exc:  # policy: LOSSY — a page without graphics still shows its text
        warnings.append(f"Page {page_index + 1}: background render failed: {exc}")
        return ""
    return _SVG_TEXT_NODES.sub("", svg)


def _cqw(value: float, page_width: float) -> str:
    """Express a PDF-space length as a share of the page container's width.

    Percentages would resolve against the parent font size, and the vertical
    axis uses the same unit as the horizontal one deliberately: the page has a
    fixed aspect ratio, so one scale factor keeps x and y in proportion.
    """
    return f"{100 * value / page_width:.3f}cqw"


def _render_text_layer(
    nodes: list[LayoutNode],
    fonts: dict[str, tuple[str, str]],
    page_width: float,
) -> str:
    """Place the page's layout nodes over the background, keeping their identity.

    Each node is a positioned box rather than a bare grouping element. The
    reader scrolls to it and anchors comments against it, and an element with no
    box of its own - ``display:contents``, say - reports neither a position nor
    a size to do that with.

    Span offsets are relative to the node's own box. ``cqw`` still resolves
    against the page, because only the page declares ``container-type``.
    """
    parts: list[str] = []
    for node in nodes:
        if not node.spans:
            continue

        left, top, right, bottom = node.bbox
        attributes = (
            f' data-node-id="{html.escape(node.id, quote=True)}"'
            f' data-node-type="{html.escape(node.type, quote=True)}"'
        )
        if node.level is not None:
            attributes += f' data-node-level="{int(node.level)}"'

        parts.append(
            f'<div class="pdf-fidelity-node"{attributes}'
            f' style="left:{_cqw(left, page_width)};top:{_cqw(top, page_width)};'
            f'width:{_cqw(right - left, page_width)};height:{_cqw(bottom - top, page_width)}">'
        )
        parts.extend(_render_span(span, fonts, page_width, left, top) for span in node.spans)
        parts.append("</div>")
    return "".join(parts)


def _render_span(
    span: LayoutSpan,
    fonts: dict[str, tuple[str, str]],
    page_width: float,
    origin_x: float,
    origin_y: float,
) -> str:
    stack = _css_font_family(span.font_family, fonts)
    # Families are pre-quoted with single quotes; this string is interpolated
    # into a double-quoted HTML attribute.
    family = f"font-family:{stack};" if stack else ""
    return (
        f'<span style="left:{_cqw(span.bbox[0] - origin_x, page_width)};'
        f"top:{_cqw(span.bbox[1] - origin_y, page_width)};"
        f"font-size:{_cqw(span.font_size, page_width)};"
        f'{family}color:#{span.color & 0xFFFFFF:06x}">{html.escape(span.text)}</span>'
    )


def _css_font_family(family: str, fonts: dict[str, tuple[str, str]]) -> str:
    """The stack for a span: the embedded face where there is one, else a match."""
    # ``pdf_layout`` reports a span with no font name as "unknown"; naming that
    # in CSS only sends the browser looking for a family that cannot exist.
    if not family or family == "unknown":
        return ""
    entry = fonts.get(family)
    return entry[0] if entry else _fallback_stack(family)


def build_fidelity_reader_artifact(pdf_bytes: bytes) -> dict[str, Any]:
    """Render a PDF and shape it like every other stored reader artifact."""
    result = convert_pdf_to_fidelity_html(pdf_bytes)
    if result.error:
        return {
            "status": "failed",
            "html_content": "",
            "toc_items": [],
            "toc_source": "pdf_outline",
            "payload": {"status": "failed", "warnings": [], "mode": "fidelity"},
            "error": result.error,
        }
    return {
        "status": "ready",
        "html_content": result.html,
        "toc_items": result.toc_items,
        "toc_source": "pdf_outline",
        "payload": {
            "status": "ready",
            "mode": "fidelity",
            "page_count": result.page_count,
            "font_count": result.font_count,
            "toc_items": result.toc_items,
            "warnings": [{"code": "fidelity", "message": item} for item in result.warnings],
        },
        "error": None,
    }
