"""Repository for document aggregate access patterns."""

from __future__ import annotations

from sqlalchemy.orm import Query

from app.domain.specifications import TenantScopeSpec, VisibilitySpec
from app.models import Document, User
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository):
    """Document persistence/query access."""

    def query(self) -> Query:
        return self.db.query(Document)

    def get_by_id(self, document_id: int) -> Document | None:
        return self.query().filter(Document.id == document_id).first()

    def scoped_query_for_user(self, user: User) -> Query:
        return TenantScopeSpec.for_user(user).apply(self.query(), Document)

    def portal_visible_query_for_customer(self, user: User) -> Query:
        return VisibilitySpec.customer_portal(user.tenant_id).apply(self.query(), Document)

    def get_by_id_for_user(self, document_id: int, user: User) -> Document | None:
        return self.scoped_query_for_user(user).filter(Document.id == document_id).first()
