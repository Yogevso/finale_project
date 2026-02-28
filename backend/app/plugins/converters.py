"""Plugin registry for document conversion strategies."""

from __future__ import annotations

from collections.abc import Sequence

from app.conversion.document_strategies import (
    DocumentConverterStrategy,
    HtmlPassthroughStrategy,
    PdfConverterStrategy,
    TextConverterStrategy,
    WordConverterStrategy,
)
from app.conversion.models import DocumentConversionRequest


class DocumentConverterPluginRegistry:
    """Ordered registry of document converter plugins."""

    def __init__(self, plugins: Sequence[DocumentConverterStrategy] | None = None) -> None:
        self._plugins: list[DocumentConverterStrategy] = []
        self.load(plugins or [])

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(plugin.name for plugin in self._plugins)

    def load(self, plugins: Sequence[DocumentConverterStrategy]) -> None:
        for plugin in plugins:
            self.register(plugin)

    def register(self, plugin: DocumentConverterStrategy) -> None:
        name = (plugin.name or "").strip().lower()
        if not name:
            raise ValueError("Converter plugin name is required")
        if name in self.names:
            raise ValueError(f"Converter plugin '{name}' is already registered")
        self._plugins.append(plugin)

    def validate(self) -> None:
        if not self._plugins:
            raise ValueError("At least one converter plugin must be registered")

    def select(self, request: DocumentConversionRequest) -> DocumentConverterStrategy | None:
        self.validate()
        for plugin in self._plugins:
            if plugin.supports(request):
                return plugin
        return None


def build_default_document_converter_registry(
    *,
    pdf_converter: PdfConverterStrategy | None = None,
    word_converter: WordConverterStrategy | None = None,
) -> DocumentConverterPluginRegistry:
    """Load default converter plugins in deterministic precedence order."""
    pdf_plugin = pdf_converter or PdfConverterStrategy()
    word_plugin = word_converter or WordConverterStrategy()
    registry = DocumentConverterPluginRegistry(
        plugins=[
            pdf_plugin,
            word_plugin,
            HtmlPassthroughStrategy(),
            TextConverterStrategy(),
        ]
    )
    registry.validate()
    return registry
