"""Public API for the reviews bounded context."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.container import AppContainer, build_container
from app.models import User
from app.schemas import VersionCreate


@dataclass
class ReviewsContextAPI:
    """Stable API for review/version workflow operations."""

    db: Session
    container: AppContainer | None = None

    def _version_service(self):
        container = self.container or build_container()
        return container.version_service(self.db)

    def get_versions_for_document(self, document_id: int, current_user: User) -> list[dict]:
        return self._version_service().get_versions(document_id, current_user)

    def create_version_for_document(
        self,
        document_id: int,
        version_data: VersionCreate,
        current_user: User,
    ) -> dict:
        return self._version_service().create_version(document_id, version_data, current_user)
