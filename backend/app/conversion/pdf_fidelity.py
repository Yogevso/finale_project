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
"""

from __future__ import annotations

import base64
import html
import io
import logging
import re
from dataclasses import dataclass, field
from typing import Any

import fitz  # PyMuPDF

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
        result.toc_items = _build_toc_items(doc)

        parts = [f"<style>{_STYLE}</style>", _font_face_css(fonts), '<div class="pdf-fidelity">']
        for page_index in range(page_limit):
            parts.append(_render_page(doc[page_index], fonts, result.warnings, page_index))
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
    fonts: dict[str, tuple[str, str]],
    warnings: list[str],
    page_index: int,
) -> str:
    width, height = page.rect.width, page.rect.height
    if width <= 0 or height <= 0:
        return ""

    background = _render_background(page, warnings, page_index)
    spans = _render_text_spans(page, fonts, width)
    return (
        f'<div class="pdf-fidelity-page" style="aspect-ratio:{width}/{height}"'
        f' data-page="{page_index + 1}">{background}'
        f'<div class="pdf-fidelity-text">{spans}</div></div>'
    )


def _render_background(page: Any, warnings: list[str], page_index: int) -> str:
    """Return the page's graphics as SVG, with its text removed."""
    try:
        svg = page.get_svg_image(text_as_path=False)
    except Exception as exc:  # policy: LOSSY — a page without graphics still shows its text
        warnings.append(f"Page {page_index + 1}: background render failed: {exc}")
        return ""
    return _SVG_TEXT_NODES.sub("", svg)


def _render_text_spans(page: Any, fonts: dict[str, tuple[str, str]], page_width: float) -> str:
    """Place each text span over the background in container-relative units.

    Percentages resolve against the parent font size, so ``cqw`` is used: it is
    a share of the page container's width and therefore scales with the page.
    """
    try:
        text_dict = page.get_text("dict")
    except Exception:  # policy: LOSSY — an unreadable page renders as graphics only
        return ""

    spans: list[str] = []
    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "")
                if not text.strip():
                    continue
                x0, y0 = span["bbox"][0], span["bbox"][1]
                size = span.get("size", 10.0)
                span_font = _SUBSET_PREFIX.sub("", span.get("font", ""))
                entry = fonts.get(span_font)
                # Families are pre-quoted with single quotes; this string is
                # interpolated into a double-quoted HTML attribute.
                stack = entry[0] if entry else (_fallback_stack(span_font) if span_font else "")
                family = f"font-family:{stack};" if stack else ""
                colour = span.get("color", 0)
                rgb = f"#{colour & 0xFFFFFF:06x}" if isinstance(colour, int) else "#000000"
                spans.append(
                    f'<span style="left:{100 * x0 / page_width:.3f}cqw;'
                    f"top:{100 * y0 / page_width:.3f}cqw;"
                    f"font-size:{100 * size / page_width:.3f}cqw;"
                    f'{family}color:{rgb}">{html.escape(text)}</span>'
                )
    return "".join(spans)


# ---------------------------------------------------------------------------
# Table of contents
# ---------------------------------------------------------------------------


def _build_toc_items(doc: Any) -> list[dict[str, Any]]:
    """Use the PDF's own outline, which is authoritative, rather than guessing."""
    try:
        outline = doc.get_toc(simple=True)
    except Exception:  # policy: DEGRADED — a missing outline just means no table of contents
        return []

    items: list[dict[str, Any]] = []
    for index, entry in enumerate(outline or []):
        try:
            level, title, page = int(entry[0]), str(entry[1]).strip(), int(entry[2])
        except (TypeError, ValueError, IndexError):
            continue
        if not title:
            continue
        items.append(
            {
                "id": f"toc-{index}",
                "title": title,
                "level": max(1, level),
                "page": max(1, page),
                "page_start": max(1, page),
                "page_end": None,
                "anchor_id": "",
            }
        )
    return items


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
        "status": "completed",
        "html_content": result.html,
        "toc_items": result.toc_items,
        "toc_source": "pdf_outline",
        "payload": {
            "status": "completed",
            "mode": "fidelity",
            "page_count": result.page_count,
            "font_count": result.font_count,
            "toc_items": result.toc_items,
            "warnings": [{"code": "fidelity", "message": item} for item in result.warnings],
        },
        "error": None,
    }
