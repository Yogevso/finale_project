"""Composition helpers for wiring ports and adapters."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.ports import CollaborationStatePort, EmailPort, StoragePort
from app.infrastructure.adapters.collaboration import SqlAlchemyCollaborationStateAdapter
from app.infrastructure.adapters.email import SmtpEmailAdapter
from app.infrastructure.adapters.storage import StorageBackendAdapter
from app.services.storage_service import get_storage_backend


def get_email_port() -> EmailPort:
    """Resolve default email port implementation."""
    return SmtpEmailAdapter()


def get_storage_port() -> StoragePort:
    """Resolve default storage port implementation."""
    return StorageBackendAdapter(get_storage_backend())


def get_collaboration_state_port(db: Session) -> CollaborationStatePort:
    """Resolve default collaboration state persistence port."""
    return SqlAlchemyCollaborationStateAdapter(db)

