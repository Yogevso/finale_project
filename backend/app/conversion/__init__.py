"""Lazy public exports for conversion pipelines, contracts, and strategies."""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = [
    "DocumentConversionPipeline",
    "DocumentConversionOutput",
    "DocumentConversionRequest",
    "DocumentConversionService",
    "DocumentConverterStrategy",
    "HtmlPassthroughStrategy",
    "PowerPointConverterStrategy",
    "StrategyCapabilityDescriptor",
    "TextConverterStrategy",
    "WordConverterStrategy",
    "get_document_conversion_pipeline",
]

if TYPE_CHECKING:
    from app.conversion.contracts import DocumentConversionService
    from app.conversion.document_pipeline import (
        DocumentConversionPipeline,
        get_document_conversion_pipeline,
    )
    from app.conversion.document_strategies import (
        DocumentConversionOutput,
        DocumentConverterStrategy,
        HtmlPassthroughStrategy,
        PowerPointConverterStrategy,
        StrategyCapabilityDescriptor,
        TextConverterStrategy,
        WordConverterStrategy,
    )
    from app.conversion.models import DocumentConversionRequest


def __getattr__(name: str):
    if name == "DocumentConversionService":
        from app.conversion.contracts import DocumentConversionService

        return DocumentConversionService

    if name in {"DocumentConversionPipeline", "get_document_conversion_pipeline"}:
        from app.conversion.document_pipeline import (
            DocumentConversionPipeline,
            get_document_conversion_pipeline,
        )

        exports = {
            "DocumentConversionPipeline": DocumentConversionPipeline,
            "get_document_conversion_pipeline": get_document_conversion_pipeline,
        }
        return exports[name]

    if name in {
        "DocumentConversionOutput",
        "DocumentConverterStrategy",
        "HtmlPassthroughStrategy",
        "PowerPointConverterStrategy",
        "StrategyCapabilityDescriptor",
        "TextConverterStrategy",
        "WordConverterStrategy",
    }:
        from app.conversion.document_strategies import (
            DocumentConversionOutput,
            DocumentConverterStrategy,
            HtmlPassthroughStrategy,
            PowerPointConverterStrategy,
            StrategyCapabilityDescriptor,
            TextConverterStrategy,
            WordConverterStrategy,
        )

        exports = {
            "DocumentConversionOutput": DocumentConversionOutput,
            "DocumentConverterStrategy": DocumentConverterStrategy,
            "HtmlPassthroughStrategy": HtmlPassthroughStrategy,
            "PowerPointConverterStrategy": PowerPointConverterStrategy,
            "StrategyCapabilityDescriptor": StrategyCapabilityDescriptor,
            "TextConverterStrategy": TextConverterStrategy,
            "WordConverterStrategy": WordConverterStrategy,
        }
        return exports[name]

    if name == "DocumentConversionRequest":
        from app.conversion.models import DocumentConversionRequest

        return DocumentConversionRequest

    raise AttributeError(f"module 'app.conversion' has no attribute {name!r}")
