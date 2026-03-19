"""PDF export service — renders reader artifact HTML into a downloadable PDF.

Uses PyMuPDF's Story API to convert the structured HTML (produced by the
reader-artifact pipeline) into a paginated PDF that portal and viewer
users receive as their download.
"""

from __future__ import annotations

import io
import logging

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# Default page dimensions (Letter size in points: 612 × 792)
_PAGE_WIDTH = 612
_PAGE_HEIGHT = 792
_MARGIN = 54  # 0.75 inch margins

_CSS = """\
body { font-family: Helvetica, Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: #222; }
h1 { font-size: 20pt; margin-top: 18pt; margin-bottom: 8pt; }
h2 { font-size: 16pt; margin-top: 14pt; margin-bottom: 6pt; }
h3 { font-size: 13pt; margin-top: 10pt; margin-bottom: 4pt; }
p { margin-top: 4pt; margin-bottom: 4pt; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0; }
td, th { border: 0.5pt solid #999; padding: 4pt 6pt; font-size: 10pt; }
th { background-color: #f0f0f0; font-weight: bold; }
img { max-width: 100%; }
code { font-family: Courier, monospace; font-size: 10pt; background: #f5f5f5; padding: 1pt 3pt; }
"""


def render_html_to_pdf(html: str, *, title: str = "Document") -> bytes:
    """Render an HTML string into PDF bytes.

    Parameters
    ----------
    html:
        The HTML content (typically the reader-artifact HTML).
    title:
        PDF document title metadata.

    Returns
    -------
    bytes
        The generated PDF as raw bytes, or empty bytes on failure.
    """
    try:
        # Wrap bare HTML in a full document if needed
        if "<html" not in html.lower():
            html = f"<html><head><style>{_CSS}</style></head><body>{html}</body></html>"
        else:
            # Inject CSS into existing document
            html = html.replace("</head>", f"<style>{_CSS}</style></head>", 1)

        story = fitz.Story(html)
        writer = fitz.DocumentWriter(io.BytesIO())

        content_rect = fitz.Rect(
            _MARGIN, _MARGIN, _PAGE_WIDTH - _MARGIN, _PAGE_HEIGHT - _MARGIN
        )

        more = True
        while more:
            dev = writer.begin_page(fitz.Rect(0, 0, _PAGE_WIDTH, _PAGE_HEIGHT))
            more, _ = story.place(content_rect)
            story.draw(dev)
            writer.end_page()

        # Retrieve the PDF bytes from the writer
        buf = writer.close()

        # fitz.DocumentWriter with BytesIO returns the buffer content
        if isinstance(buf, (bytes, bytearray)):
            return bytes(buf)

        # Fallback: re-open and save
        return _fallback_render(html, title)
    except Exception as exc:
        logger.exception("PDF render failed: %s", exc)
        return b""


def _fallback_render(html: str, title: str) -> bytes:
    """Fallback: use fitz.open + insert_htmlbox for simpler rendering."""
    try:
        doc = fitz.open()
        page = doc.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
        rect = fitz.Rect(_MARGIN, _MARGIN, _PAGE_WIDTH - _MARGIN, _PAGE_HEIGHT - _MARGIN)
        # insert_htmlbox renders HTML into a rect area
        try:
            # insert_htmlbox may return various values depending on PyMuPDF version
            result = page.insert_htmlbox(rect, html)
            # If result is a tuple, extract the excess indicator
            excess = result[0] if isinstance(result, tuple) else result
            page_limit = 200
            while excess and page_limit > 0:
                page_limit -= 1
                page = doc.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
                result = page.insert_htmlbox(rect, html)
                excess = result[0] if isinstance(result, tuple) else result
        except TypeError:
            # Just render what fits on one page if API is unexpected
            pass
        doc.set_metadata({"title": title})
        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes
    except Exception as exc:
        logger.exception("Fallback PDF render failed: %s", exc)
        return b""
