"""Collaboration state persistence port."""

from __future__ import annotations

from typing import Protocol


class CollaborationStatePort(Protocol):
    """Persist and retrieve collaboration state for documents."""

    def get_document_state(self, document_id: int) -> bytes | None:
        """Return binary Yjs state for a document, if present."""

    def save_document_state(self, document_id: int, state: bytes) -> bool:
        """Persist binary Yjs state for a document."""

    def clear_document_state(self, document_id: int) -> bool:
        """Remove persisted Yjs state for a document."""
