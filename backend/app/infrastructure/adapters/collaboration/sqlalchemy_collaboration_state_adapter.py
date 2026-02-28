"""SQLAlchemy adapter for collaboration state persistence."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.ports import CollaborationStatePort
from app.models import Document


class SqlAlchemyCollaborationStateAdapter(CollaborationStatePort):
    """Persist collaboration state in the `documents.yjs_state` column."""

    def __init__(self, db: Session):
        self._db = db

    def get_document_state(self, document_id: int) -> bytes | None:
        document = self._db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return None
        return document.yjs_state

    def save_document_state(self, document_id: int, state: bytes) -> bool:
        document = self._db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return False

        document.yjs_state = state
        document.updated_at = datetime.utcnow()
        try:
            self._db.commit()
            return True
        except Exception:
            self._db.rollback()
            return False

    def clear_document_state(self, document_id: int) -> bool:
        document = self._db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return False

        document.yjs_state = None
        try:
            self._db.commit()
            return True
        except Exception:
            self._db.rollback()
            return False
