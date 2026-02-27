"""Public API for the collaboration bounded context."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Document, User
from app.services.collaboration_service import CollaborationService


@dataclass
class CollaborationContextAPI:
    """Stable API for collaboration permissions and state operations."""

    db: Session

    def create_token(self, user: User, document_id: int, permissions: list[str]) -> str:
        return CollaborationService.create_collab_token(user, document_id, permissions)

    def get_permissions(self, user: User, document: Document) -> list[str]:
        service = CollaborationService()
        return service.get_user_permissions_for_document(user, document)

    def get_state(self, document_id: int) -> bytes | None:
        service = CollaborationService()
        return service.get_document_state_for_document(self.db, document_id)

    def save_state(self, document_id: int, state: bytes) -> bool:
        service = CollaborationService()
        return service.save_document_state_for_document(self.db, document_id, state)

    def clear_state(self, document_id: int) -> bool:
        service = CollaborationService()
        return service.clear_document_state_for_document(self.db, document_id)
