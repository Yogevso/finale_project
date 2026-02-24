"""Collaboration Service - Handles real-time collaboration state management"""

from datetime import datetime, timedelta
from typing import Optional

from jose import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Document, User, UserRole
from app.services.permissions import can_edit_document as permission_can_edit_document
from app.services.permissions import can_view_document as permission_can_view_document
from app.services.permissions import is_internal_user

# Collaboration token expiry (shorter than regular access tokens)
COLLAB_TOKEN_EXPIRE_MINUTES = 60


class CollaborationService:
    """Service for managing real-time collaboration"""

    @staticmethod
    def _tenant_boundary_allows(user: User, document: Document) -> bool:
        role = user.role if isinstance(user.role, UserRole) else UserRole(user.role)
        if role == UserRole.SYSTEM_ADMIN:
            return True

        # Customer access is assignment-based and already covered by view permissions.
        if role == UserRole.CUSTOMER:
            return True

        if not is_internal_user(user):
            return False

        # Internal users are tenant-scoped for collaboration endpoints.
        if document.tenant_id is None:
            return True
        return user.tenant_id == document.tenant_id

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
        if expires_delta is None:
            expires_delta = timedelta(minutes=COLLAB_TOKEN_EXPIRE_MINUTES)

        expire = datetime.utcnow() + expires_delta

        to_encode = {
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role.value if isinstance(user.role, UserRole) else user.role,
            "document_id": str(document_id),
            "permissions": permissions,
            "type": "collaboration",
            "exp": expire,
            "iat": datetime.utcnow(),
        }

        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    @staticmethod
    def get_user_permissions(user: User, document: Document) -> list[str]:
        """
        Determine user's collaboration permissions for a document.

        Returns list of permissions: ['read'] or ['read', 'write']
        """
        permissions = []

        # Check if user can view the document
        if CollaborationService.can_view_document(user, document):
            permissions.append("read")

        # Check if user can edit the document
        if CollaborationService.can_edit_document(user, document):
            permissions.append("write")

        return permissions

    @staticmethod
    def can_view_document(user: User, document: Document) -> bool:
        """Check if user can view/collaborate on a document"""
        if not user or not user.is_active:
            return False

        if not permission_can_view_document(user, document):
            return False

        return CollaborationService._tenant_boundary_allows(user, document)

    @staticmethod
    def can_edit_document(user: User, document: Document) -> bool:
        """Check if user can edit a document in collaboration mode"""
        if not user or not user.is_active:
            return False

        if not permission_can_edit_document(user, document):
            return False

        return CollaborationService._tenant_boundary_allows(user, document)

    @staticmethod
    def get_document_state(db: Session, document_id: int) -> Optional[bytes]:
        """Get the Yjs state for a document"""
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            return document.yjs_state
        return None

    @staticmethod
    def save_document_state(db: Session, document_id: int, state: bytes) -> bool:
        """Save the Yjs state for a document"""
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return False

        document.yjs_state = state
        document.updated_at = datetime.utcnow()
        db.commit()
        return True

    @staticmethod
    def clear_document_state(db: Session, document_id: int) -> bool:
        """Clear the Yjs state for a document (useful for reset)"""
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return False

        document.yjs_state = None
        db.commit()
        return True

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
