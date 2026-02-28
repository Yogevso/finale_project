"""Preview PDF conversion strategies and coordinator."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol

from app.conversion.document_pipeline import DocumentConversionPipeline
from app.conversion.models import PreviewPdfConversionRequest


class PreviewPdfStrategy(Protocol):
    """Shared interface for non-PDF to preview-PDF conversion strategies."""

    name: str

    def supports(self, request: PreviewPdfConversionRequest) -> bool:
        """Return whether the strategy handles this request."""

    def convert(self, request: PreviewPdfConversionRequest) -> bytes:
        """Convert request payload to PDF bytes."""


class ImagePreviewPdfStrategy:
    """Image-to-PDF conversion strategy."""

    name = "image"

    def __init__(self, convert_image_to_pdf_bytes: Callable[[bytes, str], bytes]) -> None:
        self._convert_image_to_pdf_bytes = convert_image_to_pdf_bytes

    def supports(self, request: PreviewPdfConversionRequest) -> bool:
        return request.normalized_mime_type.startswith("image/")

    def convert(self, request: PreviewPdfConversionRequest) -> bytes:
        return self._convert_image_to_pdf_bytes(request.content, request.filename)


class OfficePreviewPdfStrategy:
    """Office file to PDF strategy."""

    name = "office"
    _office_mime_types = {
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
    _office_extensions = {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}

    def __init__(self, convert_office_to_pdf_bytes: Callable[[bytes, str, str], bytes]) -> None:
        self._convert_office_to_pdf_bytes = convert_office_to_pdf_bytes

    def supports(self, request: PreviewPdfConversionRequest) -> bool:
        return (
            request.normalized_mime_type in self._office_mime_types
            or request.extension in self._office_extensions
        )

    def convert(self, request: PreviewPdfConversionRequest) -> bytes:
        return self._convert_office_to_pdf_bytes(
            request.content,
            request.filename,
            request.normalized_mime_type,
        )


class HtmlPreviewPdfStrategy:
    """HTML source to PDF strategy."""

    name = "html"
    _html_mime_types = {"text/html", "application/xhtml+xml"}
    _html_extensions = {".html", ".htm"}

    def __init__(self, convert_html_to_pdf_bytes: Callable[[str, str], bytes]) -> None:
        self._convert_html_to_pdf_bytes = convert_html_to_pdf_bytes

    def supports(self, request: PreviewPdfConversionRequest) -> bool:
        return (
            request.normalized_mime_type in self._html_mime_types
            or request.extension in self._html_extensions
        )

    def convert(self, request: PreviewPdfConversionRequest) -> bytes:
        html_content = request.content.decode("utf-8", errors="replace")
        if not html_content.strip():
            raise ValueError("HTML conversion produced empty output")
        return self._convert_html_to_pdf_bytes(html_content, request.filename)


class TextPreviewPdfStrategy:
    """Text source to PDF strategy."""

    name = "text"
    _text_mime_types = {
        "text/plain",
        "text/markdown",
        "text/csv",
        "application/json",
    }
    _text_extensions = {".txt", ".md", ".csv", ".json"}

    def __init__(self, convert_text_to_pdf_bytes: Callable[[bytes, str], bytes]) -> None:
        self._convert_text_to_pdf_bytes = convert_text_to_pdf_bytes

    def supports(self, request: PreviewPdfConversionRequest) -> bool:
        return (
            request.normalized_mime_type in self._text_mime_types
            or request.extension in self._text_extensions
        )

    def convert(self, request: PreviewPdfConversionRequest) -> bytes:
        return self._convert_text_to_pdf_bytes(request.content, request.filename)


class GenericDocumentPreviewPdfStrategy:
    """Fallback strategy using document-to-HTML conversion pipeline."""

    name = "generic-document"

    def __init__(
        self,
        *,
        document_pipeline: DocumentConversionPipeline,
        convert_html_to_pdf_bytes: Callable[[str, str], bytes],
        is_conversion_error_html: Callable[[str], bool],
    ) -> None:
        self._document_pipeline = document_pipeline
        self._convert_html_to_pdf_bytes = convert_html_to_pdf_bytes
        self._is_conversion_error_html = is_conversion_error_html

    def supports(self, request: PreviewPdfConversionRequest) -> bool:
        _ = request
        return True

    def convert(self, request: PreviewPdfConversionRequest) -> bytes:
        html_content = self._document_pipeline.convert_document_to_html(
            request.content,
            request.normalized_mime_type,
            request.filename,
        )
        normalized_html = (html_content or "").strip()
        if not normalized_html:
            raise ValueError("Content conversion produced empty output")
        if self._is_conversion_error_html(normalized_html):
            raise ValueError(normalized_html)
        return self._convert_html_to_pdf_bytes(normalized_html, request.filename)


class PreviewPdfConversionPipeline:
    """Coordinator that routes requests to preview conversion strategies."""

    def __init__(self, strategies: Sequence[PreviewPdfStrategy]) -> None:
        self._strategies = list(strategies)

    def convert(self, request: PreviewPdfConversionRequest) -> bytes:
        for strategy in self._strategies:
            if strategy.supports(request):
                return strategy.convert(request)
        raise ValueError(
            "No preview PDF strategy matched "
            f"mime_type={request.normalized_mime_type} extension={Path(request.filename).suffix}"
        )
