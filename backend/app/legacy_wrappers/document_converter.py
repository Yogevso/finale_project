"""Strangler wrapper around legacy document converter utility module."""

from __future__ import annotations

from typing import Any, Optional

from app.conversion.contracts import DocumentConversionService
from app.legacy_wrappers.tracking import get_legacy_wrapper_tracker

DOCUMENT_CONVERTER_WRAPPER_NAME = "document_converter"

_tracker = get_legacy_wrapper_tracker()
_tracker.register_wrapper(
    wrapper_name=DOCUMENT_CONVERTER_WRAPPER_NAME,
    legacy_module="app.utils.document_converter",
    migration_completion_percent=0,
)


class DocumentConverterStranglerWrapper:
    """Wrapper boundary for converter migration from legacy utility module."""

    def __init__(self, conversion_service: DocumentConversionService | None = None) -> None:
        if conversion_service is None:
            from app.conversion.document_pipeline import get_document_conversion_pipeline

            conversion_service = get_document_conversion_pipeline()
        self._conversion_service = conversion_service

    def _record_legacy_usage(self) -> None:
        _tracker.increment_call(DOCUMENT_CONVERTER_WRAPPER_NAME)

    def convert_word_to_html(self, content: bytes) -> Optional[str]:
        self._record_legacy_usage()
        return self._conversion_service.convert_word_to_html(content)

    def convert_document_to_html(
        self, content: bytes, mime_type: str, filename: str = ""
    ) -> Optional[str]:
        self._record_legacy_usage()
        return self._conversion_service.convert_document_to_html(content, mime_type, filename)

    def convert_document_to_reader_artifact(
        self,
        content: bytes,
        mime_type: str,
        filename: str = "",
    ) -> Optional[dict[str, Any]]:
        self._record_legacy_usage()
        return self._conversion_service.convert_document_to_reader_artifact(
            content,
            mime_type,
            filename,
        )


_document_converter_wrapper: DocumentConverterStranglerWrapper | None = None


def get_document_converter_wrapper() -> DocumentConverterStranglerWrapper:
    """Resolve singleton wrapper for document converter calls."""
    global _document_converter_wrapper
    if _document_converter_wrapper is None:
        _document_converter_wrapper = DocumentConverterStranglerWrapper()
    return _document_converter_wrapper
