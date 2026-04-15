"""
Permission System for Customer Portal

This module defines all permissions and role-based access control
for the document portal system.
"""

from enum import Enum
from typing import Optional, Sequence, Set

from app.application.policies import (
    DocumentAccessPolicy,
    InvitationPolicy,
    ReviewPolicy,
)
from app.domain.capabilities import (
    AnyPermissionCapability,
    CanAssignCompanies,
    CanPublish,
    CustomerUserCapability,
    DocumentAccessCapability,
    InternalUserCapability,
    ManageUserCapability,
    PermissionCapability,
    ReviewApprovalCapability,
    RoleCapability,
)
from app.models import Document, User, UserRole
from app.policy import AuthorizationDecision, PolicyDecisionPoint


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


# Dynamic RBAC policies (published by CMS/ACL)
_DYNAMIC_ROLE_PERMISSIONS: dict[UserRole, Set[Permission]] = {}
_DOCUMENT_ACCESS_POLICY = DocumentAccessPolicy()
_REVIEW_POLICY = ReviewPolicy()
_INVITATION_POLICY = InvitationPolicy()


def set_dynamic_role_permissions(role_permissions: dict[UserRole, Set[Permission]]) -> None:
    """Replace dynamic RBAC policies in memory."""
    global _DYNAMIC_ROLE_PERMISSIONS
    _DYNAMIC_ROLE_PERMISSIONS = {
        role: set(permissions) for role, permissions in role_permissions.items()
    }


def clear_dynamic_role_permissions() -> None:
    """Clear dynamic RBAC policies, falling back to static defaults."""
    _DYNAMIC_ROLE_PERMISSIONS.clear()


def _effective_permissions(role: UserRole) -> Set[Permission]:
    dynamic_permissions = _DYNAMIC_ROLE_PERMISSIONS.get(role)
    if dynamic_permissions is not None:
        # An explicit dynamic empty set is deny-all for that role.
        return dynamic_permissions
    return ROLE_PERMISSIONS.get(role, set())


_PDP = PolicyDecisionPoint(
    document_policy=_DOCUMENT_ACCESS_POLICY,
    review_policy=_REVIEW_POLICY,
    invitation_policy=_INVITATION_POLICY,
    permission_resolver=_effective_permissions,
)


def _permission_capability_name(permission: Permission) -> str:
    return "Can" + "".join(part.capitalize() for part in permission.value.split("_"))


def _build_permission_capability(permission: Permission) -> PermissionCapability:
    if permission == Permission.PUBLISH_DOCUMENT:
        return CanPublish(permission)
    if permission == Permission.ASSIGN_COMPANIES:
        return CanAssignCompanies(permission)
    return PermissionCapability(
        name=_permission_capability_name(permission),
        permission=permission,
    )


_PERMISSION_CAPABILITIES: dict[Permission, PermissionCapability] = {
    permission: _build_permission_capability(permission) for permission in Permission
}


def _with_capability_metadata(
    decision: AuthorizationDecision, capability_name: str
) -> AuthorizationDecision:
    metadata = dict(decision.metadata)
    metadata.setdefault("capability", capability_name)
    return AuthorizationDecision(
        allowed=decision.allowed,
        action=decision.action,
        reason_code=decision.reason_code,
        metadata=metadata,
    )


def resolve_permission_capability(permission: Permission) -> PermissionCapability:
    """Resolve a permission to a reusable capability object."""
    return _PERMISSION_CAPABILITIES[permission]


def evaluate_permission_capability(
    user: Optional[User], capability: PermissionCapability
) -> AuthorizationDecision:
    """Evaluate a single-permission capability."""
    decision = _PDP.permission(user, capability.permission)
    return _with_capability_metadata(decision, capability.name)


def get_policy_decision_point() -> PolicyDecisionPoint:
    """Get the shared policy decision point instance."""
    return _PDP


def evaluate_permission(user: Optional[User], permission: Permission) -> AuthorizationDecision:
    """Return structured permission decision for user/permission pair."""
    return evaluate_permission_capability(user, resolve_permission_capability(permission))


def evaluate_any_permission(
    user: Optional[User], permissions: Sequence[Permission]
) -> AuthorizationDecision:
    """Return structured decision for "any of these permissions" checks."""
    capability = AnyPermissionCapability(
        name="CanAnyPermission",
        permissions=tuple(permissions),
    )
    decision = _PDP.any_permission(user, capability.permissions)
    return _with_capability_metadata(decision, capability.name)


def evaluate_role_membership(
    user: Optional[User], roles: Sequence[UserRole]
) -> AuthorizationDecision:
    """Return structured decision for role membership checks."""
    capability = RoleCapability(
        name="CanMatchRoleMembership",
        roles=tuple(roles),
    )
    decision = _PDP.role_membership(user, capability.roles)
    return _with_capability_metadata(decision, capability.name)


def evaluate_internal_user(user: Optional[User]) -> AuthorizationDecision:
    """Return structured decision for internal-user gate checks."""
    capability = InternalUserCapability()
    decision = _PDP.internal_user(user)
    return _with_capability_metadata(decision, capability.name)


def evaluate_customer(user: Optional[User]) -> AuthorizationDecision:
    """Return structured decision for customer-only gate checks."""
    capability = CustomerUserCapability()
    decision = _PDP.customer_user(user)
    return _with_capability_metadata(decision, capability.name)


def evaluate_admin_or_above(user: Optional[User]) -> AuthorizationDecision:
    """Return structured decision for admin-or-above checks."""
    capability = RoleCapability(
        name="CanAdminOrAbove",
        roles=(UserRole.SYSTEM_ADMIN, UserRole.ADMIN),
    )
    decision = _PDP.role_membership(user, capability.roles)
    return _with_capability_metadata(decision, capability.name)


def evaluate_manager_or_above(user: Optional[User]) -> AuthorizationDecision:
    """Return structured decision for manager-or-above checks."""
    capability = RoleCapability(
        name="CanManagerOrAbove",
        roles=(UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER),
    )
    decision = _PDP.role_membership(user, capability.roles)
    return _with_capability_metadata(decision, capability.name)


def evaluate_editor_or_above(user: Optional[User]) -> AuthorizationDecision:
    """Return structured decision for editor-or-above checks."""
    capability = RoleCapability(
        name="CanEditorOrAbove",
        roles=(UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER, UserRole.EDITOR),
    )
    decision = _PDP.role_membership(user, capability.roles)
    return _with_capability_metadata(decision, capability.name)


def evaluate_document_access(
    user: Optional[User], document: Optional[Document], access_type: str
) -> AuthorizationDecision:
    """Return structured decision for document view/edit/delete/publish gates."""
    normalized_access_type = (
        access_type if access_type in {"view", "edit", "delete", "publish"} else "view"
    )
    capability_name = {
        "view": "CanViewDocument",
        "edit": "CanEditDocument",
        "delete": "CanDeleteDocument",
        "publish": "CanPublishDocument",
    }[normalized_access_type]
    capability = DocumentAccessCapability(
        name=capability_name,
        access_type=access_type,
        edit_permission=Permission.EDIT_DOCUMENT,
        delete_permission=Permission.DELETE_DOCUMENT,
        publish_permission=Permission.PUBLISH_DOCUMENT,
    )
    decision = _PDP.document_access(
        user,
        document,
        access_type=capability.access_type,
        edit_permission=capability.edit_permission,
        delete_permission=capability.delete_permission,
        publish_permission=capability.publish_permission,
    )
    return _with_capability_metadata(decision, capability.name)


def evaluate_review_approval(
    user: Optional[User], submitter: Optional[User]
) -> AuthorizationDecision:
    """Return structured decision for review-approval checks."""
    capability = ReviewApprovalCapability(
        name="CanApproveReview",
        approve_permission=Permission.APPROVE_REVIEW,
        peer_approve_permission=Permission.APPROVE_PEER_REVIEW,
    )
    decision = _PDP.review_approval(
        reviewer=user,
        submitter=submitter,
        approve_permission=capability.approve_permission,
        peer_approve_permission=capability.peer_approve_permission,
    )
    return _with_capability_metadata(decision, capability.name)


def evaluate_manage_user(
    current_user: Optional[User],
    target_user: Optional[User] = None,
    target_role: Optional[UserRole] = None,
) -> AuthorizationDecision:
    """Return structured decision for user-management checks."""
    capability = ManageUserCapability()
    decision = _PDP.manage_user(
        current_user,
        target_user=target_user,
        target_role=target_role,
    )
    return _with_capability_metadata(decision, capability.name)


def has_permission(user: User, permission: Permission) -> bool:
    """
    Check if a user has a specific permission.

    Args:
        user: The user to check
        permission: The permission to verify

    Returns:
        True if user has the permission, False otherwise
    """
    return evaluate_permission(user, permission).allowed


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

    return _effective_permissions(user.role)


def is_internal_user(user: User) -> bool:
    """
    Check if a user is an internal staff member (not a customer).

    Args:
        user: The user to check

    Returns:
        True if user is internal staff, False if customer or invalid
    """
    return evaluate_internal_user(user).allowed


def is_admin_or_above(user: User) -> bool:
    """
    Check if user is admin or system_admin.

    Args:
        user: The user to check

    Returns:
        True if user is admin or system_admin
    """
    return evaluate_admin_or_above(user).allowed


def is_manager_or_above(user: User) -> bool:
    """
    Check if user is manager, admin, or system_admin.

    Args:
        user: The user to check

    Returns:
        True if user is manager or above
    """
    return evaluate_manager_or_above(user).allowed


def is_editor_or_above(user: User) -> bool:
    """
    Check if user is editor, manager, admin, or system_admin.

    Args:
        user: The user to check

    Returns:
        True if user is editor or above
    """
    return evaluate_editor_or_above(user).allowed


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
    return evaluate_document_access(user, document, "view").allowed


def can_edit_document(user: User, document: Document) -> bool:
    """
    Check if a user can edit a specific document.

    Args:
        user: The user trying to edit
        document: The document to check access for

    Returns:
        True if user can edit the document
    """
    return evaluate_document_access(user, document, "edit").allowed


def can_delete_document(user: User, document: Document) -> bool:
    """
    Check if a user can delete a specific document.

    Args:
        user: The user trying to delete
        document: The document to check access for

    Returns:
        True if user can delete the document
    """
    return evaluate_document_access(user, document, "delete").allowed


def can_publish_document(user: User, document: Document) -> bool:
    """
    Check if a user can publish a specific document.

    Args:
        user: The user trying to publish
        document: The document to check access for

    Returns:
        True if user can publish the document
    """
    return evaluate_document_access(user, document, "publish").allowed


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
    return evaluate_review_approval(user, submitter).allowed


def get_document_access_policy() -> DocumentAccessPolicy:
    """Get the shared document access policy instance."""
    return _DOCUMENT_ACCESS_POLICY


def get_review_policy() -> ReviewPolicy:
    """Get the shared review policy instance."""
    return _REVIEW_POLICY


def get_invitation_policy() -> InvitationPolicy:
    """Get the shared invitation policy instance."""
    return _INVITATION_POLICY


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
    return evaluate_manage_user(current_user, target_user, target_role).allowed
