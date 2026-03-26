"""Public API for the collaboration bounded context."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.container import AppContainer, build_container
from app.models import Document, User


@dataclass
class CollaborationContextAPI:
    """Stable API for collaboration permissions and state operations."""

    db: Session
    container: AppContainer | None = None

    def _collaboration_service(self):
        container = self.container or build_container()
        return container.collaboration_service(self.db)

    def create_token(self, user: User, document_id: int, permissions: list[str]) -> str:
        return self._collaboration_service().issue_collab_token(user, document_id, permissions)

    def get_permissions(self, user: User, document: Document) -> list[str]:
        return self._collaboration_service().get_user_permissions_for_document(user, document)

    def get_state(self, document_id: int) -> bytes | None:
        return self._collaboration_service().get_document_state_for_document(self.db, document_id)

    def save_state(self, document_id: int, state: bytes) -> bool:
        return self._collaboration_service().save_document_state_for_document(
            self.db,
            document_id,
            state,
        )

    def clear_state(self, document_id: int) -> bool:
        return self._collaboration_service().clear_document_state_for_document(
            self.db,
            document_id,
        )
