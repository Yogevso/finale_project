"""Tests for the structure DOCX declares about itself.

The fixtures follow the Intel release-notes template: a generated contents page
whose lines carry "number TAB title TAB page", headings that do not contain their
own numbers because Word renders those from the numbering definition, and titles
that repeat verbatim under several chapters.
"""

from __future__ import annotations

from app.conversion.docx_structure import (
    DocumentStructure,
    StructureNode,
    TocEntry,
    _link_toc_to_nodes,
    normalize_title,
    parse_toc_line,
)


def test_parse_toc_line_splits_number_title_and_page():
    assert parse_toc_line("1\tRelease Kit Summary\t10") == ("1", "Release Kit Summary", 10)
    assert parse_toc_line("1.1\tRelease Kit Details\t10") == ("1.1", "Release Kit Details", 10)


def test_parse_toc_line_accepts_dotted_leaders():
    """A hand-edited contents page uses leader dots where Word uses tabs."""
    assert parse_toc_line("2.3 Supported OS.........11") == ("2.3", "Supported OS", 11)


def test_parse_toc_line_survives_a_missing_number_or_page():
    assert parse_toc_line("Revision History\t4") == (None, "Revision History", 4)
    assert parse_toc_line("Appendix") == (None, "Appendix", None)


def test_normalize_title_ignores_numbering_and_punctuation():
    assert normalize_title("2.1\tImportant Notes") == normalize_title("Important Notes")
    assert normalize_title("Intel® Silicon — Firmware") == "intel silicon firmware"


def _structure(headings: list[tuple[str, int]], toc: list[tuple[str, int, str]]):
    structure = DocumentStructure()
    structure.nodes = [
        StructureNode(
            id=f"heading-{text.lower().replace(' ', '-')}"
            + ("" if index == 0 else f"-{index + 1}"),
            type="heading",
            level=level,
            text=text,
            style=f"heading {level}",
            index=position,
        )
        for position, (text, level, index) in enumerate(
            (text, level, [t for t, _ in headings[:position]].count(text))
            for position, (text, level) in enumerate(headings)
        )
    ]
    structure.toc = [
        TocEntry(level=level, title=title, number=number) for title, level, number in toc
    ]
    return structure


def test_headings_recover_the_number_that_only_the_contents_page_holds():
    structure = _structure(
        headings=[("Release Kit Summary", 1), ("Release Kit Details", 2)],
        toc=[("Release Kit Summary", 1, "1"), ("Release Kit Details", 2, "1.1")],
    )

    _link_toc_to_nodes(structure)

    assert [node.number for node in structure.headings] == ["1", "1.1"]
    assert all(entry.node_id for entry in structure.toc)


def test_repeated_titles_bind_to_successive_headings():
    """Intel templates reuse titles under several chapters; each needs its own id."""
    structure = _structure(
        headings=[("Important Notes", 2), ("Important Notes", 2)],
        toc=[("Important Notes", 2, "2.1"), ("Important Notes", 2, "3.1")],
    )

    _link_toc_to_nodes(structure)

    targets = [entry.node_id for entry in structure.toc]
    assert len(set(targets)) == 2, f"contents entries collapsed onto one heading: {targets}"


def test_an_entry_without_a_matching_heading_is_left_unlinked():
    structure = _structure(
        headings=[("Release Kit Summary", 1)],
        toc=[("Release Kit Summary", 1, "1"), ("Missing Section", 1, "2")],
    )

    _link_toc_to_nodes(structure)

    assert structure.toc[0].node_id is not None
    assert structure.toc[1].node_id is None
