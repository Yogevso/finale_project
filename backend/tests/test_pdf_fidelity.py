"""Tests for the PDF fidelity (page-layout) HTML converter.

``_make_structured_pdf`` reproduces the shape of the Intel GCC user guide that
matters here: a running header repeated on every page, and a section heading
whose number sits far to the left of its title, named by the PDF's own outline.
"""

from __future__ import annotations

import re

import fitz
import pytest

from app.conversion.pdf_fidelity import (
    _fallback_stack,
    build_fidelity_reader_artifact,
    convert_pdf_to_fidelity_html,
)


def _make_pdf(pages: int = 2, text: str = "Hello Fidelity") -> bytes:
    doc = fitz.open()
    for index in range(pages):
        page = doc.new_page()
        page.insert_text((72, 96), f"{text} {index + 1}", fontsize=18)
    data = doc.tobytes()
    doc.close()
    return data


def _make_structured_pdf(pages: int = 6) -> bytes:
    """A document with page chrome, body copy and one numbered section heading."""
    doc = fitz.open()
    for index in range(pages):
        page = doc.new_page()
        # Repeated at the same place on every page: this is the running header.
        page.insert_text((72, 60), "Intel GCC User Guide", fontsize=8)
        if index == 1:
            # The number and the title are separate spans on one baseline, as
            # Word and Acrobat both emit them.
            page.insert_text((76, 200), "2", fontsize=22)
            page.insert_text((141, 200), "Key Known Issues", fontsize=22)
        for row in range(12):
            page.insert_text((72, 260 + row * 14), f"Body copy line {row}", fontsize=9)
    doc.set_toc([[1, "Key Known Issues", 2]])
    data = doc.tobytes()
    doc.close()
    return data


def _rendered_node_ids(rendered_html: str) -> set[str]:
    return set(re.findall(r'data-node-id="([^"]+)"', rendered_html))


class TestConvertPdfToFidelityHtml:
    def test_renders_one_container_per_page(self):
        result = convert_pdf_to_fidelity_html(_make_pdf(pages=3))

        assert result.error is None
        assert result.page_count == 3
        assert result.html.count('class="pdf-fidelity-page"') == 3

    def test_keeps_text_as_real_selectable_nodes(self):
        result = convert_pdf_to_fidelity_html(_make_pdf(pages=1, text="Searchable"))

        assert "Searchable" in result.html
        assert '<div class="pdf-fidelity-text">' in result.html

    def test_strips_text_from_the_background_svg(self):
        # Text must live in the HTML layer only, otherwise it renders twice.
        result = convert_pdf_to_fidelity_html(_make_pdf(pages=1))

        assert "<svg" in result.html
        assert "<text" not in result.html

    def test_escapes_markup_in_page_text(self):
        result = convert_pdf_to_fidelity_html(_make_pdf(pages=1, text="<script>x</script>"))

        assert "<script>" not in result.html
        assert "&lt;script&gt;" in result.html

    def test_reports_a_stable_error_for_invalid_input(self):
        result = convert_pdf_to_fidelity_html(b"this is not a pdf")

        assert result.error is not None
        assert result.html == ""


class TestFallbackStack:
    @pytest.mark.parametrize(
        ("base_font", "expected"),
        [
            ("HWEBFC+Verdana-Bold", "Verdana"),
            ("ORIAAM+IntelClear-Light", "IntelClear"),
            ("Arial", "Arial"),
        ],
    )
    def test_drops_subset_tag_and_style_suffix(self, base_font, expected):
        assert _fallback_stack(base_font).startswith(f"'{expected}'")

    def test_preserves_serif_and_monospace_intent(self):
        assert "serif" in _fallback_stack("Times-Roman")
        assert "monospace" in _fallback_stack("CourierNewPSMT")
        assert "sans-serif" in _fallback_stack("Verdana")


class TestBuildFidelityReaderArtifact:
    def test_shapes_the_payload_like_other_reader_artifacts(self):
        artifact = build_fidelity_reader_artifact(_make_pdf(pages=2))

        assert artifact["status"] == "ready"
        assert artifact["error"] is None
        assert artifact["toc_source"] == "pdf_outline"
        assert artifact["payload"]["mode"] == "fidelity"
        assert artifact["payload"]["page_count"] == 2
        assert set(artifact) == {
            "status",
            "html_content",
            "toc_items",
            "toc_source",
            "payload",
            "error",
        }

    def test_reports_failure_without_raising(self):
        artifact = build_fidelity_reader_artifact(b"not a pdf")

        assert artifact["status"] == "failed"
        assert artifact["error"]
        assert artifact["html_content"] == ""

    def test_uses_the_pdf_outline_for_the_table_of_contents(self):
        doc = fitz.open()
        for _ in range(2):
            doc.new_page()
        doc.set_toc([[1, "Chapter One", 1], [2, "Section 1.1", 2]])
        data = doc.tobytes()
        doc.close()

        artifact = build_fidelity_reader_artifact(data)

        titles = [item["title"] for item in artifact["toc_items"]]
        assert titles == ["Chapter One", "Section 1.1"]
        assert artifact["toc_items"][1]["level"] == 2
        assert artifact["toc_items"][1]["page"] == 2


class TestNodeIdentity:
    """The render and the document model address the same nodes by the same ids."""

    def test_every_rendered_line_carries_a_node_id(self):
        result = convert_pdf_to_fidelity_html(_make_structured_pdf())

        assert result.error is None
        # 6 pages: one running header and twelve body lines each, plus the heading.
        assert len(_rendered_node_ids(result.html)) == 6 * 13 + 1

    def test_marks_a_detected_heading_with_its_level(self):
        result = convert_pdf_to_fidelity_html(_make_structured_pdf())

        assert 'data-node-type="heading" data-node-level="1"' in result.html

    def test_marks_the_running_header_as_page_chrome(self):
        """The header is drawn, but named, so a reader can tell it from content."""
        result = convert_pdf_to_fidelity_html(_make_structured_pdf())

        assert result.html.count('data-node-type="running-header"') == 6

    def test_keeps_a_heading_number_on_the_page(self):
        """The model lifts "2" out of the title; the page still has to show it."""
        result = convert_pdf_to_fidelity_html(_make_structured_pdf())

        heading = re.search(
            r'<div class="pdf-fidelity-node" data-node-id="[^"]+" data-node-type="heading".*?</div>',
            result.html,
            re.S,
        )
        assert heading is not None
        assert ">2</span>" in heading.group(0)
        assert ">Key Known Issues</span>" in heading.group(0)

    def test_escapes_markup_in_a_node_id(self):
        result = convert_pdf_to_fidelity_html(_make_structured_pdf())

        assert all('"' not in node_id and "<" not in node_id for node_id in _rendered_node_ids(result.html))


class TestFidelityTableOfContents:
    def test_anchors_point_at_nodes_that_exist_in_the_render(self):
        """Navigation is a lookup, so every anchor must name a rendered node."""
        artifact = build_fidelity_reader_artifact(_make_structured_pdf())
        rendered = _rendered_node_ids(artifact["html_content"])

        anchors = [item["anchor_id"] for item in artifact["toc_items"]]
        assert anchors == ["n2-1"]
        assert set(anchors) <= rendered

    def test_falls_back_to_the_outline_where_no_heading_is_detected(self):
        """A bookmark still earns an entry; it just has nothing to anchor to."""
        doc = fitz.open()
        for _ in range(2):
            doc.new_page()
        doc.set_toc([[1, "Chapter One", 1]])
        data = doc.tobytes()
        doc.close()

        artifact = build_fidelity_reader_artifact(data)

        assert artifact["toc_items"][0]["title"] == "Chapter One"
        assert artifact["toc_items"][0]["anchor_id"] is None
