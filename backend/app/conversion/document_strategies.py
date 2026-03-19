"""Document conversion strategy objects."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

from app.conversion.docx_extractor import DocxExtractor
from app.conversion.docx_extractor import ExtractionResult as DocxExtractionResult
from app.conversion.models import DocumentConversionRequest
from app.conversion.pptx_extractor import (
    ExtractionResult as PptxExtractionResult,
)
from app.conversion.pptx_extractor import (
    PptxExtractor,
)
from app.conversion.reader_artifact import build_reader_artifact_from_extraction_result


class DocumentConversionOutput(str, Enum):
    """Named outputs that a conversion strategy may provide."""

    HTML = "html"
    READER_ARTIFACT = "reader_artifact"


@dataclass(frozen=True)
class StrategyCapabilityDescriptor:
    """Explicit output support metadata for a converter strategy."""

    outputs: frozenset[DocumentConversionOutput]

    def supports(self, output: DocumentConversionOutput) -> bool:
        return output in self.outputs

    def as_names(self) -> tuple[str, ...]:
        return tuple(sorted(output.value for output in self.outputs))


class DocumentConverterStrategy(Protocol):
    """Shared interface for document-to-HTML conversion strategies."""

    name: str
    capabilities: StrategyCapabilityDescriptor

    def supports(self, request: DocumentConversionRequest) -> bool:
        """Return whether the strategy handles this conversion request."""

    def convert_to_html(self, request: DocumentConversionRequest) -> str | None:
        """Convert the request payload to HTML, or return None if unsupported."""

    def convert_to_reader_artifact(self, request: DocumentConversionRequest) -> dict[str, Any] | None:
        """Convert the request payload into a reader-artifact payload when supported."""


_HTML_ONLY_CAPABILITIES = StrategyCapabilityDescriptor(
    outputs=frozenset({DocumentConversionOutput.HTML})
)
_HTML_AND_READER_CAPABILITIES = StrategyCapabilityDescriptor(
    outputs=frozenset(
        {
            DocumentConversionOutput.HTML,
            DocumentConversionOutput.READER_ARTIFACT,
        }
    )
)


class WordConverterStrategy:
    """Word document conversion strategy."""

    name = "word"
    capabilities = _HTML_AND_READER_CAPABILITIES
    _word_mime_types = {
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    _word_extensions = {".doc", ".docx"}
    _docx_mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    @staticmethod
    def _legacy_module():
        from app.utils import document_converter

        return document_converter

    def __init__(self, *, extractor: DocxExtractor | None = None) -> None:
        self._extractor = extractor or DocxExtractor()

    def supports(self, request: DocumentConversionRequest) -> bool:
        return (
            request.normalized_mime_type in self._word_mime_types
            or request.extension in self._word_extensions
        )

    def convert_to_html(self, request: DocumentConversionRequest) -> str | None:
        if request.normalized_mime_type == self._docx_mime_type or request.extension == ".docx":
            return self._extract_ready_html(self._extractor.extract_bytes(request.content))
        return self._legacy_module().convert_word_to_html(request.content)

    def convert_word_to_html(self, content: bytes) -> str | None:
        extracted_html = self._extract_ready_html(self._extractor.extract_bytes(content))
        if extracted_html:
            return extracted_html
        return self._legacy_module().convert_word_to_html(content)

    def convert_to_reader_artifact(self, request: DocumentConversionRequest) -> dict[str, Any] | None:
        if request.normalized_mime_type != self._docx_mime_type and request.extension != ".docx":
            return None
        return build_reader_artifact_from_extraction_result(
            self._extractor.extract_bytes(request.content)
        )

    @staticmethod
    def _extract_ready_html(result: DocxExtractionResult) -> str | None:
        if result.status != "ready":
            return None
        return result.html or None


class PowerPointConverterStrategy:
    """PowerPoint presentation conversion strategy."""

    name = "powerpoint"
    capabilities = _HTML_AND_READER_CAPABILITIES
    _powerpoint_mime_types = {
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
    _powerpoint_extensions = {".pptx"}

    def __init__(self, *, extractor: PptxExtractor | None = None) -> None:
        self._extractor = extractor or PptxExtractor()

    def supports(self, request: DocumentConversionRequest) -> bool:
        return (
            request.normalized_mime_type in self._powerpoint_mime_types
            or request.extension in self._powerpoint_extensions
        )

    def convert_to_html(self, request: DocumentConversionRequest) -> str | None:
        return self._extract_ready_html(self._extractor.extract_bytes(request.content))

    def convert_to_reader_artifact(self, request: DocumentConversionRequest) -> dict[str, Any] | None:
        return build_reader_artifact_from_extraction_result(
            self._extractor.extract_bytes(request.content)
        )

    @staticmethod
    def _extract_ready_html(result: PptxExtractionResult) -> str | None:
        if result.status != "ready":
            return None
        return result.html or None


class TextConverterStrategy:
    """Plain-text and text-like conversion strategy."""

    name = "text"
    capabilities = _HTML_ONLY_CAPABILITIES
    _text_mime_types = {
        "text/markdown",
        "text/x-markdown",
        "application/json",
        "application/rtf",
    }
    _text_extensions = {".txt", ".md", ".json", ".rtf", ".csv"}

    @staticmethod
    def _legacy_module():
        from app.utils import document_converter

        return document_converter

    def supports(self, request: DocumentConversionRequest) -> bool:
        return (
            request.normalized_mime_type.startswith("text/")
            or request.normalized_mime_type in self._text_mime_types
            or request.extension in self._text_extensions
        )

    def convert_to_html(self, request: DocumentConversionRequest) -> str | None:
        return self._legacy_module().convert_text_to_html(request.content)

    def convert_to_reader_artifact(self, request: DocumentConversionRequest) -> dict[str, Any] | None:
        return None


class HtmlPassthroughStrategy:
    """HTML passthrough strategy that decodes bytes as HTML text.

    AF-012: Content is sanitized via ``strip_dangerous_html_patterns``
    before being returned, so backend never serves raw unsanitized HTML.
    """

    name = "html"
    capabilities = _HTML_ONLY_CAPABILITIES
    _html_mime_types = {"text/html", "application/xhtml+xml"}
    _html_extensions = {".html", ".htm"}

    def supports(self, request: DocumentConversionRequest) -> bool:
        return (
            request.normalized_mime_type in self._html_mime_types
            or request.extension in self._html_extensions
        )

    def convert_to_html(self, request: DocumentConversionRequest) -> str | None:
        from app.utils.sanitization import strip_dangerous_html_patterns

        try:
            raw = request.content.decode("utf-8")
        except UnicodeDecodeError:
            raw = request.content.decode("utf-8", errors="replace")
        return strip_dangerous_html_patterns(raw)

    def convert_to_reader_artifact(self, request: DocumentConversionRequest) -> dict[str, Any] | None:
        return None
