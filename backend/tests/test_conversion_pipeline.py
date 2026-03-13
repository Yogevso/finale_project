"""Tests for conversion strategy pipelines."""

from __future__ import annotations

from types import SimpleNamespace

from app.conversion import (
    DocumentConversionOutput,
    DocumentConversionPipeline,
    StrategyCapabilityDescriptor,
)
from app.conversion.ir import IRNode


def test_document_conversion_pipeline_selects_legacy_word_strategy_for_doc(monkeypatch):
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


def test_document_conversion_pipeline_selects_docx_extractor(monkeypatch):
    monkeypatch.setattr(
        "app.conversion.document_strategies.DocxExtractor.extract_bytes",
        lambda _self, _content: SimpleNamespace(status="ready", html="<article>docx-html</article>"),
    )
    pipeline = DocumentConversionPipeline()

    output = pipeline.convert_document_to_html(
        b"docx-bytes",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "sample.docx",
    )

    assert output == "<article>docx-html</article>"


def test_document_conversion_pipeline_selects_pptx_extractor(monkeypatch):
    monkeypatch.setattr(
        "app.conversion.document_strategies.PptxExtractor.extract_bytes",
        lambda _self, _content: SimpleNamespace(
            status="ready",
            html='<div class="pptx-presentation"></div>',
        ),
    )
    pipeline = DocumentConversionPipeline()

    output = pipeline.convert_document_to_html(
        b"pptx-bytes",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "deck.pptx",
    )

    assert output == '<div class="pptx-presentation"></div>'


def test_document_conversion_pipeline_builds_docx_reader_artifact(monkeypatch):
    monkeypatch.setattr(
        "app.conversion.document_strategies.DocxExtractor.extract_bytes",
        lambda _self, _content: SimpleNamespace(
            status="ready",
            html="<article>docx-html</article>",
            title="Wave Y",
            headings=[
                SimpleNamespace(id="heading-wave-y", level=1, text="Wave Y", slide_number=None)
            ],
            metadata={"title": "Wave Y"},
            warnings=[SimpleNamespace(code="MISSING_IMAGES", message="1 images failed", count=1)],
            confidence=0.9,
            extraction_error=None,
            ir=IRNode(
                type="document",
                children=[
                    IRNode(type="heading", attributes={"level": 1, "id": "heading-wave-y"}),
                    IRNode(type="paragraph"),
                ],
            ),
        ),
    )
    pipeline = DocumentConversionPipeline()

    artifact = pipeline.convert_document_to_reader_artifact(
        b"docx-bytes",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "sample.docx",
    )

    assert artifact is not None
    assert artifact["html_content"] == "<article>docx-html</article>"
    assert artifact["toc_source"] == "headings"
    assert artifact["payload"]["confidence"] == 0.9
    assert artifact["payload"]["element_counts"]["heading"] == 1
    assert artifact["payload"]["warnings"][0]["code"] == "MISSING_IMAGES"
    assert artifact["payload"]["toc_items"][0]["anchor_id"] == "heading-wave-y"


def test_document_conversion_pipeline_builds_pptx_reader_artifact(monkeypatch):
    monkeypatch.setattr(
        "app.conversion.document_strategies.PptxExtractor.extract_bytes",
        lambda _self, _content: SimpleNamespace(
            status="ready",
            html='<div class="pptx-presentation"></div>',
            title="Deck",
            headings=[SimpleNamespace(id="slide-3-title", level=2, text="Roadmap", slide_number=3)],
            slides=[
                SimpleNamespace(
                    number=3,
                    archive_path="ppt/slides/slide3.xml",
                    title="Roadmap",
                    has_notes=True,
                    has_images=False,
                )
            ],
            metadata={"slideCount": 1},
            warnings=[],
            confidence=1.0,
            extraction_error=None,
            ir=IRNode(type="document", children=[IRNode(type="slide")]),
        ),
    )
    pipeline = DocumentConversionPipeline()

    artifact = pipeline.convert_document_to_reader_artifact(
        b"pptx-bytes",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "deck.pptx",
    )

    assert artifact is not None
    assert artifact["payload"]["slides"][0]["number"] == 3
    assert artifact["payload"]["toc_items"][0]["page"] == 3
    assert artifact["payload"]["element_counts"]["slide"] == 1


def test_document_conversion_pipeline_html_passthrough():
    pipeline = DocumentConversionPipeline()

    output = pipeline.convert_document_to_html(
        b"<h1>Hello</h1>",
        "text/html",
        "page.html",
    )

    assert output == "<h1>Hello</h1>"


def test_document_conversion_pipeline_describes_registered_strategy_capabilities():
    pipeline = DocumentConversionPipeline()

    assert pipeline.describe_strategy_capabilities() == {
        "word": ("html", "reader_artifact"),
        "powerpoint": ("html", "reader_artifact"),
        "html": ("html",),
        "text": ("html",),
    }


def test_document_conversion_pipeline_returns_none_when_strategy_has_no_reader_output(caplog):
    pipeline = DocumentConversionPipeline()

    with caplog.at_level("INFO"):
        artifact = pipeline.convert_document_to_reader_artifact(
            b"plain text",
            "text/plain",
            "notes.txt",
        )

    assert artifact is None
    assert "does not support reader artifacts" in caplog.text


def test_strategy_capability_descriptor_sorts_output_names():
    descriptor = StrategyCapabilityDescriptor(
        outputs=frozenset(
            {
                DocumentConversionOutput.READER_ARTIFACT,
                DocumentConversionOutput.HTML,
            }
        )
    )

    assert descriptor.as_names() == ("html", "reader_artifact")
    assert descriptor.supports(DocumentConversionOutput.HTML) is True
