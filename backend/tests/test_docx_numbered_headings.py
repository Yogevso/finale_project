"""Numbered headings must stay headings.

Word applies automatic numbering to heading styles ("1.1 Release Kit Summary"),
which gives those paragraphs a ``numPr`` exactly like a list item has. The list
branch used to claim them first, so documents built from the standard Intel
release-notes template lost every heading and, with it, the table of contents.
"""

from __future__ import annotations

from app.conversion.docx_extractor import (
    BodyBlock,
    DocxExtractor,
    ParagraphBlock,
    ParagraphRun,
)
from app.conversion.html_generator import ir_to_html


def _paragraph(text: str, *, style: str | None = None, num_id: str | None = None) -> ParagraphBlock:
    return ParagraphBlock(runs=[ParagraphRun(text=text)], style_name=style, num_id=num_id)


def _numbered_heading(text: str, style: str) -> ParagraphBlock:
    """A heading that Word also numbers, so it carries list numbering too."""
    return _paragraph(text, style=style, num_id="7")


def _document() -> tuple[list[BodyBlock], list[ParagraphBlock]]:
    paragraphs = [
        _numbered_heading("Release Kit Summary", "heading 1"),
        _paragraph("Body copy under the first heading."),
        _paragraph("First bullet", num_id="3"),
        _paragraph("Second bullet", num_id="3"),
        _numbered_heading("Release Kit Details", "heading 2"),
        _paragraph("Body copy under the second heading."),
    ]
    return [BodyBlock(kind="paragraph", paragraph=p) for p in paragraphs], paragraphs


def _heading_lookup(extractor: DocxExtractor, paragraphs: list[ParagraphBlock]) -> dict:
    positions = extractor._extract_headings(paragraphs)
    return {id(paragraphs[index]): heading for index, heading in positions.items()}


def test_numbered_headings_reach_the_html_as_headings():
    extractor = DocxExtractor()
    blocks, paragraphs = _document()
    lookup = _heading_lookup(extractor, paragraphs)

    html = ir_to_html(extractor._build_ir(blocks, lookup))

    assert "<h1" in html and "Release Kit Summary" in html
    assert "<h2" in html and "Release Kit Details" in html


def test_real_list_items_are_still_rendered_as_a_list():
    extractor = DocxExtractor()
    blocks, paragraphs = _document()

    html = ir_to_html(extractor._build_ir(blocks, _heading_lookup(extractor, paragraphs)))

    assert "<li" in html
    assert "First bullet" in html
    assert "Second bullet" in html


def test_a_list_run_stops_at_a_numbered_heading():
    extractor = DocxExtractor()
    blocks, paragraphs = _document()
    lookup = _heading_lookup(extractor, paragraphs)

    # Collecting from the first bullet must not swallow the heading that follows it.
    run, next_index = extractor._collect_list_run(blocks, 2, lookup)

    assert [p.text for p in run] == ["First bullet", "Second bullet"]
    assert next_index == 4


def test_no_text_is_lost():
    extractor = DocxExtractor()
    blocks, paragraphs = _document()

    html = ir_to_html(extractor._build_ir(blocks, _heading_lookup(extractor, paragraphs)))

    for paragraph in paragraphs:
        assert paragraph.text in html


def test_the_generated_contents_page_is_not_emitted_as_body_paragraphs():
    """Word's contents page is navigation, and it is served as the TOC instead.

    Left in the body, each of its lines becomes a paragraph and then a phantom
    "section" anchored to a page number rather than to a heading. A review then
    reports every one of them as deleted the moment the page is regenerated,
    burying the change the author actually made.
    """
    extractor = DocxExtractor()
    contents = [
        _paragraph("1\tRelease Kit Summary\t10", style="toc 1"),
        _paragraph("1.1\tRelease Kit Details\t10", style="toc 2"),
    ]
    body = [
        _numbered_heading("Release Kit Summary", "heading 1"),
        _paragraph("Real body copy."),
    ]
    paragraphs = contents + body
    blocks = [BodyBlock(kind="paragraph", paragraph=p) for p in paragraphs]

    html = ir_to_html(extractor._build_ir(blocks, _heading_lookup(extractor, paragraphs)))

    assert "Release Kit Details" not in html, "a contents line must not become content"
    assert "PAGEREF" not in html
    assert "<h1" in html and "Release Kit Summary" in html, "the heading itself must survive"
    assert "Real body copy." in html
