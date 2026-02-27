"""Public API for the reviews bounded context."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import User
from app.schemas import VersionCreate
from app.services.version_service import VersionService


@dataclass
class ReviewsContextAPI:
    """Stable API for review/version workflow operations."""

    db: Session

    def get_versions_for_document(self, document_id: int, current_user: User) -> list[dict]:
        return VersionService(self.db).get_versions(document_id, current_user)

    def create_version_for_document(
        self,
        document_id: int,
        version_data: VersionCreate,
        current_user: User,
    ) -> dict:
        return VersionService(self.db).create_version(document_id, version_data, current_user)
