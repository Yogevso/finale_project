"""
Document Converter Utility

Converts various document types (PDF, Word, etc.) to HTML for editing.
"""

import html
import io
import logging
import math
import re
from collections import Counter
from typing import Any, Optional

logger = logging.getLogger(__name__)

HEADING_NUMBER_RE = re.compile(r"^(\d+(?:\.\d+)*)[.)]?\s+\S+")
UPPERCASE_HEADING_RE = re.compile(r"^[A-Z0-9][A-Z0-9\s\-_/]{3,}$")
TOC_HEADER_RE = re.compile(r"\b(table\s+of\s+contents|contents)\b", re.IGNORECASE)
TOC_ENTRY_RE = re.compile(r"^(?P<title>.+?)(?:\s*[.\u2022·_-]{2,}\s*|\s{2,}|\t+)(?P<page>\d{1,4})$")
TOC_INLINE_PAGE_RE = re.compile(r"^(?P<title>.+?)\s+(?P<page>\d{1,4})$")
TOC_PAGE_ONLY_RE = re.compile(r"^(?:p(?:age)?\s*)?(?P<page>\d{1,4})$", re.IGNORECASE)
LIST_BULLET_RE = re.compile(r"^(?:[\u2022\u2023\u25E6\u2043\u2219•\-*])\s+(?P<text>.+)$")
LIST_NUMBERED_RE = re.compile(r"^(?P<marker>\d+(?:\.\d+)*[.)])\s+(?P<text>.+)$")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
TOKEN_RE = re.compile(r"[A-Za-z0-9@._%-]{2,}")
EMPLOYEE_ID_RE = re.compile(r"\b\d{7,12}\b")
INTEL_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@intel\.com\b", re.IGNORECASE)
WATERMARK_ROTATION_THRESHOLD_DEG = 2.5
WATERMARK_LOW_OPACITY_THRESHOLD = 0.35


def _escape_html(value: str) -> str:
    return html.escape(value, quote=True)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return slug or "section"


def _strip_leader_dots(value: str) -> str:
    cleaned = re.sub(r"\.{2,}", " ", value or "")
    return _normalize_text(cleaned)


def _derive_level_from_numbering(title: str) -> Optional[int]:
    match = HEADING_NUMBER_RE.match(title or "")
    if not match:
        return None
    try:
        depth = match.group(1).count(".") + 1
    except Exception:
        return None
    return min(max(depth, 1), 6)


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = _normalize_text(value).lower()
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        output.append(value)
    return output


def _format_table_pre_line(value: str) -> str:
    """Normalize fallback preformatted table lines while preserving alignment."""
    return (value or "").replace("\u00a0", " ").expandtabs(4).rstrip()


def _is_bold_span(flags: int, font_name: str) -> bool:
    return bool(flags & (1 << 4)) or "bold" in (font_name or "").lower()


def _is_italic_span(flags: int, font_name: str) -> bool:
    return bool(flags & (1 << 1)) or "italic" in (font_name or "").lower()


def _is_monospace_font(font_name: str) -> bool:
    normalized = (font_name or "").lower()
    return any(
        token in normalized
        for token in ("courier", "mono", "consolas", "menlo", "sourcecode", "liberationmono")
    )


def _is_table_like_text(value: str) -> bool:
    raw = (value or "").strip()
    if not raw:
        return False
    if "|" in raw and len([part for part in raw.split("|") if part.strip()]) >= 3:
        return True
    columns = [segment for segment in re.split(r"\s{2,}|\t+", raw) if segment.strip()]
    if len(columns) >= 3:
        return True
    return False


def _token_repetition_ratio(value: str) -> tuple[float, int]:
    tokens = [token.lower() for token in TOKEN_RE.findall(value or "")]
    if not tokens:
        return 0.0, 0
    token_counter = Counter(tokens)
    repeated_token_count = sum(count for count in token_counter.values() if count > 1)
    return repeated_token_count / float(len(tokens)), len(tokens)


def _looks_garbled_text(value: str) -> bool:
    text = _normalize_text(value)
    if not text:
        return False

    repetition_ratio, token_count = _token_repetition_ratio(text)
    if token_count >= 12 and repetition_ratio >= 0.5:
        return True

    email_hits = EMAIL_RE.findall(text)
    if len(email_hits) >= 3:
        email_counter = Counter(hit.lower() for hit in email_hits)
        if email_counter.most_common(1)[0][1] >= 2:
            return True

    return False


def _normalize_opacity_value(raw_value: Any) -> Optional[float]:
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return None

    if value < 0:
        return None
    if value <= 1.0:
        return value
    if value <= 100.0:
        return value / 100.0
    if value <= 255.0:
        return value / 255.0
    return None


def _extract_span_opacity(span: dict[str, Any]) -> Optional[float]:
    """Best-effort extraction of text span opacity across PyMuPDF variants."""
    candidates = (
        "opacity",
        "alpha",
        "fill_opacity",
        "stroke_opacity",
        "fill-opacity",
        "stroke-opacity",
    )
    values: list[float] = []
    for field in candidates:
        if field not in span:
            continue
        normalized = _normalize_opacity_value(span.get(field))
        if normalized is not None:
            values.append(normalized)
    if not values:
        return None
    return min(values)


def _extract_span_rotation_degrees(line: dict[str, Any], span: dict[str, Any]) -> float:
    """Resolve span rotation angle using span matrix when available, else line direction."""
    matrix = span.get("matrix")
    if isinstance(matrix, (list, tuple)) and len(matrix) >= 2:
        try:
            a = float(matrix[0])
            b = float(matrix[1])
            if abs(a) > 1e-6 or abs(b) > 1e-6:
                return math.degrees(math.atan2(b, a))
        except (TypeError, ValueError):
            pass

    direction = line.get("dir")
    if isinstance(direction, (list, tuple)) and len(direction) >= 2:
        try:
            dx = float(direction[0])
            dy = float(direction[1])
            if abs(dx) > 1e-6 or abs(dy) > 1e-6:
                return math.degrees(math.atan2(dy, dx))
        except (TypeError, ValueError):
            pass

    return 0.0


def _is_nonzero_rotation(rotation_degrees: float) -> bool:
    normalized = abs(float(rotation_degrees)) % 180.0
    distance_from_horizontal = min(normalized, abs(180.0 - normalized))
    return distance_from_horizontal > WATERMARK_ROTATION_THRESHOLD_DEG


def _contains_watermark_pattern(value: str) -> bool:
    text = _normalize_text(value).lower()
    if not text:
        return False
    if "@intel.com" in text:
        return True
    if INTEL_EMAIL_RE.search(text):
        return True
    if EMPLOYEE_ID_RE.search(text):
        return True
    return False


def _iter_page_text_spans(page) -> list[dict[str, Any]]:
    """Collect normalized span metadata for watermark candidate detection."""
    try:
        blocks = page.get_text("dict").get("blocks", [])
    except Exception:
        return []

    spans: list[dict[str, Any]] = []
    for block in blocks:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                raw_text = str(span.get("text") or "")
                text = _normalize_text(raw_text)
                if not text and not raw_text.strip():
                    continue
                spans.append(
                    {
                        "text": text,
                        "rotation_degrees": _extract_span_rotation_degrees(line, span),
                        "opacity": _extract_span_opacity(span),
                    }
                )
    return spans


def _detect_repeated_watermark_texts(doc, page_count: int) -> set[str]:
    """Identify suspicious repeated watermark strings across multiple pages."""
    page_hits: dict[str, set[int]] = {}
    for page_index in range(page_count):
        page_number = page_index + 1
        page = doc[page_index]
        seen_in_page: set[str] = set()

        for span_meta in _iter_page_text_spans(page):
            text = _normalize_text(str(span_meta.get("text") or ""))
            if len(text) < 5:
                continue
            key = text.lower()

            rotation_degrees = float(span_meta.get("rotation_degrees", 0.0) or 0.0)
            is_rotated = _is_nonzero_rotation(rotation_degrees)
            opacity = span_meta.get("opacity")
            is_low_opacity = (
                opacity is not None and float(opacity) <= WATERMARK_LOW_OPACITY_THRESHOLD
            )
            has_pattern = _contains_watermark_pattern(text)

            if not (is_rotated or is_low_opacity or has_pattern):
                continue
            seen_in_page.add(key)

        for key in seen_in_page:
            page_hits.setdefault(key, set()).add(page_number)

    return {text for text, pages in page_hits.items() if len(pages) >= 2}


def _should_filter_watermark_span(
    text: str,
    *,
    line: dict[str, Any],
    span: dict[str, Any],
    repeated_watermark_texts: Optional[set[str]] = None,
) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False

    repeated_candidates = repeated_watermark_texts or set()
    text_key = normalized.lower()

    rotation_degrees = _extract_span_rotation_degrees(line, span)
    is_rotated = _is_nonzero_rotation(rotation_degrees)
    opacity = _extract_span_opacity(span)
    is_low_opacity = opacity is not None and opacity <= WATERMARK_LOW_OPACITY_THRESHOLD
    has_pattern = _contains_watermark_pattern(normalized)
    appears_repeated = text_key in repeated_candidates

    if is_low_opacity:
        return True
    if is_rotated and (appears_repeated or has_pattern or len(normalized) >= 12):
        return True
    if appears_repeated and has_pattern:
        return True
    return False


def _parse_list_item(line_text: str) -> Optional[tuple[str, str]]:
    text = _normalize_text(line_text)
    if not text:
        return None

    bullet_match = LIST_BULLET_RE.match(text)
    if bullet_match:
        return "ul", _normalize_text(bullet_match.group("text"))

    numbered_match = LIST_NUMBERED_RE.match(text)
    if numbered_match:
        return "ol", _normalize_text(numbered_match.group("text"))

    return None


def _extract_table_fallback_pre_blocks(
    page, page_number: int
) -> tuple[list[dict[str, Any]], list[tuple[float, float, float, float]]]:
    lines = _collect_pdf_lines(page, [])
    if not lines:
        return [], []

    grouped_lines: list[list[dict[str, Any]]] = []
    current_group: list[dict[str, Any]] = []

    for line in lines:
        raw_text = str(line.get("raw_text") or line.get("text") or "")
        normalized_text = _normalize_text(raw_text)
        line_is_table_like = _is_table_like_text(raw_text) or _is_table_like_text(normalized_text)
        line_is_mono = bool(line.get("is_monospace"))

        if line_is_table_like and (line_is_mono or "\t" in raw_text or "  " in raw_text):
            current_group.append(line)
        else:
            if len(current_group) >= 2:
                grouped_lines.append(current_group)
            current_group = []

    if len(current_group) >= 2:
        grouped_lines.append(current_group)

    table_entries: list[dict[str, Any]] = []
    table_bboxes: list[tuple[float, float, float, float]] = []

    for group_index, group in enumerate(grouped_lines):
        raw_lines = [
            _format_table_pre_line(str(item.get("raw_text") or item.get("text") or ""))
            for item in group
            if _normalize_text(str(item.get("raw_text") or item.get("text") or ""))
        ]
        if len(raw_lines) < 2:
            continue

        min_x = min(float(item.get("x0", 0.0) or 0.0) for item in group)
        min_y = min(float(item.get("y0", 0.0) or 0.0) for item in group)
        max_x = max(float(item.get("bbox", (0.0, 0.0, 0.0, 0.0))[2]) for item in group)
        max_y = max(float(item.get("bbox", (0.0, 0.0, 0.0, 0.0))[3]) for item in group)
        bbox = (min_x, min_y, max_x, max_y)
        table_bboxes.append(bbox)

        pre_content = "\n".join(_escape_html(line) for line in raw_lines)
        table_entries.append(
            {
                "html": (
                    f"<div class='pdf-table-wrap pdf-table-fallback' data-page='{page_number}'>"
                    f"<pre>{pre_content}</pre></div>"
                ),
                "bbox": bbox,
                "y0": min_y,
                "fallback": True,
                "id": f"pre-table-{page_number}-{group_index}",
            }
        )

    table_entries.sort(key=lambda item: item.get("y0", 0.0))
    return table_entries, table_bboxes


def _extract_pdf_tables_with_bboxes(
    page,
    page_number: int,
) -> tuple[list[dict[str, Any]], list[tuple[float, float, float, float]]]:
    """Extract table-like structures and their rough page coordinates."""
    if not hasattr(page, "find_tables"):
        return _extract_table_fallback_pre_blocks(page, page_number)

    try:
        tables_result = page.find_tables()
    except Exception as exc:
        logger.debug("PDF table detection failed: %s", exc)
        return _extract_table_fallback_pre_blocks(page, page_number)

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
            "<div class='pdf-table-wrap pdf-table-grid'>",
            "<table class='pdf-table'>",
            "<thead><tr>",
        ]
        table_parts.extend(
            f"<th class='pdf-table-cell'>{cell if cell else '&nbsp;'}</th>" for cell in header_row
        )
        table_parts.append("</tr></thead>")

        if body_rows:
            table_parts.append("<tbody>")
            for row in body_rows:
                table_parts.append("<tr>")
                table_parts.extend(
                    f"<td class='pdf-table-cell'>{cell if cell else '&nbsp;'}</td>" for cell in row
                )
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
    if table_entries:
        return table_entries, table_bboxes

    return _extract_table_fallback_pre_blocks(page, page_number)


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
    line_bbox: tuple[float, float, float, float],
    table_bboxes: list[tuple[float, float, float, float]],
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
            span_raw_parts: list[str] = []
            max_size = 0.0
            is_bold = False
            monospace_count = 0
            span_count = 0
            min_x = float("inf")
            min_y = float("inf")
            max_x = 0.0
            max_y = 0.0

            for span in spans:
                raw_span_text = str(span.get("text") or "")
                text = _normalize_text(raw_span_text)
                if not text and not raw_span_text.strip():
                    continue
                span_count += 1

                flags = int(span.get("flags", 0) or 0)
                font_name = str(span.get("font", "") or "")
                size = float(span.get("size", 0.0) or 0.0)
                if _is_monospace_font(font_name):
                    monospace_count += 1
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
                span_raw_parts.append(raw_span_text)

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
            raw_text = " ".join(part.replace("\n", " ") for part in span_raw_parts).rstrip()
            html_text = " ".join(span_html_parts).strip()
            if not plain_text or not html_text:
                continue

            lines.append(
                {
                    "text": plain_text,
                    "raw_text": raw_text or plain_text,
                    "html": html_text,
                    "size": max_size if max_size > 0 else 12.0,
                    "is_bold": is_bold,
                    "is_monospace": (monospace_count / span_count) >= 0.5 if span_count else False,
                    "bbox": line_bbox,
                    "y0": line_bbox[1],
                    "x0": line_bbox[0],
                }
            )

    lines.sort(key=lambda item: (round(float(item.get("y0", 0.0)), 1), float(item.get("x0", 0.0))))
    return lines


def _safe_bbox_tuple(raw_bbox: Any) -> tuple[float, float, float, float]:
    if isinstance(raw_bbox, (list, tuple)) and len(raw_bbox) >= 4:
        try:
            return (
                float(raw_bbox[0]),
                float(raw_bbox[1]),
                float(raw_bbox[2]),
                float(raw_bbox[3]),
            )
        except (TypeError, ValueError):
            return (0.0, 0.0, 0.0, 0.0)
    return (0.0, 0.0, 0.0, 0.0)


def _collect_pdf_visual_blocks(
    page,
    table_bboxes: list[tuple[float, float, float, float]],
    repeated_watermark_texts: Optional[set[str]] = None,
) -> list[dict[str, Any]]:
    """Collect text grouped by visual blocks to improve reading order."""
    try:
        blocks = page.get_text("dict").get("blocks", [])
    except Exception:
        return []

    visual_blocks: list[dict[str, Any]] = []

    for block_index, block in enumerate(blocks):
        if block.get("type") != 0:
            continue

        block_bbox = _safe_bbox_tuple(block.get("bbox"))
        if _line_intersects_table(block_bbox, table_bboxes):
            continue

        line_items: list[dict[str, Any]] = []
        previous_line_key: Optional[str] = None

        for line in block.get("lines", []):
            spans = line.get("spans", [])
            span_html_parts: list[str] = []
            span_plain_parts: list[str] = []
            span_raw_parts: list[str] = []
            max_size = 0.0
            bold_count = 0
            total_count = 0
            monospace_count = 0

            for span in spans:
                raw_span_text = str(span.get("text") or "")
                text = _normalize_text(raw_span_text)
                if not text and not raw_span_text.strip():
                    continue
                if _should_filter_watermark_span(
                    raw_span_text,
                    line=line,
                    span=span,
                    repeated_watermark_texts=repeated_watermark_texts,
                ):
                    continue
                total_count += 1
                flags = int(span.get("flags", 0) or 0)
                font_name = str(span.get("font", "") or "")
                size = float(span.get("size", 0.0) or 0.0)
                if _is_monospace_font(font_name):
                    monospace_count += 1
                is_bold = _is_bold_span(flags, font_name)
                if is_bold:
                    bold_count += 1

                max_size = max(max_size, size)
                span_plain_parts.append(text)
                span_raw_parts.append(raw_span_text)

                rendered = _escape_html(text)
                if is_bold:
                    rendered = f"<strong>{rendered}</strong>"
                if _is_italic_span(flags, font_name):
                    rendered = f"<em>{rendered}</em>"
                span_html_parts.append(rendered)

            if not span_plain_parts:
                continue

            line_text = _normalize_text(" ".join(span_plain_parts))
            if _looks_garbled_text(line_text):
                continue
            line_key = line_text.lower()
            if previous_line_key and line_key == previous_line_key:
                continue
            previous_line_key = line_key

            line_bbox = _safe_bbox_tuple(line.get("bbox"))
            if _line_intersects_table(line_bbox, table_bboxes):
                continue

            line_items.append(
                {
                    "text": line_text,
                    "raw_text": " ".join(
                        part.replace("\n", " ") for part in span_raw_parts
                    ).rstrip()
                    or line_text,
                    "html": " ".join(span_html_parts).strip(),
                    "size": max_size if max_size > 0 else 12.0,
                    "is_bold": (bold_count / total_count) >= 0.5 if total_count > 0 else False,
                    "is_monospace": (monospace_count / total_count) >= 0.5
                    if total_count > 0
                    else False,
                    "bbox": line_bbox,
                    "y0": line_bbox[1],
                    "x0": line_bbox[0],
                }
            )

        if not line_items:
            continue

        line_items.sort(
            key=lambda item: (round(float(item.get("y0", 0.0)), 1), float(item.get("x0", 0.0)))
        )

        deduped_line_texts = _dedupe_preserve_order([str(line["text"]) for line in line_items])
        if not deduped_line_texts:
            continue

        avg_size = (
            sum(float(line.get("size", 12.0) or 12.0) for line in line_items) / len(line_items)
            if line_items
            else 12.0
        )
        max_size = max(float(line.get("size", 12.0) or 12.0) for line in line_items)
        bold_ratio = (
            sum(1 for line in line_items if bool(line.get("is_bold"))) / len(line_items)
            if line_items
            else 0.0
        )
        monospace_ratio = (
            sum(1 for line in line_items if bool(line.get("is_monospace"))) / len(line_items)
            if line_items
            else 0.0
        )

        visual_blocks.append(
            {
                "block_index": block_index,
                "bbox": block_bbox,
                "x0": block_bbox[0],
                "y0": block_bbox[1],
                "text": _normalize_text(" ".join(deduped_line_texts)),
                "line_texts": deduped_line_texts,
                "line_html": [
                    str(line.get("html") or "") for line in line_items if line.get("html")
                ],
                "line_items": line_items,
                "avg_size": avg_size,
                "max_size": max_size,
                "bold_ratio": bold_ratio,
                "monospace_ratio": monospace_ratio,
                "line_count": len(line_items),
            }
        )

    visual_blocks.sort(
        key=lambda block: (round(float(block.get("y0", 0.0)), 1), float(block.get("x0", 0.0)))
    )
    return visual_blocks


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


def _estimate_body_font_size_from_blocks(blocks: list[dict[str, Any]]) -> float:
    if not blocks:
        return 12.0

    sizes = sorted(
        float(block.get("avg_size", block.get("max_size", 12.0)) or 12.0)
        for block in blocks
        if float(block.get("avg_size", block.get("max_size", 0.0)) or 0.0) > 0
    )
    if not sizes:
        return 12.0
    return sizes[len(sizes) // 2]


def _classify_heading_level_from_block(
    block: dict[str, Any], body_font_size: float
) -> Optional[int]:
    text = _normalize_text(str(block.get("text") or ""))
    if not text:
        return None

    words = text.split()
    if len(words) < 1 or len(words) > 24:
        return None
    if len(text) > 200:
        return None

    size = float(block.get("max_size", block.get("avg_size", body_font_size)) or body_font_size)
    size_delta = size - body_font_size
    bold_ratio = float(block.get("bold_ratio", 0.0) or 0.0)
    is_bold = bold_ratio >= 0.45
    is_numbered = bool(HEADING_NUMBER_RE.match(text))
    is_upper = bool(UPPERCASE_HEADING_RE.match(text))

    if len(words) <= 2 and not is_numbered:
        return None

    # Filter common body-like lines even if bold.
    if text.endswith(".") and len(words) > 10 and not is_numbered and size_delta < 2.0:
        return None

    if is_numbered:
        depth = _derive_level_from_numbering(text) or 1
        return min(depth, 4)

    if size_delta >= 6.0:
        return 1
    if size_delta >= 3.5:
        return 2
    if size_delta >= 1.8:
        return 3
    if is_bold and len(words) <= 16:
        return 3
    if is_upper and len(words) <= 14:
        return 2
    return None


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


def _collect_heading_candidates_from_blocks(
    blocks: list[dict[str, Any]], page_number: int, body_font_size: float
) -> list[dict[str, Any]]:
    headings: list[dict[str, Any]] = []
    for block in blocks:
        level = _classify_heading_level_from_block(block, body_font_size)
        if not level:
            continue
        title = _normalize_text(str(block.get("text") or ""))
        if not title:
            continue
        anchor_id = _build_anchor_id(page_number, title, len(headings))
        headings.append(
            {
                "title": title,
                "level": level,
                "page_start": page_number,
                "anchor_id": anchor_id,
                "normalized_title": title.lower(),
            }
        )
    return headings


def _render_pdf_page_html(
    visual_blocks: list[dict[str, Any]],
    table_entries: list[dict[str, Any]],
    page_number: int,
    body_font_size: float,
) -> tuple[list[str], list[dict[str, Any]]]:
    """Render reader HTML using visual block order with table interleaving."""
    page_parts: list[str] = []
    page_headings: list[dict[str, Any]] = []
    last_emitted_body_key: Optional[str] = None

    events: list[tuple[float, float, int, str, Any]] = []
    for block_index, block in enumerate(visual_blocks):
        events.append(
            (
                float(block.get("y0", 0.0)),
                float(block.get("x0", 0.0)),
                block_index,
                "block",
                block,
            )
        )
    for table_index, table in enumerate(table_entries):
        bbox = table.get("bbox")
        x0 = float(bbox[0]) if isinstance(bbox, (list, tuple)) and len(bbox) >= 1 else 0.0
        events.append(
            (
                float(table.get("y0", 0.0)),
                x0,
                table_index,
                "table",
                table,
            )
        )
    events.sort(key=lambda item: (round(item[0], 2), round(item[1], 2), item[2]))

    for _, _, _, event_type, payload in events:
        if event_type == "table":
            table_html = str(payload.get("html") or "")
            if table_html:
                if "data-page=" in table_html:
                    page_parts.append(table_html)
                else:
                    page_parts.append(
                        f"<div class='pdf-table-wrap' data-page='{page_number}'>{table_html}</div>"
                    )
            last_emitted_body_key = None
            continue

        block = payload
        block_text = _normalize_text(str(block.get("text") or ""))
        if not block_text:
            continue
        if _looks_garbled_text(block_text):
            continue

        deduped_lines = _dedupe_preserve_order(
            [str(line) for line in block.get("line_texts", []) if _normalize_text(str(line))]
        )
        line_items = [line for line in block.get("line_items", []) if isinstance(line, dict)]

        list_candidates: list[tuple[str, str]] = []
        for line in deduped_lines:
            parsed_item = _parse_list_item(line)
            if parsed_item:
                list_candidates.append(parsed_item)

        if list_candidates and len(list_candidates) >= max(2, len(deduped_lines) // 2):
            list_type = list_candidates[0][0]
            if all(candidate[0] == list_type for candidate in list_candidates):
                page_parts.append(f"<{list_type} data-page='{page_number}'>")
                for _, list_text in list_candidates:
                    if not list_text or _looks_garbled_text(list_text):
                        continue
                    page_parts.append(f"<li>{_escape_html(list_text)}</li>")
                page_parts.append(f"</{list_type}>")
                last_emitted_body_key = None
                continue

        heading_level = _classify_heading_level_from_block(block, body_font_size)
        if heading_level:
            anchor_id = _build_anchor_id(page_number, block_text, len(page_headings))
            page_parts.append(
                f"<h{heading_level} id='{anchor_id}' data-page='{page_number}'>{_escape_html(block_text)}</h{heading_level}>"
            )
            page_headings.append(
                {
                    "title": block_text,
                    "level": heading_level,
                    "page_start": page_number,
                    "anchor_id": anchor_id,
                    "normalized_title": block_text.lower(),
                }
            )
            last_emitted_body_key = None
            continue

        if line_items and float(block.get("monospace_ratio", 0.0) or 0.0) >= 0.75:
            raw_lines = _dedupe_preserve_order(
                [
                    _format_table_pre_line(str(line.get("raw_text") or line.get("text") or ""))
                    for line in line_items
                    if _normalize_text(str(line.get("raw_text") or line.get("text") or ""))
                ]
            )
            if raw_lines and any(_is_table_like_text(line) for line in raw_lines):
                pre_payload = "\n".join(_escape_html(line) for line in raw_lines)
                page_parts.append(
                    (
                        f"<div class='pdf-table-wrap pdf-table-fallback' data-page='{page_number}'>"
                        f"<pre>{pre_payload}</pre></div>"
                    )
                )
                last_emitted_body_key = None
                continue

        if deduped_lines:
            cleaned_lines = [line for line in deduped_lines if not _looks_garbled_text(line)]
            if cleaned_lines:
                paragraph_text = _normalize_text(" ".join(cleaned_lines))
            else:
                paragraph_text = ""
        else:
            paragraph_text = block_text if not _looks_garbled_text(block_text) else ""

        if not paragraph_text:
            continue

        paragraph_key = paragraph_text.lower()
        if last_emitted_body_key and paragraph_key == last_emitted_body_key:
            continue

        page_parts.append(f"<p data-page='{page_number}'>{_escape_html(paragraph_text)}</p>")
        last_emitted_body_key = paragraph_key

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
                            or str(heading.get("normalized_title") or "")
                            in normalized_outline_title
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


def _resolve_toc_anchor_id(
    title: str, page_start: int, headings_by_page: dict[int, list[dict[str, Any]]]
) -> str:
    normalized_title = _normalize_text(title).lower()
    page_headings = headings_by_page.get(page_start, [])
    if not page_headings:
        return f"pdf-page-{page_start}"

    exact = next(
        (
            item
            for item in page_headings
            if str(item.get("normalized_title") or "") == normalized_title
        ),
        None,
    )
    if exact:
        return str(exact.get("anchor_id") or f"pdf-page-{page_start}")

    fuzzy = next(
        (
            item
            for item in page_headings
            if normalized_title
            and (
                normalized_title in str(item.get("normalized_title") or "")
                or str(item.get("normalized_title") or "") in normalized_title
            )
        ),
        None,
    )
    if fuzzy:
        return str(fuzzy.get("anchor_id") or f"pdf-page-{page_start}")
    return str(page_headings[0].get("anchor_id") or f"pdf-page-{page_start}")


def _parse_toc_entry_line(raw_text: str) -> Optional[tuple[str, int]]:
    text = _normalize_text(raw_text)
    if not text or TOC_HEADER_RE.search(text):
        return None
    if len(text) < 4:
        return None

    match = TOC_ENTRY_RE.match(text)
    if not match:
        inline_match = TOC_INLINE_PAGE_RE.match(text)
        if inline_match:
            title_candidate = _strip_leader_dots(inline_match.group("title"))
            page_candidate = inline_match.group("page")
            # Avoid false positives on lines like "2026 7" or simple IDs.
            if len(title_candidate.split()) >= 2 or _derive_level_from_numbering(title_candidate):
                match = inline_match
                text = f"{title_candidate} {page_candidate}"
        if not match:
            return None

    title = _strip_leader_dots(match.group("title"))
    if not title:
        return None

    try:
        page_number = int(match.group("page"))
    except (TypeError, ValueError):
        return None
    if page_number < 1:
        return None

    return title, page_number


def _build_heading_page_index(
    headings_by_page: dict[int, list[dict[str, Any]]],
) -> dict[str, list[int]]:
    index: dict[str, list[int]] = {}
    for page_number, headings in headings_by_page.items():
        for heading in headings:
            normalized_title = _normalize_text(str(heading.get("title") or "")).lower()
            if not normalized_title:
                continue
            pages = index.setdefault(normalized_title, [])
            if page_number not in pages:
                pages.append(page_number)
    return index


def _find_heading_page_for_title(
    title: str, heading_page_index: dict[str, list[int]]
) -> Optional[int]:
    normalized_title = _normalize_text(title).lower()
    if not normalized_title:
        return None

    direct_pages = heading_page_index.get(normalized_title)
    if direct_pages:
        return direct_pages[0]

    for candidate_title, pages in heading_page_index.items():
        if normalized_title in candidate_title or candidate_title in normalized_title:
            return pages[0]
    return None


def _extract_contents_page_toc(
    doc, page_count: int, headings_by_page: dict[int, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    """Fallback TOC extraction from visible Contents page when bookmarks are missing."""
    if page_count <= 0:
        return []

    max_scan_pages = min(page_count, 10)
    toc_start_page: Optional[int] = None
    best_candidate_page: Optional[int] = None
    best_candidate_score = -1

    for page_index in range(max_scan_pages):
        page = doc[page_index]
        lines = _collect_pdf_lines(page, [])
        if not lines:
            continue

        line_texts = [_normalize_text(str(line.get("text") or "")) for line in lines]
        line_texts = [line for line in line_texts if line]
        if not line_texts:
            continue

        joined_page_text = " ".join(line_texts)
        has_header = bool(TOC_HEADER_RE.search(joined_page_text))

        parsed_entries = 0
        for line_index, raw_line in enumerate(line_texts):
            if _parse_toc_entry_line(raw_line):
                parsed_entries += 1
                continue

            if line_index + 1 >= len(line_texts):
                continue

            next_line = line_texts[line_index + 1]
            page_only_match = TOC_PAGE_ONLY_RE.match(next_line)
            if page_only_match and _parse_toc_entry_line(
                f"{raw_line} {page_only_match.group('page')}"
            ):
                parsed_entries += 1
                continue

            if _parse_toc_entry_line(f"{raw_line} {next_line}"):
                parsed_entries += 1

        score = parsed_entries + (5 if has_header else 0)
        if score > best_candidate_score:
            best_candidate_score = score
            best_candidate_page = page_index + 1

        if has_header and parsed_entries >= 2:
            toc_start_page = page_index + 1
            break

    if toc_start_page is None:
        if best_candidate_page and best_candidate_score >= 4:
            toc_start_page = best_candidate_page
        else:
            return []

    toc_candidates: list[dict[str, Any]] = []
    empty_streak = 0
    stop_page = min(page_count, toc_start_page + 6)

    for page_number in range(toc_start_page, stop_page + 1):
        page = doc[page_number - 1]
        lines = _collect_pdf_lines(page, [])
        if not lines:
            empty_streak += 1
            if empty_streak >= 2:
                break
            continue

        page_entries = 0
        min_x = min(float(line.get("x0", 0.0) or 0.0) for line in lines) if lines else 0.0

        line_index = 0
        while line_index < len(lines):
            line = lines[line_index]
            raw_text = _normalize_text(str(line.get("text") or ""))
            if not raw_text:
                line_index += 1
                continue

            parsed = _parse_toc_entry_line(raw_text)
            consumed_next = False

            if not parsed and line_index + 1 < len(lines):
                next_text = _normalize_text(str(lines[line_index + 1].get("text") or ""))
                page_only_match = TOC_PAGE_ONLY_RE.match(next_text or "")
                if page_only_match:
                    parsed = _parse_toc_entry_line(f"{raw_text} {page_only_match.group('page')}")
                    consumed_next = parsed is not None
                if not parsed and next_text:
                    parsed = _parse_toc_entry_line(f"{raw_text} {next_text}")
                    consumed_next = parsed is not None

            if not parsed:
                line_index += 1
                continue

            title, parsed_page = parsed
            if parsed_page > page_count:
                line_index += 2 if consumed_next else 1
                continue

            numbering_level = _derive_level_from_numbering(title)
            if numbering_level is not None:
                level = numbering_level
            else:
                x0 = float(line.get("x0", min_x) or min_x)
                indent = max(0.0, x0 - min_x)
                level = min(6, int(indent // 18.0) + 1)

            toc_candidates.append(
                {
                    "id": f"toc-contents-{len(toc_candidates)}",
                    "title": title,
                    "level": max(1, level),
                    "page_start": parsed_page,
                    "page_end": None,
                    "anchor_id": f"pdf-page-{parsed_page}",
                }
            )
            page_entries += 1
            line_index += 2 if consumed_next else 1

        if page_entries == 0:
            empty_streak += 1
            if empty_streak >= 2:
                break
        else:
            empty_streak = 0

    if not toc_candidates:
        return []

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for item in toc_candidates:
        key = (_normalize_text(item["title"]).lower(), int(item["page_start"]))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= 250:
            break

    heading_page_index = _build_heading_page_index(headings_by_page)
    offset_votes: dict[int, int] = {}
    for item in deduped:
        matched_page = _find_heading_page_for_title(item["title"], heading_page_index)
        if matched_page is None:
            continue
        parsed_page = int(item["page_start"])
        offset = matched_page - parsed_page
        if -25 <= offset <= 25:
            offset_votes[offset] = offset_votes.get(offset, 0) + 1

    best_offset = 0
    if offset_votes:
        best_offset, best_votes = max(
            offset_votes.items(), key=lambda pair: (pair[1], -abs(pair[0]))
        )
        if best_votes < 2:
            best_offset = 0

    remapped: list[dict[str, Any]] = []
    remapped_seen: set[tuple[str, int]] = set()
    for item in deduped:
        parsed_page = int(item["page_start"])
        mapped_page = min(page_count, max(1, parsed_page + best_offset))

        matched_page = _find_heading_page_for_title(item["title"], heading_page_index)
        if matched_page is not None and abs(matched_page - mapped_page) <= 3:
            mapped_page = matched_page

        normalized_title = _normalize_text(item["title"]).lower()
        dedupe_key = (normalized_title, mapped_page)
        if dedupe_key in remapped_seen:
            continue
        remapped_seen.add(dedupe_key)

        remapped_item = dict(item)
        remapped_item["page_start"] = mapped_page
        remapped_item["anchor_id"] = _resolve_toc_anchor_id(
            str(remapped_item["title"]), mapped_page, headings_by_page
        )
        remapped.append(remapped_item)

    if not remapped:
        return []

    for index, item in enumerate(remapped):
        item["id"] = f"toc-contents-{index}"

    _compute_page_end(remapped, page_count)
    return remapped


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
        repeated_watermark_texts = _detect_repeated_watermark_texts(doc, page_count)

        for page_index in range(page_count):
            page_number = page_index + 1
            page = doc[page_index]
            table_entries, table_bboxes = _extract_pdf_tables_with_bboxes(page, page_number)
            visual_blocks = _collect_pdf_visual_blocks(
                page,
                table_bboxes,
                repeated_watermark_texts=repeated_watermark_texts,
            )
            body_font_size = _estimate_body_font_size_from_blocks(visual_blocks)

            if include_html:
                page_html, page_headings = _render_pdf_page_html(
                    visual_blocks,
                    table_entries,
                    page_number,
                    body_font_size,
                )
            else:
                page_html = []
                page_headings = _collect_heading_candidates_from_blocks(
                    visual_blocks, page_number, body_font_size
                )

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
            toc_source = "bookmarks"
        else:
            contents_items = _extract_contents_page_toc(doc, page_count, headings_by_page)
            if contents_items:
                toc_items = contents_items
                toc_source = "contents-fallback"
            else:
                toc_items = _build_heuristic_toc(heading_items, page_count)
                toc_source = "contents-fallback" if toc_items else "none"

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
        text = content.decode("latin-1", errors="replace")

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
    if (
        mime_type
        in [
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]
        or filename.endswith(".docx")
        or filename.endswith(".doc")
    ):
        return convert_word_to_html(content)

    # Plain text
    if mime_type.startswith("text/") or filename.endswith(".txt"):
        return convert_text_to_html(content)

    # Markdown
    if mime_type in ["text/markdown", "text/x-markdown"] or filename.endswith(".md"):
        return convert_text_to_html(content)

    # HTML content
    if (
        mime_type in ["text/html", "application/xhtml+xml"]
        or filename.endswith(".html")
        or filename.endswith(".htm")
    ):
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
