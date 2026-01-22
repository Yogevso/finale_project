"""
Permission System for Customer Portal

This module defines all permissions and role-based access control
for the document portal system.
"""

from enum import Enum
from typing import Optional, Set

from app.models import Document, DocumentVisibility, User, UserRole


class Permission(str, Enum):
    """All available permissions in the system"""

    # Document viewing
    VIEW_PUBLIC_DOCS = "view_public_docs"
    VIEW_INTERNAL_DOCS = "view_internal_docs"
    VIEW_COMPANY_DOCS = "view_company_docs"

    # Document management
    CREATE_DOCUMENT = "create_document"
    EDIT_DOCUMENT = "edit_document"
    DELETE_DOCUMENT = "delete_document"

    # Review workflow
    SUBMIT_REVIEW = "submit_review"
    APPROVE_REVIEW = "approve_review"
    APPROVE_PEER_REVIEW = "approve_peer_review"  # Editors can review other editors

    # Publishing
    PUBLISH_DOCUMENT = "publish_document"
    ASSIGN_COMPANIES = "assign_companies"

    # Collaboration
    ADD_COMMENTS = "add_comments"
    SUBMIT_FEEDBACK = "submit_feedback"
    DOWNLOAD_ATTACHMENTS = "download_attachments"

    # User management
    MANAGE_USERS = "manage_users"
    MANAGE_EDITORS = "manage_editors"  # Managers can create editors

    # Admin
    MANAGE_COMPANIES = "manage_companies"
    SYSTEM_SETTINGS = "system_settings"
    MANAGE_ADMINS = "manage_admins"


# Permission matrix: maps each role to its set of permissions
ROLE_PERMISSIONS: dict[UserRole, Set[Permission]] = {
    UserRole.SYSTEM_ADMIN: {
        Permission.VIEW_PUBLIC_DOCS,
        Permission.VIEW_INTERNAL_DOCS,
        Permission.VIEW_COMPANY_DOCS,
        Permission.CREATE_DOCUMENT,
        Permission.EDIT_DOCUMENT,
        Permission.DELETE_DOCUMENT,
        Permission.SUBMIT_REVIEW,
        Permission.APPROVE_REVIEW,
        Permission.APPROVE_PEER_REVIEW,
        Permission.PUBLISH_DOCUMENT,
        Permission.ASSIGN_COMPANIES,
        Permission.ADD_COMMENTS,
        Permission.SUBMIT_FEEDBACK,
        Permission.DOWNLOAD_ATTACHMENTS,
        Permission.MANAGE_USERS,
        Permission.MANAGE_EDITORS,
        Permission.MANAGE_COMPANIES,
        Permission.SYSTEM_SETTINGS,
        Permission.MANAGE_ADMINS,
    },
    UserRole.ADMIN: {
        Permission.VIEW_PUBLIC_DOCS,
        Permission.VIEW_INTERNAL_DOCS,
        Permission.VIEW_COMPANY_DOCS,
        Permission.CREATE_DOCUMENT,
        Permission.EDIT_DOCUMENT,
        Permission.DELETE_DOCUMENT,
        Permission.SUBMIT_REVIEW,
        Permission.APPROVE_REVIEW,
        Permission.APPROVE_PEER_REVIEW,
        Permission.PUBLISH_DOCUMENT,
        Permission.ASSIGN_COMPANIES,
        Permission.ADD_COMMENTS,
        Permission.SUBMIT_FEEDBACK,
        Permission.DOWNLOAD_ATTACHMENTS,
        Permission.MANAGE_USERS,
        Permission.MANAGE_EDITORS,
        Permission.MANAGE_COMPANIES,
        Permission.SYSTEM_SETTINGS,
        # Note: Cannot MANAGE_ADMINS
    },
    UserRole.MANAGER: {
        Permission.VIEW_PUBLIC_DOCS,
        Permission.VIEW_INTERNAL_DOCS,
        Permission.VIEW_COMPANY_DOCS,
        Permission.CREATE_DOCUMENT,
        Permission.EDIT_DOCUMENT,
        Permission.DELETE_DOCUMENT,
        Permission.SUBMIT_REVIEW,
        Permission.APPROVE_REVIEW,
        Permission.APPROVE_PEER_REVIEW,
        Permission.PUBLISH_DOCUMENT,
        Permission.ASSIGN_COMPANIES,
        Permission.ADD_COMMENTS,
        Permission.SUBMIT_FEEDBACK,
        Permission.DOWNLOAD_ATTACHMENTS,
        Permission.MANAGE_EDITORS,  # Can manage editors only
        # Note: Cannot MANAGE_USERS (full), MANAGE_COMPANIES, SYSTEM_SETTINGS
    },
    UserRole.EDITOR: {
        Permission.VIEW_PUBLIC_DOCS,
        Permission.VIEW_INTERNAL_DOCS,
        Permission.VIEW_COMPANY_DOCS,
        Permission.CREATE_DOCUMENT,
        Permission.EDIT_DOCUMENT,
        # Note: Cannot DELETE_DOCUMENT
        Permission.SUBMIT_REVIEW,
        Permission.APPROVE_PEER_REVIEW,  # Can review other editors' work
        # Note: Cannot APPROVE_REVIEW (manager level), PUBLISH_DOCUMENT
        Permission.ADD_COMMENTS,
        Permission.SUBMIT_FEEDBACK,
        Permission.DOWNLOAD_ATTACHMENTS,
    },
    UserRole.VIEWER: {
        Permission.VIEW_PUBLIC_DOCS,
        Permission.VIEW_INTERNAL_DOCS,
        Permission.VIEW_COMPANY_DOCS,
        Permission.ADD_COMMENTS,
        Permission.SUBMIT_FEEDBACK,
        Permission.DOWNLOAD_ATTACHMENTS,
    },
    UserRole.CUSTOMER: {
        Permission.VIEW_PUBLIC_DOCS,
        Permission.VIEW_COMPANY_DOCS,  # Own company only
        Permission.SUBMIT_FEEDBACK,
        Permission.DOWNLOAD_ATTACHMENTS,
        # Note: Cannot VIEW_INTERNAL_DOCS, ADD_COMMENTS
    },
}


def has_permission(user: User, permission: Permission) -> bool:
    """
    Check if a user has a specific permission.

    Args:
        user: The user to check
        permission: The permission to verify

    Returns:
        True if user has the permission, False otherwise
    """
    if not user or not user.is_active:
        return False

    user_permissions = ROLE_PERMISSIONS.get(user.role, set())
    return permission in user_permissions


def get_user_permissions(user: User) -> Set[Permission]:
    """
    Get all permissions for a user.

    Args:
        user: The user to get permissions for

    Returns:
        Set of permissions the user has
    """
    if not user or not user.is_active:
        return set()

    return ROLE_PERMISSIONS.get(user.role, set())


def is_internal_user(user: User) -> bool:
    """
    Check if a user is an internal staff member (not a customer).

    Args:
        user: The user to check

    Returns:
        True if user is internal staff, False if customer or invalid
    """
    if not user:
        return False

    return user.role != UserRole.CUSTOMER


def is_admin_or_above(user: User) -> bool:
    """
    Check if user is admin or system_admin.

    Args:
        user: The user to check

    Returns:
        True if user is admin or system_admin
    """
    if not user:
        return False

    return user.role in (UserRole.SYSTEM_ADMIN, UserRole.ADMIN)


def is_manager_or_above(user: User) -> bool:
    """
    Check if user is manager, admin, or system_admin.

    Args:
        user: The user to check

    Returns:
        True if user is manager or above
    """
    if not user:
        return False

    return user.role in (UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER)


def is_editor_or_above(user: User) -> bool:
    """
    Check if user is editor, manager, admin, or system_admin.

    Args:
        user: The user to check

    Returns:
        True if user is editor or above
    """
    if not user:
        return False

    return user.role in (UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER, UserRole.EDITOR)


def can_view_document(user: Optional[User], document: Document) -> bool:
    """
    Check if a user can view a specific document.

    Rules:
    - PUBLIC docs: Anyone can view (user can be None)
    - INTERNAL docs: Only internal users (not customers)
    - COMPANY docs: Internal users OR customers belonging to an assigned company

    Args:
        user: The user trying to view (can be None for anonymous)
        document: The document to check access for

    Returns:
        True if user can view the document
    """
    # PUBLIC documents can be viewed by anyone
    if document.visibility == DocumentVisibility.PUBLIC:
        # But document must also be ACTIVE (published)
        from app.models import DocumentStatus

        if document.status == DocumentStatus.ACTIVE:
            return True
        # If not active, only internal users can see drafts
        if user and is_internal_user(user):
            return True
        return False

    # For INTERNAL and COMPANY, user must be logged in
    if not user:
        return False

    # Check if user is active
    if not user.is_active:
        return False

    # INTERNAL documents: only internal staff
    if document.visibility == DocumentVisibility.INTERNAL:
        return is_internal_user(user)

    # COMPANY documents: internal staff OR customers from assigned companies
    if document.visibility == DocumentVisibility.COMPANY:
        # Internal users can always view company docs
        if is_internal_user(user):
            return True

        # Customers can view if their company is assigned
        if user.role == UserRole.CUSTOMER and user.tenant_id:
            # Check if user's tenant is in assigned companies
            assigned_tenant_ids = [t.id for t in document.assigned_companies]
            return user.tenant_id in assigned_tenant_ids

        return False

    # Default deny
    return False


def can_edit_document(user: User, document: Document) -> bool:
    """
    Check if a user can edit a specific document.

    Args:
        user: The user trying to edit
        document: The document to check access for

    Returns:
        True if user can edit the document
    """
    if not user or not user.is_active:
        return False

    # Must have edit permission
    if not has_permission(user, Permission.EDIT_DOCUMENT):
        return False

    # For multi-tenant: check if user belongs to same tenant or is super admin
    if user.role == UserRole.SYSTEM_ADMIN:
        return True  # System admin can edit any document

    # Other users can only edit documents in their tenant
    if document.tenant_id and user.tenant_id:
        return document.tenant_id == user.tenant_id

    # If no tenant restriction, allow edit
    return True


def can_delete_document(user: User, document: Document) -> bool:
    """
    Check if a user can delete a specific document.

    Args:
        user: The user trying to delete
        document: The document to check access for

    Returns:
        True if user can delete the document
    """
    if not user or not user.is_active:
        return False

    # Must have delete permission (admin, manager, or above)
    if not has_permission(user, Permission.DELETE_DOCUMENT):
        return False

    # For multi-tenant: check tenant restriction
    if user.role == UserRole.SYSTEM_ADMIN:
        return True  # System admin can delete any document

    if document.tenant_id and user.tenant_id:
        return document.tenant_id == user.tenant_id

    return True


def can_publish_document(user: User, document: Document) -> bool:
    """
    Check if a user can publish a specific document.

    Args:
        user: The user trying to publish
        document: The document to check access for

    Returns:
        True if user can publish the document
    """
    if not user or not user.is_active:
        return False

    # Must have publish permission
    if not has_permission(user, Permission.PUBLISH_DOCUMENT):
        return False

    # Tenant check
    if user.role == UserRole.SYSTEM_ADMIN:
        return True

    if document.tenant_id and user.tenant_id:
        return document.tenant_id == user.tenant_id

    return True


def can_review_document(user: User, document: Document, submitter: User) -> bool:
    """
    Check if a user can review (approve/reject) a document.

    Rules:
    - Cannot review own submissions
    - Managers/Admins can review any submission
    - Editors can peer-review other editors' submissions

    Args:
        user: The user trying to review
        document: The document being reviewed
        submitter: The user who submitted for review

    Returns:
        True if user can review the document
    """
    if not user or not user.is_active:
        return False

    # Cannot review own submission
    if user.id == submitter.id:
        return False

    # Managers and above can review anyone
    if has_permission(user, Permission.APPROVE_REVIEW):
        return True

    # Editors can peer-review other editors
    if has_permission(user, Permission.APPROVE_PEER_REVIEW):
        # Only if submitter is also an editor (not manager/admin)
        if submitter.role == UserRole.EDITOR:
            return True

    return False


def can_manage_user(
    current_user: User, target_user: Optional[User] = None, target_role: Optional[UserRole] = None
) -> bool:
    """
    Check if current user can manage (create/edit/delete) another user.

    Rules:
    - System admins can manage anyone
    - Admins can manage non-admin users
    - Managers can only manage editors and viewers

    Args:
        current_user: The user performing the action
        target_user: The user being managed (optional)
        target_role: The role being assigned (optional)

    Returns:
        True if current_user can manage the target
    """
    if not current_user or not current_user.is_active:
        return False

    role_to_check = target_role if target_role else (target_user.role if target_user else None)

    if current_user.role == UserRole.SYSTEM_ADMIN:
        return True  # Can manage anyone

    if current_user.role == UserRole.ADMIN:
        # Cannot manage system_admins or other admins
        if role_to_check in (UserRole.SYSTEM_ADMIN, UserRole.ADMIN):
            return False
        return True

    if current_user.role == UserRole.MANAGER:
        # Can only manage editors and viewers
        if role_to_check in (UserRole.EDITOR, UserRole.VIEWER):
            return True
        return False

    return False
