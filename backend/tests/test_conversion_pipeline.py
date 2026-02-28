"""Tests for conversion strategy pipelines."""

from __future__ import annotations

import pytest

from app.conversion import (
    DocumentConversionPipeline,
    GenericDocumentPreviewPdfStrategy,
    HtmlPreviewPdfStrategy,
    ImagePreviewPdfStrategy,
    OfficePreviewPdfStrategy,
    PreviewPdfConversionPipeline,
    PreviewPdfConversionRequest,
    TextPreviewPdfStrategy,
)


def test_document_conversion_pipeline_selects_word_strategy(monkeypatch):
    monkeypatch.setattr(
        "app.utils.document_converter.convert_word_to_html",
        lambda _content: "<p>word-html</p>",
    )
    pipeline = DocumentConversionPipeline()

    output = pipeline.convert_document_to_html(
        b"doc-bytes",
        "application/msword",
        "sample.doc",
    )

    assert output == "<p>word-html</p>"


def test_document_conversion_pipeline_html_passthrough():
    pipeline = DocumentConversionPipeline()

    output = pipeline.convert_document_to_html(
        b"<h1>Hello</h1>",
        "text/html",
        "page.html",
    )

    assert output == "<h1>Hello</h1>"


def test_preview_pdf_pipeline_uses_first_matching_strategy():
    calls: list[str] = []

    def _image_converter(_content: bytes, _title: str) -> bytes:
        calls.append("image")
        return b"%PDF-image%"

    def _office_converter(_content: bytes, _filename: str, _mime: str) -> bytes:
        calls.append("office")
        return b"%PDF-office%"

    def _html_converter(_html: str, _title: str) -> bytes:
        calls.append("html")
        return b"%PDF-html%"

    def _text_converter(_content: bytes, _title: str) -> bytes:
        calls.append("text")
        return b"%PDF-text%"

    pipeline = PreviewPdfConversionPipeline(
        strategies=[
            ImagePreviewPdfStrategy(convert_image_to_pdf_bytes=_image_converter),
            OfficePreviewPdfStrategy(convert_office_to_pdf_bytes=_office_converter),
            HtmlPreviewPdfStrategy(convert_html_to_pdf_bytes=_html_converter),
            TextPreviewPdfStrategy(convert_text_to_pdf_bytes=_text_converter),
        ]
    )

    output = pipeline.convert(
        PreviewPdfConversionRequest(
            content=b"image-bytes",
            mime_type="image/png",
            filename="preview.png",
        )
    )

    assert output == b"%PDF-image%"
    assert calls == ["image"]


class _StubDocumentPipeline:
    def __init__(self, html_output: str):
        self.html_output = html_output

    def convert_document_to_html(self, _content: bytes, _mime_type: str, _filename: str) -> str:
        return self.html_output


def test_generic_preview_strategy_raises_on_conversion_error_marker():
    strategy = GenericDocumentPreviewPdfStrategy(
        document_pipeline=_StubDocumentPipeline("Word conversion not available."),
        convert_html_to_pdf_bytes=lambda html_content, _title: html_content.encode("utf-8"),
        is_conversion_error_html=lambda html_content: "conversion not available"
        in html_content.lower(),
    )

    with pytest.raises(ValueError, match="Word conversion not available"):
        strategy.convert(
            PreviewPdfConversionRequest(
                content=b"binary",
                mime_type="application/octet-stream",
                filename="unsupported.bin",
            )
        )
