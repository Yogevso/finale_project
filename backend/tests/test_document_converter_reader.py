"""Unit tests for Reader HTML structure extraction helpers."""

from app.utils import document_converter as converter


class _FakePage:
    def find_tables(self):
        raise RuntimeError("no table detector in test")


class _FakeTextPage:
    def __init__(self, payload: dict):
        self._payload = payload

    def get_text(self, mode: str):
        if mode != "dict":
            raise ValueError("Unsupported mode")
        return self._payload


class _FakeDoc:
    def __init__(self, pages: list[_FakeTextPage]):
        self._pages = pages

    def __getitem__(self, index: int):
        return self._pages[index]


def test_render_pdf_page_html_renders_ordered_list_block():
    visual_blocks = [
        {
            "text": "1. Install package 2. Configure environment 3. Run validation",
            "line_texts": [
                "1. Install package",
                "2. Configure environment",
                "3. Run validation",
            ],
            "line_items": [],
            "max_size": 11.0,
            "avg_size": 11.0,
            "bold_ratio": 0.0,
            "monospace_ratio": 0.0,
            "x0": 10.0,
            "y0": 50.0,
        }
    ]

    page_parts, page_headings = converter._render_pdf_page_html(
        visual_blocks=visual_blocks,
        table_entries=[],
        page_number=2,
        body_font_size=11.0,
    )
    html_output = "\n".join(page_parts)

    assert "<ol data-page='2'>" in html_output
    assert "<li>Install package</li>" in html_output
    assert "<li>Configure environment</li>" in html_output
    assert "<li>Run validation</li>" in html_output
    assert page_headings == []


def test_extract_pdf_tables_uses_pre_fallback_when_detector_fails(monkeypatch):
    fake_lines = [
        {
            "text": "Field  Value  Notes",
            "raw_text": "Field   Value   Notes",
            "is_monospace": True,
            "bbox": (10.0, 100.0, 320.0, 112.0),
            "x0": 10.0,
            "y0": 100.0,
        },
        {
            "text": "Platform  PTL-H",
            "raw_text": "Platform   PTL-H   Intel",
            "is_monospace": True,
            "bbox": (10.0, 114.0, 320.0, 126.0),
            "x0": 10.0,
            "y0": 114.0,
        },
    ]

    monkeypatch.setattr(converter, "_collect_pdf_lines", lambda _page, _bboxes: fake_lines)

    table_entries, table_bboxes = converter._extract_pdf_tables_with_bboxes(
        _FakePage(), page_number=5
    )

    assert len(table_entries) == 1
    assert "pdf-table-fallback" in table_entries[0]["html"]
    assert "<pre>" in table_entries[0]["html"]
    assert "data-page='5'" in table_entries[0]["html"]
    assert len(table_bboxes) == 1


def test_looks_garbled_text_detects_repeated_email_noise():
    noisy_line = (
        "yakir.gurievsky@intel.com 11635294 yakir.gurievsky@intel.com "
        "11635294 yakir.gurievsky@intel.com 11635294"
    )
    assert converter._looks_garbled_text(noisy_line) is True


def test_detect_repeated_watermark_texts_finds_rotated_intel_watermark():
    watermark = "yakir.gurievsky@intel.com 11635294"

    def page_payload(text: str, rotated: bool):
        direction = [0.7, 0.7] if rotated else [1.0, 0.0]
        return {
            "blocks": [
                {
                    "type": 0,
                    "lines": [
                        {
                            "dir": direction,
                            "spans": [{"text": text, "font": "Arial", "size": 10}],
                        }
                    ],
                }
            ]
        }

    doc = _FakeDoc(
        [
            _FakeTextPage(page_payload(watermark, True)),
            _FakeTextPage(page_payload(watermark, True)),
            _FakeTextPage(page_payload("Introduction", False)),
        ]
    )

    repeated = converter._detect_repeated_watermark_texts(doc, page_count=3)

    assert watermark.lower() in repeated
    assert "introduction" not in repeated


def test_collect_pdf_visual_blocks_filters_rotated_repeated_watermark_spans():
    watermark = "yakir.gurievsky@intel.com 11635294"
    page = _FakeTextPage(
        {
            "blocks": [
                {
                    "type": 0,
                    "bbox": [0, 0, 500, 40],
                    "lines": [
                        {
                            "dir": [0.7, 0.7],
                            "bbox": [5, 5, 400, 20],
                            "spans": [
                                {
                                    "text": watermark,
                                    "font": "Arial",
                                    "size": 9,
                                    "flags": 0,
                                    "bbox": [5, 5, 300, 20],
                                }
                            ],
                        }
                    ],
                },
                {
                    "type": 0,
                    "bbox": [0, 100, 500, 140],
                    "lines": [
                        {
                            "dir": [1.0, 0.0],
                            "bbox": [10, 100, 300, 118],
                            "spans": [
                                {
                                    "text": "1 Introduction",
                                    "font": "Arial-Bold",
                                    "size": 15,
                                    "flags": 16,
                                    "bbox": [10, 100, 190, 118],
                                }
                            ],
                        }
                    ],
                },
            ]
        }
    )

    visual_blocks = converter._collect_pdf_visual_blocks(
        page,
        [],
        repeated_watermark_texts={watermark.lower()},
    )

    merged_text = " ".join(block.get("text", "") for block in visual_blocks)
    assert "Introduction" in merged_text
    assert "intel.com" not in merged_text.lower()


def test_collect_pdf_visual_blocks_filters_low_opacity_watermark():
    page = _FakeTextPage(
        {
            "blocks": [
                {
                    "type": 0,
                    "bbox": [0, 0, 500, 40],
                    "lines": [
                        {
                            "dir": [1.0, 0.0],
                            "bbox": [5, 5, 400, 20],
                            "spans": [
                                {
                                    "text": "John Doe 11635294",
                                    "font": "Arial",
                                    "size": 10,
                                    "flags": 0,
                                    "opacity": 0.2,
                                    "bbox": [5, 5, 200, 20],
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    )

    visual_blocks = converter._collect_pdf_visual_blocks(page, [], repeated_watermark_texts=set())
    assert visual_blocks == []
