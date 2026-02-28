"""Shared collaboration manager primitives."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import User
from app.repositories import DocumentRepository
from app.services.collaboration_service import CollaborationService


class CollaborationManagerBase:
    """Base class for collaboration managers with shared access checks."""

    def __init__(
        self,
        db: Session,
        collaboration_service: CollaborationService | None = None,
        document_repository: DocumentRepository | None = None,
    ) -> None:
        self.db = db
        self.collaboration_service = collaboration_service or CollaborationService()
        self.document_repository = document_repository or DocumentRepository(db)

    def get_document_or_404(self, document_id: int):
        document = self.document_repository.get_by_id(document_id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return document

    def ensure_document_read_access(
        self,
        *,
        document,
        current_user: User,
        denied_detail: str = "You don't have permission to access this document",
    ) -> list[str]:
        permissions = self.collaboration_service.get_user_permissions_for_document(
            current_user, document
        )
        if not permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=denied_detail)
        return permissions

    def ensure_document_write_access(
        self,
        *,
        document,
        current_user: User,
        denied_detail: str = "You don't have permission to edit this document",
    ) -> list[str]:
        permissions = self.collaboration_service.get_user_permissions_for_document(
            current_user, document
        )
        if "write" not in permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=denied_detail)
        return permissions
