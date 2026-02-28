"""Collaboration Service - Handles real-time collaboration state management"""

from datetime import timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.adapters import CollaborationContractAdapter
from app.application.policies import DocumentAccessPolicy
from app.auth_context import CollaborationAuthService
from app.domain.ports import CollaborationStatePort
from app.infrastructure.composition import get_collaboration_state_port
from app.models import Document, User
from app.services.permissions import Permission, has_permission


class CollaborationService:
    """Service for managing real-time collaboration"""

    def __init__(
        self,
        state_port: CollaborationStatePort | None = None,
        document_policy: DocumentAccessPolicy | None = None,
        collaboration_auth_service: CollaborationAuthService | None = None,
        contract_adapter: CollaborationContractAdapter | None = None,
    ):
        self._state_port = state_port
        self._document_policy = document_policy or DocumentAccessPolicy()
        self._collaboration_auth_service = collaboration_auth_service or CollaborationAuthService()
        self._contract_adapter = contract_adapter or CollaborationContractAdapter()

    def _resolve_state_port(self, db: Session) -> CollaborationStatePort:
        return self._state_port or get_collaboration_state_port(db)

    def issue_collab_token(
        self,
        user: User,
        document_id: int,
        permissions: list[str],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create a collaboration JWT token for WebSocket access."""
        normalized_document_id = self._contract_adapter.coerce_document_id(document_id)
        normalized_permissions = self._contract_adapter.normalize_permissions(permissions)
        return self._collaboration_auth_service.create_collab_token(
            user=user,
            document_id=normalized_document_id,
            permissions=normalized_permissions,
            expires_delta=expires_delta,
        )

    @staticmethod
    def create_collab_token(
        user: User,
        document_id: int,
        permissions: list[str],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create a JWT token specifically for WebSocket collaboration.

        This token includes document-specific permissions and is validated
        by the Hocuspocus server.
        """
        contract_adapter = CollaborationContractAdapter()
        normalized_document_id = contract_adapter.coerce_document_id(document_id)
        normalized_permissions = contract_adapter.normalize_permissions(permissions)
        return CollaborationAuthService().create_collab_token(
            user=user,
            document_id=normalized_document_id,
            permissions=normalized_permissions,
            expires_delta=expires_delta,
        )

    def can_view_document_access(self, user: User, document: Document) -> bool:
        if not user or not user.is_active:
            return False

        if not self._document_policy.can_view_document(user, document):
            return False

        return self._document_policy.collaboration_tenant_boundary_allows(user, document)

    def can_edit_document_access(self, user: User, document: Document) -> bool:
        if not user or not user.is_active:
            return False

        if not self._document_policy.can_edit_document(
            user,
            document,
            has_edit_permission=has_permission(user, Permission.EDIT_DOCUMENT),
        ):
            return False

        return self._document_policy.collaboration_tenant_boundary_allows(user, document)

    def get_user_permissions_for_document(self, user: User, document: Document) -> list[str]:
        """
        Determine user's collaboration permissions for a document.

        Returns list of permissions: ['read'] or ['read', 'write']
        """
        can_view = self.can_view_document_access(user, document)
        can_edit = self.can_edit_document_access(user, document)
        return self._contract_adapter.permissions_from_access(
            can_view=can_view,
            can_edit=can_edit,
        )

    @staticmethod
    def get_user_permissions(user: User, document: Document) -> list[str]:
        """Compatibility wrapper for existing call sites."""
        return CollaborationService().get_user_permissions_for_document(user, document)

    @staticmethod
    def can_view_document(user: User, document: Document) -> bool:
        """Compatibility wrapper for existing call sites."""
        return CollaborationService().can_view_document_access(user, document)

    @staticmethod
    def can_edit_document(user: User, document: Document) -> bool:
        """Compatibility wrapper for existing call sites."""
        return CollaborationService().can_edit_document_access(user, document)

    def get_document_state_for_document(self, db: Session, document_id: int) -> Optional[bytes]:
        port = self._resolve_state_port(db)
        return port.get_document_state(document_id)

    def save_document_state_for_document(self, db: Session, document_id: int, state: bytes) -> bool:
        port = self._resolve_state_port(db)
        return port.save_document_state(document_id, state)

    def clear_document_state_for_document(self, db: Session, document_id: int) -> bool:
        port = self._resolve_state_port(db)
        return port.clear_document_state(document_id)

    @staticmethod
    def get_document_state(
        db: Session,
        document_id: int,
        state_port: CollaborationStatePort | None = None,
    ) -> Optional[bytes]:
        """Get the Yjs state for a document"""
        return CollaborationService(state_port=state_port).get_document_state_for_document(
            db, document_id
        )

    @staticmethod
    def save_document_state(
        db: Session,
        document_id: int,
        state: bytes,
        state_port: CollaborationStatePort | None = None,
    ) -> bool:
        """Save the Yjs state for a document"""
        return CollaborationService(state_port=state_port).save_document_state_for_document(
            db, document_id, state
        )

    @staticmethod
    def clear_document_state(
        db: Session,
        document_id: int,
        state_port: CollaborationStatePort | None = None,
    ) -> bool:
        """Clear the Yjs state for a document (useful for reset)"""
        return CollaborationService(state_port=state_port).clear_document_state_for_document(
            db, document_id
        )

    @staticmethod
    def get_active_collaborators(document_id: int) -> list[dict]:
        """
        Get list of active collaborators for a document.

        This would typically be tracked by the Hocuspocus server,
        but we can query it via HTTP if needed.
        """
        # This is a placeholder - in production, you'd query the Hocuspocus server
        # via its HTTP API or use a shared Redis/database for presence
        return []
