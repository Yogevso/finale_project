"""
Permission Dependencies for FastAPI

This module provides FastAPI dependencies for permission-based access control.
"""

from typing import Callable, List, Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Document, User, UserRole
from app.security import get_current_active_user
from app.services.permissions import (
    Permission,
    can_delete_document,
    can_edit_document,
    can_publish_document,
    can_view_document,
    has_permission,
    is_admin_or_above,
    is_editor_or_above,
    is_internal_user,
    is_manager_or_above,
)


def require_permission(permission: Permission) -> Callable:
    """
    Dependency factory that requires a specific permission.

    Usage:
        @router.get("/documents")
        async def list_docs(user: User = Depends(require_permission(Permission.VIEW_INTERNAL_DOCS))):
            ...

    Args:
        permission: The permission required

    Returns:
        A dependency function that validates the permission
    """

    async def dependency(current_user: User = Depends(get_current_active_user)) -> User:
        if not has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value}",
            )
        return current_user

    return dependency


def require_any_permission(*permissions: Permission) -> Callable:
    """
    Dependency factory that requires at least one of the specified permissions.

    Usage:
        @router.get("/documents")
        async def list_docs(
            user: User = Depends(require_any_permission(
                Permission.VIEW_PUBLIC_DOCS,
                Permission.VIEW_INTERNAL_DOCS
            ))
        ):
            ...
    """

    async def dependency(current_user: User = Depends(get_current_active_user)) -> User:
        for permission in permissions:
            if has_permission(current_user, permission):
                return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: requires one of {[p.value for p in permissions]}",
        )

    return dependency


def require_any_role(roles: List[UserRole]) -> Callable:
    """
    Dependency factory that requires the user to have one of the specified roles.

    Usage:
        @router.post("/admin/settings")
        async def update_settings(
            user: User = Depends(require_any_role([UserRole.SYSTEM_ADMIN, UserRole.ADMIN]))
        ):
            ...
    """

    async def dependency(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: requires role {[r.value for r in roles]}",
            )
        return current_user

    return dependency


async def require_internal_user(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Dependency that requires the user to be an internal staff member.
    Blocks customers from accessing internal-only endpoints.

    Usage:
        @router.get("/internal/dashboard")
        async def dashboard(user: User = Depends(require_internal_user)):
            ...
    """
    if not is_internal_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: internal users only"
        )
    return current_user


async def require_customer(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Dependency that requires the user to be a customer.
    Used for customer-only portal endpoints.

    Usage:
        @router.get("/portal/my-documents")
        async def my_docs(user: User = Depends(require_customer)):
            ...
    """
    if current_user.role != UserRole.CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: customers only"
        )
    return current_user


async def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Dependency that requires admin or system_admin role.

    Usage:
        @router.post("/admin/users")
        async def create_user(user: User = Depends(require_admin)):
            ...
    """
    if not is_admin_or_above(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: admin privileges required"
        )
    return current_user


async def require_system_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Dependency that requires system_admin role.

    Usage:
        @router.post("/system/settings")
        async def update_system(user: User = Depends(require_system_admin)):
            ...
    """
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: system administrator privileges required",
        )
    return current_user


async def require_manager(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Dependency that requires manager or above role.

    Usage:
        @router.post("/documents/{id}/publish")
        async def publish_doc(user: User = Depends(require_manager)):
            ...
    """
    if not is_manager_or_above(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: manager privileges required",
        )
    return current_user


async def require_editor(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Dependency that requires editor or above role.

    Usage:
        @router.post("/documents")
        async def create_doc(user: User = Depends(require_editor)):
            ...
    """
    if not is_editor_or_above(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: editor privileges required",
        )
    return current_user


class DocumentAccessChecker:
    """
    Dependency class for checking document access.

    This provides a reusable way to verify document permissions
    with different access levels (view, edit, delete, publish).
    """

    def __init__(self, access_type: str = "view"):
        """
        Initialize the checker with an access type.

        Args:
            access_type: One of "view", "edit", "delete", "publish"
        """
        self.access_type = access_type

    async def __call__(
        self,
        document_id: int,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ) -> Document:
        """
        Check if user can access the document.

        Returns the document if access is granted, raises HTTPException otherwise.
        """
        document = db.query(Document).filter(Document.id == document_id).first()

        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        # Check access based on type
        access_granted = False

        if self.access_type == "view":
            access_granted = can_view_document(current_user, document)
        elif self.access_type == "edit":
            access_granted = can_edit_document(current_user, document)
        elif self.access_type == "delete":
            access_granted = can_delete_document(current_user, document)
        elif self.access_type == "publish":
            access_granted = can_publish_document(current_user, document)
        else:
            # Default to view
            access_granted = can_view_document(current_user, document)

        if not access_granted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: cannot {self.access_type} this document",
            )

        return document


# Pre-configured document access checkers
require_document_view = DocumentAccessChecker("view")
require_document_edit = DocumentAccessChecker("edit")
require_document_delete = DocumentAccessChecker("delete")
require_document_publish = DocumentAccessChecker("publish")


async def get_document_if_accessible(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Document:
    """
    Dependency that returns a document if the user can view it.

    This is a convenience function for endpoints that need to
    fetch and verify document access in one step.

    Usage:
        @router.get("/documents/{document_id}")
        async def get_document(
            document: Document = Depends(get_document_if_accessible)
        ):
            return document
    """
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if not can_view_document(current_user, document):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you cannot view this document",
        )

    return document


def get_optional_current_user():
    """
    Dependency that returns the current user if authenticated, None otherwise.

    Useful for endpoints that work for both authenticated and anonymous users
    (like public document viewing).

    Usage:
        @router.get("/public/documents/{id}")
        async def get_public_doc(
            document_id: int,
            user: Optional[User] = Depends(get_optional_current_user),
            db: Session = Depends(get_db)
        ):
            ...
    """
    from app.security import oauth2_scheme

    async def dependency(
        token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)
    ) -> Optional[User]:
        if not token:
            return None

        try:
            from app.security import verify_token

            payload = verify_token(token)
            if payload is None:
                return None

            user_id = payload.get("sub")
            if user_id is None:
                return None

            user = db.query(User).filter(User.id == int(user_id)).first()
            if user and user.is_active:
                return user
            return None
        except Exception:
            return None

    return dependency
