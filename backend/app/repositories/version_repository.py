"""Repository for version aggregate access patterns."""

from __future__ import annotations

from sqlalchemy.orm import joinedload

from app.models import Version
from app.repositories.base import BaseRepository


class VersionRepository(BaseRepository):
    """Version persistence/query access."""

    def _query(self, include_users: bool = False):
        query = self.db.query(Version)
        if include_users:
            query = query.options(
                joinedload(Version.created_by_user),
                joinedload(Version.published_by_user),
            )
        return query

    def list_for_document(self, document_id: int, include_users: bool = False) -> list[Version]:
        return (
            self._query(include_users)
            .filter(Version.document_id == document_id)
            .order_by(Version.version_number.desc())
            .all()
        )

    def get_by_id_for_document(
        self,
        version_id: int,
        document_id: int,
        include_users: bool = False,
    ) -> Version | None:
        return (
            self._query(include_users)
            .filter(Version.id == version_id, Version.document_id == document_id)
            .first()
        )

    def get_latest_for_document(self, document_id: int) -> Version | None:
        return (
            self.db.query(Version)
            .filter(Version.document_id == document_id)
            .order_by(Version.version_number.desc())
            .first()
        )

    def get_latest_published_for_document(self, document_id: int) -> Version | None:
        return (
            self.db.query(Version)
            .filter(
                Version.document_id == document_id,
                Version.is_published == True,  # noqa: E712
            )
            .order_by(Version.version_number.desc())
            .first()
        )

