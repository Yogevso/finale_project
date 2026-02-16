"""
Document Converter Utility

Converts various document types (PDF, Word, etc.) to HTML for editing.
"""

import io
import html
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

HEADING_NUMBER_RE = re.compile(r"^(\d+(?:\.\d+)*)[.)]?\s+\S+")
UPPERCASE_HEADING_RE = re.compile(r"^[A-Z0-9][A-Z0-9\s\-_/]{3,}$")


def _escape_html(value: str) -> str:
    return html.escape(value, quote=True)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return slug or "section"


def _is_bold_span(flags: int, font_name: str) -> bool:
    return bool(flags & (1 << 4)) or "bold" in (font_name or "").lower()


def _is_italic_span(flags: int, font_name: str) -> bool:
    return bool(flags & (1 << 1)) or "italic" in (font_name or "").lower()


def _extract_pdf_tables_with_bboxes(page) -> tuple[list[dict[str, Any]], list[tuple[float, float, float, float]]]:
    """Extract table-like structures and their rough page coordinates."""
    if not hasattr(page, "find_tables"):
        return [], []

    try:
        tables_result = page.find_tables()
    except Exception as exc:
        logger.debug("PDF table detection failed: %s", exc)
        return [], []

    table_objects = getattr(tables_result, "tables", None)
    if table_objects is None:
        if isinstance(tables_result, (list, tuple)):
            table_objects = tables_result
        else:
            table_objects = []

    table_entries: list[dict[str, Any]] = []
    table_bboxes: list[tuple[float, float, float, float]] = []

    for table_index, table in enumerate(table_objects):
        try:
            extracted_rows = table.extract() if hasattr(table, "extract") else None
        except Exception as exc:
            logger.debug("Skipping unreadable table in PDF page: %s", exc)
            continue

        if not extracted_rows:
            continue

        rows: list[list[str]] = []
        for raw_row in extracted_rows:
            if raw_row is None:
                continue
            normalized_row = [_escape_html(_normalize_text(cell or "")) for cell in raw_row]
            if any(normalized_row):
                rows.append(normalized_row)

        if not rows:
            continue

        header_row = rows[0]
        body_rows = rows[1:] if len(rows) > 1 else []

        table_parts = [
            "<div class='pdf-table-wrap'>",
            "<table>",
            "<thead><tr>",
        ]
        table_parts.extend(f"<th>{cell if cell else '&nbsp;'}</th>" for cell in header_row)
        table_parts.append("</tr></thead>")

        if body_rows:
            table_parts.append("<tbody>")
            for row in body_rows:
                table_parts.append("<tr>")
                table_parts.extend(f"<td>{cell if cell else '&nbsp;'}</td>" for cell in row)
                table_parts.append("</tr>")
            table_parts.append("</tbody>")

        table_parts.append("</table>")
        table_parts.append("</div>")

        bbox_raw = getattr(table, "bbox", None) or getattr(table, "rect", None)
        bbox: Optional[tuple[float, float, float, float]] = None
        if isinstance(bbox_raw, (list, tuple)) and len(bbox_raw) == 4:
            try:
                bbox = (
                    float(bbox_raw[0]),
                    float(bbox_raw[1]),
                    float(bbox_raw[2]),
                    float(bbox_raw[3]),
                )
                table_bboxes.append(bbox)
            except (TypeError, ValueError):
                bbox = None

        y0 = bbox[1] if bbox else float(table_index) * 10000.0
        table_entries.append(
            {
                "html": "".join(table_parts),
                "bbox": bbox,
                "y0": y0,
            }
        )

    table_entries.sort(key=lambda item: item.get("y0", 0.0))
    return table_entries, table_bboxes


def _bbox_overlap_ratio(
    lhs: tuple[float, float, float, float], rhs: tuple[float, float, float, float]
) -> float:
    left = max(lhs[0], rhs[0])
    top = max(lhs[1], rhs[1])
    right = min(lhs[2], rhs[2])
    bottom = min(lhs[3], rhs[3])
    if right <= left or bottom <= top:
        return 0.0

    intersection = (right - left) * (bottom - top)
    lhs_area = max((lhs[2] - lhs[0]) * (lhs[3] - lhs[1]), 1.0)
    return intersection / lhs_area


def _line_intersects_table(
    line_bbox: tuple[float, float, float, float], table_bboxes: list[tuple[float, float, float, float]]
) -> bool:
    for table_bbox in table_bboxes:
        if _bbox_overlap_ratio(line_bbox, table_bbox) >= 0.45:
            return True
    return False


def _collect_pdf_lines(
    page, table_bboxes: list[tuple[float, float, float, float]]
) -> list[dict[str, Any]]:
    """Collect page text lines with position + basic style metadata."""
    try:
        blocks = page.get_text("dict").get("blocks", [])
    except Exception:
        blocks = []

    lines: list[dict[str, Any]] = []

    for block in blocks:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            span_html_parts: list[str] = []
            span_plain_parts: list[str] = []
            max_size = 0.0
            is_bold = False
            min_x = float("inf")
            min_y = float("inf")
            max_x = 0.0
            max_y = 0.0

            for span in spans:
                text = _normalize_text(span.get("text") or "")
                if not text:
                    continue

                flags = int(span.get("flags", 0) or 0)
                font_name = str(span.get("font", "") or "")
                size = float(span.get("size", 0.0) or 0.0)
                span_bbox = span.get("bbox") or [0.0, 0.0, 0.0, 0.0]
                try:
                    x0, y0, x1, y1 = (
                        float(span_bbox[0]),
                        float(span_bbox[1]),
                        float(span_bbox[2]),
                        float(span_bbox[3]),
                    )
                except (TypeError, ValueError, IndexError):
                    x0, y0, x1, y1 = 0.0, 0.0, 0.0, 0.0

                min_x = min(min_x, x0)
                min_y = min(min_y, y0)
                max_x = max(max_x, x1)
                max_y = max(max_y, y1)
                max_size = max(max_size, size)
                span_plain_parts.append(text)

                rendered = _escape_html(text)
                if _is_bold_span(flags, font_name):
                    rendered = f"<strong>{rendered}</strong>"
                    is_bold = True
                if _is_italic_span(flags, font_name):
                    rendered = f"<em>{rendered}</em>"
                span_html_parts.append(rendered)

            if not span_plain_parts:
                continue

            line_bbox = (
                min_x if min_x != float("inf") else 0.0,
                min_y if min_y != float("inf") else 0.0,
                max_x,
                max_y,
            )
            if _line_intersects_table(line_bbox, table_bboxes):
                continue

            plain_text = _normalize_text(" ".join(span_plain_parts))
            html_text = " ".join(span_html_parts).strip()
            if not plain_text or not html_text:
                continue

            lines.append(
                {
                    "text": plain_text,
                    "html": html_text,
                    "size": max_size if max_size > 0 else 12.0,
                    "is_bold": is_bold,
                    "y0": line_bbox[1],
                    "x0": line_bbox[0],
                }
            )

    lines.sort(key=lambda item: (round(float(item.get("y0", 0.0)), 1), float(item.get("x0", 0.0))))
    return lines


def _estimate_body_font_size(lines: list[dict[str, Any]]) -> float:
    if not lines:
        return 12.0

    sizes = sorted(
        float(line.get("size", 12.0) or 12.0)
        for line in lines
        if float(line.get("size", 0.0) or 0.0) > 0
    )
    if not sizes:
        return 12.0

    return sizes[len(sizes) // 2]


def _classify_heading_level(line: dict[str, Any], body_font_size: float) -> Optional[int]:
    text = _normalize_text(str(line.get("text") or ""))
    if not text:
        return None
    if len(text) < 3 or len(text) > 180:
        return None

    words = text.split()
    if len(words) > 24:
        return None
    if len(words) <= 2 and not HEADING_NUMBER_RE.match(text):
        return None

    size = float(line.get("size", body_font_size) or body_font_size)
    size_delta = size - body_font_size
    is_bold = bool(line.get("is_bold"))
    is_numbered = bool(HEADING_NUMBER_RE.match(text))
    is_upper = bool(UPPERCASE_HEADING_RE.match(text))
    looks_like_sentence = text.endswith(".") and len(words) > 8 and not is_numbered

    if looks_like_sentence and size_delta < 2.5 and not is_bold:
        return None

    if not (size_delta >= 1.2 or is_bold or is_numbered or is_upper):
        return None

    if is_numbered:
        number_part = HEADING_NUMBER_RE.match(text).group(1)
        depth = min(number_part.count(".") + 1, 3)
        return depth

    if size_delta >= 6.0:
        return 1
    if size_delta >= 3.5:
        return 2
    if size_delta >= 1.8:
        return 3
    if is_upper and len(words) <= 12:
        return 2
    if is_bold and len(words) <= 14:
        return 3
    return None


def _build_anchor_id(page_number: int, title: str, index: int) -> str:
    slug = _slugify(title)[:60]
    return f"reader-p{page_number}-{slug}-{index}"


def _collect_heading_candidates(
    lines: list[dict[str, Any]], page_number: int, body_font_size: float
) -> list[dict[str, Any]]:
    headings: list[dict[str, Any]] = []
    for line in lines:
        level = _classify_heading_level(line, body_font_size)
        if not level:
            continue
        title = _normalize_text(str(line.get("text") or ""))
        if not title:
            continue
        anchor_id = _build_anchor_id(page_number, title, len(headings))
        headings.append(
            {
                "title": title,
                "level": level,
                "page_start": page_number,
                "anchor_id": anchor_id,
                "normalized_title": _normalize_text(title).lower(),
            }
        )
    return headings


def _render_pdf_page_html(
    lines: list[dict[str, Any]],
    table_entries: list[dict[str, Any]],
    page_number: int,
    body_font_size: float,
) -> tuple[list[str], list[dict[str, Any]]]:
    page_parts: list[str] = []
    page_headings: list[dict[str, Any]] = []
    paragraph_lines: list[str] = []
    last_line_y: Optional[float] = None

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if not paragraph_lines:
            return
        paragraph_html = " ".join(paragraph_lines).strip()
        paragraph_lines = []
        if paragraph_html:
            page_parts.append(f"<p>{paragraph_html}</p>")

    events: list[tuple[float, int, str, Any]] = []
    for line_index, line in enumerate(lines):
        events.append((float(line.get("y0", 0.0)), line_index, "line", line))
    for table_index, table in enumerate(table_entries):
        events.append((float(table.get("y0", 0.0)), table_index, "table", table))
    events.sort(key=lambda item: (item[0], item[1], 0 if item[2] == "line" else 1))

    for _, _, event_type, payload in events:
        if event_type == "table":
            flush_paragraph()
            table_html = str(payload.get("html") or "")
            if table_html:
                page_parts.append(table_html)
            last_line_y = None
            continue

        line = payload
        heading_level = _classify_heading_level(line, body_font_size)
        line_y = float(line.get("y0", 0.0))
        line_size = float(line.get("size", body_font_size) or body_font_size)

        if heading_level:
            flush_paragraph()
            title = _normalize_text(str(line.get("text") or ""))
            anchor_id = _build_anchor_id(page_number, title, len(page_headings))
            rendered_title = str(line.get("html") or _escape_html(title))
            page_parts.append(
                f"<h{heading_level} id='{anchor_id}' data-page='{page_number}'>{rendered_title}</h{heading_level}>"
            )
            page_headings.append(
                {
                    "title": title,
                    "level": heading_level,
                    "page_start": page_number,
                    "anchor_id": anchor_id,
                    "normalized_title": _normalize_text(title).lower(),
                }
            )
            last_line_y = line_y
            continue

        if last_line_y is not None and (line_y - last_line_y) > max(18.0, line_size * 1.45):
            flush_paragraph()
        paragraph_lines.append(str(line.get("html") or ""))
        last_line_y = line_y

    flush_paragraph()
    return page_parts, page_headings


def _compute_page_end(items: list[dict[str, Any]], page_count: int) -> None:
    for index, item in enumerate(items):
        current_page = int(item.get("page_start", 1) or 1)
        if index == len(items) - 1:
            end_page = page_count
        else:
            next_page = int(items[index + 1].get("page_start", current_page) or current_page)
            end_page = max(current_page, next_page - 1)
        item["page_end"] = end_page if end_page > current_page else None


def _extract_outline_items(doc, page_count: int) -> list[dict[str, Any]]:
    raw_outline = doc.get_toc(simple=True) or []
    items: list[dict[str, Any]] = []

    for entry in raw_outline:
        if not isinstance(entry, (list, tuple)) or len(entry) < 3:
            continue

        try:
            level = max(1, int(entry[0]))
            page_start = min(page_count, max(1, int(entry[2])))
        except (TypeError, ValueError):
            continue

        title = _normalize_text(str(entry[1] or ""))
        if not title:
            continue

        items.append(
            {
                "title": title,
                "level": level,
                "page_start": page_start,
                "normalized_title": title.lower(),
            }
        )

    return items


def _map_outline_to_toc(
    outline_items: list[dict[str, Any]],
    headings_by_page: dict[int, list[dict[str, Any]]],
    page_count: int,
) -> list[dict[str, Any]]:
    mapped_items: list[dict[str, Any]] = []
    for index, outline_item in enumerate(outline_items):
        page_start = int(outline_item.get("page_start", 1) or 1)
        normalized_outline_title = str(outline_item.get("normalized_title") or "")

        anchor_id = f"pdf-page-{page_start}"
        page_headings = headings_by_page.get(page_start, [])
        if page_headings:
            exact_match = next(
                (
                    heading
                    for heading in page_headings
                    if heading.get("normalized_title") == normalized_outline_title
                ),
                None,
            )
            fuzzy_match = None
            if not exact_match:
                fuzzy_match = next(
                    (
                        heading
                        for heading in page_headings
                        if normalized_outline_title
                        and (
                            normalized_outline_title in str(heading.get("normalized_title") or "")
                            or str(heading.get("normalized_title") or "") in normalized_outline_title
                        )
                    ),
                    None,
                )
            matched = exact_match or fuzzy_match or page_headings[0]
            anchor_id = str(matched.get("anchor_id") or anchor_id)

        mapped_items.append(
            {
                "id": f"toc-outline-{index}",
                "title": str(outline_item.get("title") or ""),
                "level": int(outline_item.get("level", 1) or 1),
                "page_start": page_start,
                "page_end": None,
                "anchor_id": anchor_id,
            }
        )

    _compute_page_end(mapped_items, page_count)
    return mapped_items


def _build_heuristic_toc(
    heading_items: list[dict[str, Any]], page_count: int
) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()
    for heading in heading_items:
        page_start = int(heading.get("page_start", 1) or 1)
        title = str(heading.get("title") or "").strip()
        key = (page_start, title.lower())
        if not title or key in seen:
            continue
        seen.add(key)
        deduped.append(
            {
                "id": f"toc-heuristic-{len(deduped)}",
                "title": title,
                "level": int(heading.get("level", 1) or 1),
                "page_start": page_start,
                "page_end": None,
                "anchor_id": str(heading.get("anchor_id") or f"pdf-page-{page_start}"),
            }
        )
        if len(deduped) >= 150:
            break

    _compute_page_end(deduped, page_count)
    return deduped


def _build_pdf_reader_structure(content: bytes, *, include_html: bool) -> dict[str, Any]:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("PyMuPDF not installed")
        return {
            "html_content": "",
            "toc_items": [],
            "toc_source": "none",
            "page_count": 0,
            "error": "PDF conversion not available. Please install PyMuPDF.",
        }

    doc = None
    try:
        doc = fitz.open(stream=content, filetype="pdf")
        page_count = len(doc)
        html_parts: list[str] = []
        heading_items: list[dict[str, Any]] = []
        headings_by_page: dict[int, list[dict[str, Any]]] = {}

        for page_index in range(page_count):
            page_number = page_index + 1
            page = doc[page_index]
            table_entries, table_bboxes = _extract_pdf_tables_with_bboxes(page)
            lines = _collect_pdf_lines(page, table_bboxes)
            body_font_size = _estimate_body_font_size(lines)

            if include_html:
                page_html, page_headings = _render_pdf_page_html(
                    lines,
                    table_entries,
                    page_number,
                    body_font_size,
                )
            else:
                page_html = []
                page_headings = _collect_heading_candidates(lines, page_number, body_font_size)

            headings_by_page[page_number] = page_headings
            heading_items.extend(page_headings)

            if include_html:
                html_parts.append(
                    f"<section class='pdf-reader-page' data-page='{page_number}' id='pdf-page-{page_number}'>"
                )
                if page_html:
                    html_parts.extend(page_html)
                html_parts.append("</section>")
                if page_index < page_count - 1:
                    html_parts.append("<hr class='page-break'>")

        outline_items = _extract_outline_items(doc, page_count)
        if outline_items:
            toc_items = _map_outline_to_toc(outline_items, headings_by_page, page_count)
            toc_source = "outline"
        else:
            toc_items = _build_heuristic_toc(heading_items, page_count)
            toc_source = "heuristic" if toc_items else "none"

        html_content = "\n".join(html_parts).strip() if include_html else ""
        if include_html and not html_content:
            html_content = "<p>No text content could be extracted from this PDF.</p>"

        return {
            "html_content": html_content,
            "toc_items": toc_items,
            "toc_source": toc_source,
            "page_count": page_count,
            "error": None,
        }
    except Exception as exc:
        logger.error("PDF conversion error: %s", exc)
        return {
            "html_content": "",
            "toc_items": [],
            "toc_source": "none",
            "page_count": 0,
            "error": f"Error converting PDF: {exc}",
        }
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass


def convert_pdf_to_reader_artifact(content: bytes) -> dict[str, Any]:
    """Convert PDF content into a Reader artifact (HTML + TOC)."""
    return _build_pdf_reader_structure(content, include_html=True)


def extract_pdf_toc(content: bytes) -> dict[str, Any]:
    """Extract smart TOC data from a PDF without rendering full reader HTML."""
    payload = _build_pdf_reader_structure(content, include_html=False)
    return {
        "toc_items": payload.get("toc_items", []),
        "toc_source": payload.get("toc_source", "none"),
        "page_count": payload.get("page_count", 0),
        "error": payload.get("error"),
    }


def convert_pdf_to_html(content: bytes) -> str:
    """
    Convert PDF content to HTML.
    Uses PyMuPDF (fitz) to extract text with formatting.
    """
    artifact = convert_pdf_to_reader_artifact(content)
    html_content = (artifact.get("html_content") or "").strip()
    if html_content:
        return html_content

    error = artifact.get("error")
    if error:
        return f"<p>{_escape_html(str(error))}</p>"

    return "<p>No text content could be extracted from this PDF.</p>"


def convert_word_to_html(content: bytes) -> str:
    """
    Convert Word document (docx) to HTML.
    Uses mammoth for better HTML conversion.
    """
    try:
        import mammoth
    except ImportError:
        logger.error("mammoth not installed")
        return "<p>Word conversion not available. Please install mammoth.</p>"
    
    try:
        result = mammoth.convert_to_html(io.BytesIO(content))
        html = result.value
        
        # Clean up the HTML a bit
        if not html.strip():
            html = "<p>No content could be extracted from this document.</p>"
        
        return html
        
    except Exception as e:
        logger.error(f"Word conversion error: {e}")
        # Try python-docx as fallback
        return convert_word_to_html_fallback(content)


def convert_word_to_html_fallback(content: bytes) -> str:
    """
    Fallback Word conversion using python-docx.
    """
    try:
        from docx import Document
    except ImportError:
        return "<p>Word conversion not available.</p>"
    
    try:
        doc = Document(io.BytesIO(content))
        html_parts = []
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            
            # Check for heading styles
            if para.style and para.style.name:
                style = para.style.name.lower()
                if "heading 1" in style:
                    html_parts.append(f"<h1>{text}</h1>")
                elif "heading 2" in style:
                    html_parts.append(f"<h2>{text}</h2>")
                elif "heading 3" in style:
                    html_parts.append(f"<h3>{text}</h3>")
                elif "title" in style:
                    html_parts.append(f"<h1>{text}</h1>")
                else:
                    html_parts.append(f"<p>{text}</p>")
            else:
                html_parts.append(f"<p>{text}</p>")
        
        return "\n".join(html_parts) if html_parts else "<p>No content found.</p>"
        
    except Exception as e:
        logger.error(f"Word fallback conversion error: {e}")
        return f"<p>Error converting Word document: {str(e)}</p>"


def convert_text_to_html(content: bytes) -> str:
    """
    Convert plain text to HTML.
    """
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except:
            text = content.decode("utf-8", errors="replace")
    
    # Convert newlines to paragraphs
    paragraphs = text.split("\n\n")
    html_parts = []
    
    for para in paragraphs:
        para = para.strip()
        if para:
            # Escape HTML characters
            para = para.replace("&", "&amp;")
            para = para.replace("<", "&lt;")
            para = para.replace(">", "&gt;")
            # Convert single newlines to <br>
            para = para.replace("\n", "<br>")
            html_parts.append(f"<p>{para}</p>")
    
    return "\n".join(html_parts) if html_parts else "<p>No content.</p>"


def convert_document_to_html(content: bytes, mime_type: str, filename: str = "") -> Optional[str]:
    """
    Convert a document to HTML based on its MIME type.
    
    Returns HTML string or None if conversion is not supported.
    """
    mime_type = mime_type.lower()
    filename = filename.lower()
    
    # PDF
    if mime_type == "application/pdf" or filename.endswith(".pdf"):
        return convert_pdf_to_html(content)
    
    # Word documents
    if mime_type in [
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ] or filename.endswith(".docx") or filename.endswith(".doc"):
        return convert_word_to_html(content)
    
    # Plain text
    if mime_type.startswith("text/") or filename.endswith(".txt"):
        return convert_text_to_html(content)

    # Markdown
    if mime_type in ["text/markdown", "text/x-markdown"] or filename.endswith(".md"):
        return convert_text_to_html(content)

    # HTML content
    if mime_type in ["text/html", "application/xhtml+xml"] or filename.endswith(".html") or filename.endswith(".htm"):
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("utf-8", errors="replace")

    # JSON - show as formatted text
    if mime_type == "application/json" or filename.endswith(".json"):
        return convert_text_to_html(content)
    
    # RTF - treat as text for now
    if mime_type == "application/rtf" or filename.endswith(".rtf"):
        return convert_text_to_html(content)
    
    logger.info(f"No converter for mime_type={mime_type}, filename={filename}")
    return None


__all__ = [
    "convert_document_to_html",
    "convert_pdf_to_html",
    "convert_pdf_to_reader_artifact",
    "extract_pdf_toc",
    "convert_word_to_html",
]
