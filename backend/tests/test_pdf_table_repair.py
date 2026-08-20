"""Tests for recovering tables that PyMuPDF's detector returns malformed.

The fixtures reproduce the shape observed on page 19 of the Intel GCC SPS Delta
user guide: a 22x4 table whose header row collapsed into a single cell holding a
linear dump of the whole table, leaving a phantom empty first column behind.
"""

from __future__ import annotations

from app.conversion.pdf_to_docx import (
    _drop_empty_columns,
    _has_collapsed_row,
    _repair_collapsed_rows,
)

_BODY = [
    ["", "1", "14014485970", 'There is no visual change when click"Brighten Video" under IGCC'],
    ["", "2", "14014486124", "The preview video wouldn't change when apply different settings."],
    [
        "",
        "3",
        "14014547428",
        '"Something went wrong..." pops up when click random items after idle.',
    ],
    ["", "4", "14014625713", '"Hot:key StopRecording action fialed" pops up while recording'],
]


_HEADER = ["", "Sr. No.", "Internal Sighting Number", "Title"]


def _collapsed_table() -> list[list[str]]:
    """Row 1 collapses the whole table into one cell; the real header follows in row 2."""
    blob = "Sr. No. Internal Sighting Number Title " + " ".join(
        f"{row[1]} {row[2]} {row[3]}" for row in _BODY
    )
    return [[blob, "", "", ""], _HEADER[:], *[row[:] for row in _BODY]]


def test_collapsed_header_row_is_detected():
    assert _has_collapsed_row(_collapsed_table()) is True


def test_intact_table_is_left_alone():
    intact = [["Sr. No.", "Sighting", "Title"], *[row[1:] for row in _BODY]]
    warnings: list[str] = []

    assert _has_collapsed_row(intact) is False
    assert _repair_collapsed_rows(intact, 0, warnings) == intact
    assert _drop_empty_columns(intact) == intact
    assert warnings == []


def test_short_title_row_is_not_mistaken_for_a_collapse():
    titled = [
        ["Key Known Issues", "", ""],
        ["Sr. No.", "Sighting", "Title"],
        *[r[1:] for r in _BODY],
    ]
    warnings: list[str] = []

    assert _repair_collapsed_rows(titled, 0, warnings) == titled
    assert warnings == []


def test_collapsed_row_is_dropped_and_phantom_column_removed():
    warnings: list[str] = []

    repaired = _drop_empty_columns(_repair_collapsed_rows(_collapsed_table(), 18, warnings))

    assert len(repaired) == len(_BODY) + 1
    assert all(len(row) == 3 for row in repaired)
    assert repaired[0] == ["Sr. No.", "Internal Sighting Number", "Title"]
    assert repaired[1] == ["1", "14014485970", _BODY[0][3]]
    assert any("Page 19" in warning for warning in warnings)


def test_every_sighting_number_keeps_its_own_cell():
    repaired = _drop_empty_columns(_repair_collapsed_rows(_collapsed_table(), 18, []))
    numbers = [row[2] for row in _BODY]

    for cell in (cell for row in repaired for cell in row):
        assert sum(number in cell for number in numbers) <= 1, f"cells merged in: {cell!r}"

    assert [row[1] for row in repaired[1:]] == numbers


def test_unique_text_is_never_dropped():
    """A collapsed row carrying text found nowhere else must survive verbatim."""
    rows = _collapsed_table()
    rows[0][0] = "Confidential draft footnote appearing nowhere else " * 8
    warnings: list[str] = []

    repaired = _repair_collapsed_rows(rows, 18, warnings)

    assert repaired == rows
    assert warnings == []
