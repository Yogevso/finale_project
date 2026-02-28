"""Typed conversion pipeline request models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DocumentConversionRequest:
    """Input payload for document-to-HTML conversion."""

    content: bytes
    mime_type: str
    filename: str = ""

    @property
    def normalized_mime_type(self) -> str:
        return (self.mime_type or "").lower()

    @property
    def normalized_filename(self) -> str:
        return (self.filename or "").lower()

    @property
    def extension(self) -> str:
        return Path(self.normalized_filename).suffix


@dataclass(frozen=True, slots=True)
class PreviewPdfConversionRequest:
    """Input payload for non-PDF to preview-PDF conversion."""

    content: bytes
    mime_type: str
    filename: str

    @property
    def normalized_mime_type(self) -> str:
        return (self.mime_type or "").lower()

    @property
    def extension(self) -> str:
        return Path((self.filename or "").lower()).suffix
