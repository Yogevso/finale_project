"""HTML to PDF conversion helpers using reportlab."""

from __future__ import annotations

import io
import logging
import re
from html import unescape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

logger = logging.getLogger(__name__)


def _strip_tags(html: str) -> str:
    """Remove HTML tags and return plain text."""
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return unescape(text).strip()


def _html_blocks(html: str) -> list[tuple[str, str]]:
    """Parse HTML into (tag, text) blocks for basic rendering."""
    blocks: list[tuple[str, str]] = []
    # Split on heading / paragraph boundaries
    parts = re.split(r"(<h[1-6][^>]*>.*?</h[1-6]>|<p[^>]*>.*?</p>|<li[^>]*>.*?</li>)", html, flags=re.IGNORECASE | re.DOTALL)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        tag_match = re.match(r"<(h[1-6]|p|li)", part, re.IGNORECASE)
        tag = tag_match.group(1).lower() if tag_match else "p"
        text = _strip_tags(part)
        if text:
            blocks.append((tag, text))
    return blocks


def html_to_pdf_bytes(html: str, title: str = "Document") -> bytes:
    """Convert HTML string to PDF bytes using reportlab."""
    from app.utils.sanitization import sanitize_html_content

    safe_html = sanitize_html_content(html) or ""

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=title,
    )

    styles = getSampleStyleSheet()
    heading_styles = {
        "h1": ParagraphStyle("H1Export", parent=styles["Heading1"], fontSize=20, spaceAfter=12),
        "h2": ParagraphStyle("H2Export", parent=styles["Heading2"], fontSize=16, spaceAfter=10),
        "h3": ParagraphStyle("H3Export", parent=styles["Heading3"], fontSize=13, spaceAfter=8),
        "h4": ParagraphStyle("H4Export", parent=styles["Heading4"], fontSize=11, spaceAfter=6),
        "h5": ParagraphStyle("H5Export", parent=styles["Heading5"], fontSize=10, spaceAfter=6),
        "h6": ParagraphStyle("H6Export", parent=styles["Heading6"], fontSize=9, spaceAfter=6),
    }
    body_style = ParagraphStyle("BodyExport", parent=styles["BodyText"], fontSize=10, spaceAfter=6, leading=14)
    li_style = ParagraphStyle("LiExport", parent=body_style, bulletIndent=12, leftIndent=24)

    blocks = _html_blocks(safe_html)
    story: list = []

    for tag, text in blocks:
        style = heading_styles.get(tag, body_style)
        if tag == "li":
            style = li_style
            text = f"\u2022  {text}"
        try:
            story.append(Paragraph(text, style))
        except Exception:
            # If reportlab can't parse the text, add as plain
            story.append(Paragraph(text.replace("&", "&amp;").replace("<", "&lt;"), body_style))
        story.append(Spacer(1, 4))

    if not story:
        story.append(Paragraph("(Empty document)", body_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
