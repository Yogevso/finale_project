"""Tests for the PDF fidelity (page-layout) HTML converter."""

from __future__ import annotations

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

        assert artifact["status"] == "completed"
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
