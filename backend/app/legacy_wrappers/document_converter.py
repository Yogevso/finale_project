"""Strangler wrapper around legacy document converter utility module."""

from __future__ import annotations

from typing import Any, Optional

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

    @staticmethod
    def _legacy_module():
        from app.utils import document_converter

        return document_converter

    def _record_legacy_usage(self) -> None:
        _tracker.increment_call(DOCUMENT_CONVERTER_WRAPPER_NAME)

    def convert_word_to_html(self, content: bytes) -> Optional[str]:
        self._record_legacy_usage()
        return self._legacy_module().convert_word_to_html(content)

    def convert_document_to_html(
        self, content: bytes, mime_type: str, filename: str = ""
    ) -> Optional[str]:
        self._record_legacy_usage()
        return self._legacy_module().convert_document_to_html(content, mime_type, filename)

    def convert_pdf_to_reader_artifact(self, pdf_bytes: bytes) -> dict[str, Any]:
        self._record_legacy_usage()
        return self._legacy_module().convert_pdf_to_reader_artifact(pdf_bytes)

    def extract_pdf_toc(self, pdf_bytes: bytes) -> dict[str, Any]:
        self._record_legacy_usage()
        return self._legacy_module().extract_pdf_toc(pdf_bytes)


_document_converter_wrapper = DocumentConverterStranglerWrapper()


def get_document_converter_wrapper() -> DocumentConverterStranglerWrapper:
    """Resolve singleton wrapper for document converter calls."""
    return _document_converter_wrapper
