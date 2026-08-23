"""Tests for layout-preserving PDF extraction.

The fixtures reproduce the shapes measured in the Intel GCC user guide: a
section heading whose number sits far to the left of its title, a running header
that alternates between the left and right margin on facing pages, and an inline
"Note:" run set larger and bolder than the body text that continues beside it.
"""

from __future__ import annotations

import fitz

from app.conversion.pdf_layout import (
    LayoutDocument,
    LayoutNode,
    LayoutPage,
    LayoutSpan,
    _classify_headings,
    _detect_chrome,
    _merge_baselines,
    extract_layout_from_document,
    join_spans,
)

BODY = 8.0
HEADING = 22.0


def _span(text, x0, y0, size=BODY, family="Verdana", bold=False, italic=False, width=None):
    span_width = width if width is not None else len(text) * size * 0.5
    return LayoutSpan(
        text=text,
        bbox=(x0, y0, x0 + span_width, y0 + size),
        font_family=family,
        font_size=size,
        bold=bold,
        italic=italic,
    )


def test_join_spans_restores_the_gap_between_a_number_and_its_title():
    """ "2" at x=76 and the title at x=141 are one heading, not one word."""
    spans = [
        _span("2", 76.0, 95.8, HEADING, "Verdana-BoldItalic", True, True, width=13.0),
        _span("Key Known Issues", 141.0, 95.8, HEADING, "Verdana-BoldItalic", True, True),
    ]

    assert join_spans(spans) == "2 Key Known Issues"


def test_join_spans_does_not_invent_spaces_between_adjacent_runs():
    spans = [_span("Intel", 76.0, 100.0, width=30.0), _span("®", 106.0, 100.0, width=6.0)]

    assert join_spans(spans) == "Intel®"


def test_merge_baselines_rejoins_a_split_heading_line():
    number = [_span("2", 76.0, 95.8, HEADING, "Verdana-BoldItalic", True, True, width=13.0)]
    title = [_span("Key Known Issues", 141.0, 95.8, HEADING, "Verdana-BoldItalic", True, True)]

    merged = _merge_baselines([number, title])

    assert len(merged) == 1
    assert join_spans(merged[0]) == "2 Key Known Issues"


def test_merge_baselines_keeps_separate_lines_apart():
    first = [_span("first line", 76.0, 100.0)]
    second = [_span("second line", 76.0, 130.0)]

    assert len(_merge_baselines([first, second])) == 2


def test_chrome_detection_survives_headers_that_alternate_sides():
    """Two-sided layouts flip the running header between margins each page."""
    pages = [LayoutPage(number=i + 1, width=612.0, height=792.0) for i in range(12)]
    pages_lines = []
    for index in range(12):
        x = 76.0 if index % 2 == 0 else 450.0
        header = [_span(f"Chapter {index // 4}", x, 85.9, BODY, "Verdana-BoldItalic", True, True)]
        body = [_span("body copy", 76.0, 300.0)]
        pages_lines.append([header, body])

    chrome = _detect_chrome(pages_lines, pages)

    assert {page for page, _ in chrome} == set(range(12))
    assert all(line == 0 for _, line in chrome)


def test_repeating_table_header_below_the_edge_stays_content():
    """A table header row repeats too, but page chrome is the outermost line."""
    pages = [LayoutPage(number=i + 1, width=612.0, height=792.0) for i in range(12)]
    pages_lines = []
    for _ in range(12):
        header = [_span("Chapter", 76.0, 85.9, BODY, "Verdana-BoldItalic", True, True)]
        table_header = [_span("Sr. No.", 42.0, 140.0, BODY, "Verdana-Bold", True)]
        pages_lines.append([header, table_header])

    chrome = _detect_chrome(pages_lines, pages)

    assert all(line == 0 for _, line in chrome), "the table header must not be chrome"


def _document_with(nodes: list[LayoutNode]) -> LayoutDocument:
    document = LayoutDocument(body_font_size=BODY, body_font_family="Verdana")
    document.nodes = nodes
    return document


def _node(text: str, spans: list[LayoutSpan], page: int = 5) -> LayoutNode:
    dominant = max(spans, key=lambda item: item.font_size)
    return LayoutNode(
        id=f"n{page}-{text[:4]}",
        type="paragraph",
        page=page,
        bbox=(spans[0].bbox[0], spans[0].bbox[1], spans[-1].bbox[2], spans[-1].bbox[3]),
        text=text,
        spans=spans,
        font_family=dominant.font_family,
        font_size=dominant.font_size,
        bold=dominant.bold,
    )


def test_an_inline_note_is_not_promoted_to_a_heading():
    """ "Note:" is 10pt bold, but the 9pt body continues on the same line."""
    note = _node(
        "Note: Some of the IGCC features were implemented differently.",
        [
            _span("Note:", 141.0, 162.4, 10.0, "Verdana-Bold", True),
            _span("Some of the IGCC features were implemented differently.", 175.1, 162.4, 9.0),
        ],
    )
    heading = _node(
        "Key Known Issues",
        [_span("Key Known Issues", 141.0, 95.8, HEADING, "Verdana-BoldItalic", True, True)],
        page=19,
    )
    document = _document_with([note, heading])

    _classify_headings(document)

    assert note.type == "paragraph"
    assert heading.type == "heading"


def test_a_line_of_pure_punctuation_is_not_a_heading():
    separator = _node("§ §", [_span("§ §", 141.0, 700.0, 12.0, "Verdana-Bold", True)], page=18)
    document = _document_with([separator])

    _classify_headings(document)

    assert separator.type == "paragraph"


def _open_pdf(pages: int = 6) -> fitz.Document:
    doc = fitz.open()
    for index in range(pages):
        page = doc.new_page()
        page.insert_text((72, 260), f"Body copy on page {index + 1}", fontsize=9)
    doc.set_toc([[1, f"Chapter {index + 1}", index + 1] for index in range(pages)])
    return doc


def test_extracting_from_an_open_document_leaves_it_to_the_caller():
    """The fidelity renderer keeps using the document after extracting from it."""
    doc = _open_pdf(pages=2)
    try:
        document = extract_layout_from_document(doc)

        assert document.error is None
        assert doc.page_count == 2  # still open: closing it here would raise
    finally:
        doc.close()


def test_max_pages_bounds_the_read():
    """Reading stops where rendering stops, outline included."""
    doc = _open_pdf(pages=6)
    try:
        document = extract_layout_from_document(doc, max_pages=2)
    finally:
        doc.close()

    assert [page.number for page in document.pages] == [1, 2]
    assert {node.page for node in document.nodes} == {1, 2}
    assert [entry.page for entry in document.outline] == [1, 2]


def test_spans_carry_the_colour_the_pdf_gave_them():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 260), "Intel blue", fontsize=9, color=(0, 0.28, 0.73))
    try:
        document = extract_layout_from_document(doc)
    finally:
        doc.close()

    assert document.nodes[0].spans[0].color != 0
