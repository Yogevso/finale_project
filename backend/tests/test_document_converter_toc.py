"""Unit tests for PDF TOC fallback extraction."""

from app.services.attachment_service import AttachmentService
from app.utils import document_converter as converter


class _FakeDoc:
    def __init__(self, page_count: int):
        self._pages = [object() for _ in range(page_count)]

    def __getitem__(self, index: int):
        return self._pages[index]


def _line(text: str, x0: float = 20.0) -> dict:
    return {"text": text, "x0": x0}


def test_parse_toc_entry_line_supports_dot_leaders():
    parsed = converter._parse_toc_entry_line("Revision History ............ 7")
    assert parsed == ("Revision History", 7)


def test_contents_fallback_extracts_entries_and_maps_pages(monkeypatch):
    doc = _FakeDoc(12)

    line_map = {
        id(doc[0]): [_line("Intel Release Notes")],
        id(doc[1]): [
            _line("TABLE OF CONTENTS"),
            _line("Revision History ............ 3"),
            _line("1 Introduction ............ 5"),
            _line("1.1 Scope"),
            _line("6"),
            _line("2 Platform Configuration ............ 10"),
        ],
    }

    def fake_collect_pdf_lines(page, _table_bboxes):
        return line_map.get(id(page), [])

    monkeypatch.setattr(converter, "_collect_pdf_lines", fake_collect_pdf_lines)

    headings_by_page = {
        4: [
            {
                "title": "Revision History",
                "normalized_title": "revision history",
                "anchor_id": "reader-p4-revision-history-0",
            }
        ],
        6: [
            {
                "title": "1 Introduction",
                "normalized_title": "1 introduction",
                "anchor_id": "reader-p6-1-introduction-0",
            }
        ],
        7: [
            {
                "title": "1.1 Scope",
                "normalized_title": "1.1 scope",
                "anchor_id": "reader-p7-1-1-scope-0",
            }
        ],
        11: [
            {
                "title": "2 Platform Configuration",
                "normalized_title": "2 platform configuration",
                "anchor_id": "reader-p11-2-platform-configuration-0",
            }
        ],
    }

    items = converter._extract_contents_page_toc(doc, 12, headings_by_page)

    assert len(items) >= 4
    assert [item["title"] for item in items[:4]] == [
        "Revision History",
        "1 Introduction",
        "1.1 Scope",
        "2 Platform Configuration",
    ]
    # Parsed TOC pages are corrected to physical PDF pages using heading-title matches.
    assert [item["page_start"] for item in items[:4]] == [4, 6, 7, 11]
    assert items[0]["anchor_id"] == "reader-p4-revision-history-0"
    assert items[1]["anchor_id"] == "reader-p6-1-introduction-0"


def test_outline_source_normalization_contract():
    assert AttachmentService._normalize_outline_source("outline") == "bookmarks"
    assert AttachmentService._normalize_outline_source("bookmarks") == "bookmarks"
    assert (
        AttachmentService._normalize_outline_source("contents_page")
        == "contents-fallback"
    )
    assert (
        AttachmentService._normalize_outline_source("heuristic")
        == "contents-fallback"
    )
