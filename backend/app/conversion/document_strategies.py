"""Document conversion strategy objects."""

from __future__ import annotations

from typing import Any, Protocol

from app.conversion.models import DocumentConversionRequest


class DocumentConverterStrategy(Protocol):
    """Shared interface for document-to-HTML conversion strategies."""

    name: str

    def supports(self, request: DocumentConversionRequest) -> bool:
        """Return whether the strategy handles this conversion request."""

    def convert_to_html(self, request: DocumentConversionRequest) -> str | None:
        """Convert the request payload to HTML, or return None if unsupported."""


class PdfConverterStrategy:
    """PDF conversion strategy with reader artifact helpers."""

    name = "pdf"

    @staticmethod
    def _legacy_module():
        from app.utils import document_converter

        return document_converter

    def supports(self, request: DocumentConversionRequest) -> bool:
        return request.normalized_mime_type == "application/pdf" or request.extension == ".pdf"

    def convert_to_html(self, request: DocumentConversionRequest) -> str | None:
        return self._legacy_module().convert_pdf_to_html(request.content)

    def convert_pdf_to_reader_artifact(self, content: bytes) -> dict[str, Any]:
        return self._legacy_module().convert_pdf_to_reader_artifact(content)

    def extract_pdf_toc(self, content: bytes) -> dict[str, Any]:
        return self._legacy_module().extract_pdf_toc(content)


class WordConverterStrategy:
    """Word document conversion strategy."""

    name = "word"
    _word_mime_types = {
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    _word_extensions = {".doc", ".docx"}

    @staticmethod
    def _legacy_module():
        from app.utils import document_converter

        return document_converter

    def supports(self, request: DocumentConversionRequest) -> bool:
        return (
            request.normalized_mime_type in self._word_mime_types
            or request.extension in self._word_extensions
        )

    def convert_to_html(self, request: DocumentConversionRequest) -> str | None:
        return self._legacy_module().convert_word_to_html(request.content)

    def convert_word_to_html(self, content: bytes) -> str | None:
        return self._legacy_module().convert_word_to_html(content)


class TextConverterStrategy:
    """Plain-text and text-like conversion strategy."""

    name = "text"
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


class HtmlPassthroughStrategy:
    """HTML passthrough strategy that decodes bytes as HTML text."""

    name = "html"
    _html_mime_types = {"text/html", "application/xhtml+xml"}
    _html_extensions = {".html", ".htm"}

    def supports(self, request: DocumentConversionRequest) -> bool:
        return (
            request.normalized_mime_type in self._html_mime_types
            or request.extension in self._html_extensions
        )

    def convert_to_html(self, request: DocumentConversionRequest) -> str | None:
        try:
            return request.content.decode("utf-8")
        except UnicodeDecodeError:
            return request.content.decode("utf-8", errors="replace")
