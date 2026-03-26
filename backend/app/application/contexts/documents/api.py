"""Public API for the documents bounded context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.container import AppContainer, build_container
from app.dependencies.tenant import TenantContext
from app.models import Document, DocumentStatus, DocumentVisibility, User


@dataclass
class DocumentsContextAPI:
    """Stable context-level API for document operations."""

    db: Session
    tenant_ctx: Optional[TenantContext] = None
    container: AppContainer | None = None

    def _document_service(self):
        container = self.container or build_container()
        return container.document_service(self.db, self.tenant_ctx)

    def get_document(self, document_id: int) -> Document | None:
        return self._document_service().get_document(document_id)

    def list_documents(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        status: DocumentStatus | None = None,
        visibility: DocumentVisibility | None = None,
        category: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Document], int]:
        return self._document_service().get_documents(
            skip=skip,
            limit=limit,
            status=status,
            visibility=visibility,
            category=category,
            search=search,
        )

    def delete_document(self, document_id: int, user: User) -> None:
        self._document_service().delete_document(document_id, user)
