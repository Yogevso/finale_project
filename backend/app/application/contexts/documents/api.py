"""Public API for the documents bounded context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.dependencies.tenant import TenantContext
from app.models import Document, DocumentStatus, DocumentVisibility, User
from app.services.document_service import DocumentService


@dataclass
class DocumentsContextAPI:
    """Stable context-level API for document operations."""

    db: Session
    tenant_ctx: Optional[TenantContext] = None

    def get_document(self, document_id: int) -> Document | None:
        return DocumentService(self.db, self.tenant_ctx).get_document(document_id)

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
        return DocumentService(self.db, self.tenant_ctx).get_documents(
            skip=skip,
            limit=limit,
            status=status,
            visibility=visibility,
            category=category,
            search=search,
        )

    def delete_document(self, document_id: int, user: User) -> None:
        DocumentService(self.db, self.tenant_ctx).delete_document(document_id, user)

