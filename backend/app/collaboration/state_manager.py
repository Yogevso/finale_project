"""Collaboration state manager."""

from __future__ import annotations

from app.collaboration.base import CollaborationManagerBase
from app.errors import NotFoundError, OperationFailedError
from app.models import User


class CollabStateManager(CollaborationManagerBase):
    """Manages collaboration state persistence and status workflows."""

    def get_document_state(self, *, document_id: int, current_user: User) -> bytes:
        document = self.get_document_or_404(document_id)
        self.ensure_document_read_access(document=document, current_user=current_user)

        state = document.yjs_state
        if state is None:
            raise NotFoundError("No collaboration state exists for this document")
        return state

    def save_document_state(
        self,
        *,
        document_id: int,
        current_user: User,
        state: bytes,
    ) -> dict[str, object]:
        document = self.get_document_or_404(document_id)
        self.ensure_document_write_access(document=document, current_user=current_user)

        success = self.collaboration_service.save_document_state_for_document(
            self.db, document_id, state
        )
        if not success:
            raise OperationFailedError("Failed to save document state")
        return {"message": "State saved successfully", "size": len(state)}

    def clear_document_state(self, *, document_id: int, current_user: User) -> dict[str, str]:
        document = self.get_document_or_404(document_id)
        self.ensure_document_write_access(
            document=document,
            current_user=current_user,
            denied_detail="You don't have permission to clear this document's state",
        )

        success = self.collaboration_service.clear_document_state_for_document(self.db, document_id)
        if not success:
            raise OperationFailedError("Failed to clear document state")
        return {"message": "State cleared successfully"}

    def get_collaboration_status(
        self, *, document_id: int, current_user: User
    ) -> dict[str, object]:
        document = self.get_document_or_404(document_id)
        self.ensure_document_read_access(document=document, current_user=current_user)

        collaborators = self.collaboration_service.get_active_collaborators(document_id)
        return {
            "document_id": document_id,
            "active_collaborators": collaborators,
            "is_collaborative_mode": document.yjs_state is not None,
            "has_unsaved_changes": False,
        }
