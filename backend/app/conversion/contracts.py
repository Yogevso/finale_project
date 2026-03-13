"""Lightweight conversion-service contracts with no plugin/runtime imports."""

from __future__ import annotations

from typing import Any, Protocol


class DocumentConversionService(Protocol):
    """Abstraction for services that can produce HTML and reader artifacts."""

    def convert_document_to_html(
        self,
        content: bytes,
        mime_type: str,
        filename: str = "",
    ) -> str | None: ...

    def convert_word_to_html(self, content: bytes) -> str | None: ...

    def convert_document_to_reader_artifact(
        self,
        content: bytes,
        mime_type: str,
        filename: str = "",
    ) -> dict[str, Any] | None: ...

    def describe_strategy_capabilities(self) -> dict[str, tuple[str, ...]]: ...
