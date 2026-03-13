"""Pipeline coordinator for document conversion strategies."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from app.conversion.document_strategies import (
    DocumentConversionOutput,
    DocumentConverterStrategy,
    PowerPointConverterStrategy,
    WordConverterStrategy,
)
from app.conversion.models import DocumentConversionRequest
from app.plugins.converters import (
    DocumentConverterPluginRegistry,
    build_default_document_converter_registry,
)

logger = logging.getLogger(__name__)


class DocumentConversionPipeline:
    """Coordinates document conversion strategy selection."""

    def __init__(
        self,
        *,
        strategies: Sequence[DocumentConverterStrategy] | None = None,
        word_converter: WordConverterStrategy | None = None,
        powerpoint_converter: PowerPointConverterStrategy | None = None,
        converter_registry: DocumentConverterPluginRegistry | None = None,
    ) -> None:
        self._word_converter = word_converter or WordConverterStrategy()
        self._powerpoint_converter = powerpoint_converter or PowerPointConverterStrategy()
        if converter_registry is not None:
            self._converter_registry = converter_registry
        elif strategies is not None:
            self._converter_registry = DocumentConverterPluginRegistry(strategies)
        else:
            self._converter_registry = build_default_document_converter_registry(
                word_converter=self._word_converter,
                powerpoint_converter=self._powerpoint_converter,
            )

    @staticmethod
    def _build_request(content: bytes, mime_type: str, filename: str) -> DocumentConversionRequest:
        return DocumentConversionRequest(
            content=content,
            mime_type=mime_type,
            filename=filename,
        )

    def describe_strategy_capabilities(self) -> dict[str, tuple[str, ...]]:
        """Expose registered strategy outputs for diagnostics and DI consumers."""
        return {
            plugin.name: plugin.capabilities.as_names()
            for plugin in self._converter_registry.plugins
        }

    def convert_document_to_html(
        self,
        content: bytes,
        mime_type: str,
        filename: str = "",
    ) -> str | None:
        request = self._build_request(content, mime_type, filename)
        converter_plugin = self._converter_registry.select(request)
        if converter_plugin:
            return converter_plugin.convert_to_html(request)

        logger.info(
            "No document conversion strategy matched mime_type=%s filename=%s",
            mime_type,
            filename,
        )
        return None

    def convert_word_to_html(self, content: bytes) -> str | None:
        return self._word_converter.convert_word_to_html(content)

    def convert_document_to_reader_artifact(
        self,
        content: bytes,
        mime_type: str,
        filename: str = "",
    ) -> dict[str, Any] | None:
        request = self._build_request(content, mime_type, filename)
        converter_plugin = self._converter_registry.select(request)
        if converter_plugin and converter_plugin.capabilities.supports(
            DocumentConversionOutput.READER_ARTIFACT
        ):
            artifact = converter_plugin.convert_to_reader_artifact(request)
            if artifact is not None:
                return artifact
        elif converter_plugin:
            logger.info(
                "Strategy %s matched mime_type=%s filename=%s but does not support reader artifacts; outputs=%s",
                converter_plugin.name,
                mime_type,
                filename,
                converter_plugin.capabilities.as_names(),
            )
            return None

        logger.info(
            "No reader-artifact conversion strategy matched mime_type=%s filename=%s",
            mime_type,
            filename,
        )
        return None

_document_conversion_pipeline = DocumentConversionPipeline()


def get_document_conversion_pipeline() -> DocumentConversionPipeline:
    """Resolve shared document conversion pipeline singleton."""
    return _document_conversion_pipeline
