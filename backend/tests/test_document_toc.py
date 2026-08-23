"""Tests for building one table of contents from declared structure.

The regression these guard is concrete: page numbers used to be derived from
heading order, so on the Intel release notes 156 of 158 entries claimed a page
the document never had, running to "page 158" in a 109-page document.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.conversion.document_toc import (
    build_toc_from_docx_structure,
    build_toc_from_layout,
)


@dataclass
class _Entry:
    level: int
    title: str
    number: str | None = None
    page: int | None = None
    node_id: str | None = None


@dataclass
class _Structure:
    toc: list[_Entry]


@dataclass
class _Outline:
    level: int
    title: str
    page: int


@dataclass
class _Heading:
    id: str
    text: str
    page: int
    level: int = 1
    number: str | None = None


@dataclass
class _Layout:
    outline: list[_Outline]
    headings: list[_Heading]


def test_docx_entries_keep_the_page_the_document_declares():
    structure = _Structure(
        [
            _Entry(1, "Release Kit Summary", "1", 10, "heading-release-kit-summary"),
            _Entry(2, "Release Kit Details", "1.1", 10, "heading-release-kit-details"),
            _Entry(1, "General Information", "2", 11, "heading-general-information"),
        ]
    )

    items = build_toc_from_docx_structure(structure)

    assert [item["page"] for item in items] == [10, 10, 11]
    assert [item["page_start"] for item in items] == [10, 10, 11]


def test_docx_entries_show_their_numbering_and_point_at_a_node():
    structure = _Structure([_Entry(2, "Release Kit Details", "1.1", 10, "heading-x")])

    item = build_toc_from_docx_structure(structure)[0]

    assert item["title"] == "1.1 Release Kit Details"
    assert item["anchor_id"] == "heading-x"
    assert item["level"] == 2


def test_an_entry_without_a_declared_page_falls_back_to_its_position():
    structure = _Structure([_Entry(1, "Appendix", None, None, "heading-appendix")])

    assert build_toc_from_docx_structure(structure)[0]["page"] == 1


def test_untitled_entries_are_dropped_without_shifting_ids():
    structure = _Structure(
        [_Entry(1, "", None, 3, None), _Entry(1, "Real Section", None, 4, "heading-real")]
    )

    items = build_toc_from_docx_structure(structure)

    assert len(items) == 1
    assert items[0]["id"] == "toc-0"


def test_pdf_outline_leads_and_detected_headings_fill_the_gaps():
    """The GCC guide ships four shallow bookmarks; detection covers the rest."""
    layout = _Layout(
        outline=[_Outline(1, "Revision History", 4), _Outline(1, "2 Key Known Issues", 19)],
        headings=[
            _Heading("n4-0", "Revision History", 4),
            _Heading("n3-0", "Contents", 3, level=2),
            _Heading("n19-1", "Key Known Issues", 19, number="2"),
        ],
    )

    items = build_toc_from_layout(layout)

    assert [item["page"] for item in items] == [3, 4, 19], "entries must run in page order"
    assert [item["id"] for item in items] == ["toc-0", "toc-1", "toc-2"]


def test_an_outline_entry_is_bound_to_the_heading_it_names():
    layout = _Layout(
        outline=[_Outline(1, "2 Key Known Issues", 19)],
        headings=[_Heading("n19-1", "Key Known Issues", 19, number="2")],
    )

    assert build_toc_from_layout(layout)[0]["anchor_id"] == "n19-1"


def test_a_page_the_outline_already_claims_is_not_listed_twice():
    layout = _Layout(
        outline=[_Outline(1, "Revision History", 4)],
        headings=[_Heading("n4-0", "Revision History", 4)],
    )

    assert len(build_toc_from_layout(layout)) == 1
