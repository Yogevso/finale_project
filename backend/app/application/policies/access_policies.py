"""Central policy objects for document/review/invitation access decisions."""

from __future__ import annotations

import logging
from typing import Optional

from app.dependencies.tenant import TenantContext
from app.models import Document, DocumentStatus, DocumentVisibility, User, UserRole

logger = logging.getLogger(__name__)


def safe_user_role(user: Optional[User]) -> Optional[UserRole]:
    """Convert user.role to UserRole safely, returning None on invalid values."""
    if not user:
        return None
    if isinstance(user.role, UserRole):
        return user.role
    try:
        return UserRole(user.role)
    except (ValueError, KeyError):
        logger.error("Invalid role value %r for user %s — denying access", user.role, user.id)
        return None


class DocumentAccessPolicy:
    """Policy object for document access and tenant-boundary checks."""

    _TENANT_MANAGERS = {
        UserRole.SYSTEM_ADMIN,
        UserRole.ADMIN,
        UserRole.MANAGER,
    }

    @staticmethod
    def _role(user: Optional[User]) -> Optional[UserRole]:
        return safe_user_role(user)

    def is_internal_user(self, user: Optional[User]) -> bool:
        role = self._role(user)
        if role is None:
            return False
        return role != UserRole.CUSTOMER

    def _same_tenant_or_unscoped(self, user: User, document: Document) -> bool:
        role = self._role(user)
        if role == UserRole.SYSTEM_ADMIN:
            return True
        if not document.tenant_id or not user.tenant_id:
            return False
        return document.tenant_id == user.tenant_id

    def can_access_document_tenant(self, user: Optional[User], document: Document) -> bool:
        """Tenant-only boundary check (without permission/visibility rules)."""
        if not user:
            return False
        role = self._role(user)
        if role == UserRole.SYSTEM_ADMIN:
            return True
        return document.tenant_id == user.tenant_id

    def can_view_document(self, user: Optional[User], document: Document) -> bool:
        """Document read access, including anonymous access for public active docs."""
        if getattr(document, "deleted_at", None) is not None:
            return False
        if document.visibility == DocumentVisibility.PUBLIC:
            if document.status == DocumentStatus.ACTIVE:
                return True
            if user and self.is_internal_user(user):
                return True
            return False

        if not user or not user.is_active:
            return False

        if document.visibility == DocumentVisibility.INTERNAL:
            return self.is_internal_user(user)

        if document.visibility == DocumentVisibility.COMPANY:
            role = self._role(user)
            if self.is_internal_user(user):
                if role == UserRole.SYSTEM_ADMIN:
                    return True
                if user.tenant_id and document.tenant_id == user.tenant_id:
                    return True

            if role == UserRole.CUSTOMER and user.tenant_id:
                assigned_tenant_ids = [tenant.id for tenant in document.assigned_companies]
                return user.tenant_id in assigned_tenant_ids
            return False

        return False

    def can_edit_document(self, user: User, document: Document, has_edit_permission: bool) -> bool:
        if getattr(document, "deleted_at", None) is not None:
            return False
        if not user or not user.is_active or not has_edit_permission:
            return False
        role = self._role(user)
        if role in self._TENANT_MANAGERS:
            return self._same_tenant_or_unscoped(user, document)
        if role == UserRole.EDITOR:
            return self._same_tenant_or_unscoped(user, document) and user.id == document.created_by
        return False

    def can_delete_document(
        self, user: User, document: Document, has_delete_permission: bool
    ) -> bool:
        if getattr(document, "deleted_at", None) is not None:
            return False
        if not user or not user.is_active or not has_delete_permission:
            return False
        role = self._role(user)
        if role in self._TENANT_MANAGERS:
            return self._same_tenant_or_unscoped(user, document)
        if role == UserRole.EDITOR:
            return self._same_tenant_or_unscoped(user, document) and user.id == document.created_by
        return False

    def can_publish_document(
        self, user: User, document: Document, has_publish_permission: bool
    ) -> bool:
        if getattr(document, "deleted_at", None) is not None:
            return False
        if not user or not user.is_active or not has_publish_permission:
            return False
        return self._same_tenant_or_unscoped(user, document)

    def collaboration_tenant_boundary_allows(self, user: User, document: Document) -> bool:
        """Stricter tenant boundary applied for collaboration endpoints."""
        role = self._role(user)
        if role == UserRole.CUSTOMER:
            return True
        if not self.is_internal_user(user):
            return False
        if document.tenant_id is None or user.tenant_id is None:
            return False
        return user.tenant_id == document.tenant_id


class ReviewPolicy:
    """Policy object for review submission/approval permissions."""

    @staticmethod
    def _role(user: Optional[User]) -> Optional[UserRole]:
        return safe_user_role(user)

    def can_submit_for_review(self, user: Optional[User]) -> bool:
        role = self._role(user)
        return role in {
            UserRole.EDITOR,
            UserRole.MANAGER,
            UserRole.ADMIN,
            UserRole.SYSTEM_ADMIN,
        }

    def can_review_documents(self, user: Optional[User]) -> bool:
        return self.can_submit_for_review(user)

    def can_approve_review(
        self,
        reviewer: Optional[User],
        submitter: Optional[User],
        *,
        has_approve_permission: bool,
        has_peer_approve_permission: bool,
    ) -> bool:
        if not reviewer or not reviewer.is_active:
            return False

        if submitter and reviewer.id == submitter.id:
            return False

        if has_approve_permission:
            return True

        if has_peer_approve_permission and submitter:
            return self._role(submitter) == UserRole.EDITOR

        return False


class InvitationPolicy:
    """Policy object for invitation role and tenant assignment decisions."""

    @staticmethod
    def can_invite_role(inviter_role: UserRole, target_role: UserRole) -> bool:
        if inviter_role == UserRole.SYSTEM_ADMIN:
            return True
        if inviter_role == UserRole.ADMIN:
            return target_role != UserRole.SYSTEM_ADMIN
        if inviter_role == UserRole.MANAGER:
            return target_role in [UserRole.EDITOR, UserRole.VIEWER, UserRole.CUSTOMER]
        return False

    @staticmethod
    def can_manage_invitations(user: Optional[User]) -> bool:
        if not user or not user.is_active:
            return False
        role = safe_user_role(user)
        return role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.SYSTEM_ADMIN]

    @staticmethod
    def resolve_invitation_tenant_id(
        requested_tenant_id: Optional[int],
        tenant_ctx: TenantContext,
    ) -> Optional[int]:
        if tenant_ctx.is_system_admin:
            return requested_tenant_id

        if requested_tenant_id is None:
            return tenant_ctx.tenant_id

        if requested_tenant_id != tenant_ctx.tenant_id:
            return None
        return requested_tenant_id

    @staticmethod
    def can_access_invitation_tenant(
        invitation_tenant_id: Optional[int],
        tenant_ctx: TenantContext,
    ) -> bool:
        if tenant_ctx.is_system_admin:
            return True
        return invitation_tenant_id == tenant_ctx.tenant_id


# ---------------------------------------------------------------------------
# M-29: Extracted access policies for support, feedback, and analytics.
# These replace hand-rolled inline checks in the respective route files.
# ---------------------------------------------------------------------------


class SupportAccessPolicy:
    """Policy object for support ticket access decisions."""

    # Roles allowed to access the support module at all.
    _ALLOWED_ROLES = {
        UserRole.SYSTEM_ADMIN,
        UserRole.ADMIN,
        UserRole.MANAGER,
        UserRole.EDITOR,
        UserRole.VIEWER,
    }

    @staticmethod
    def _role(user: Optional[User]) -> Optional[UserRole]:
        return safe_user_role(user)

    def can_access_support(self, user: Optional[User]) -> bool:
        """Gate for basic support module access (replaces require_internal_user)."""
        if not user or not user.is_active:
            return False
        return self._role(user) in self._ALLOWED_ROLES

    def can_manage_ticket(self, user: User) -> bool:
        """Can assign agents, change priority, handoff."""
        role = self._role(user)
        return role in {UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER}

    def can_view_internal_notes(self, user: User) -> bool:
        """Internal notes are visible to internal staff only."""
        return self.can_access_support(user)


class FeedbackAccessPolicy:
    """Policy object for feedback access decisions.

    Centralises the contributor-based visibility rules that were previously
    hand-rolled in ``feedback.py``.
    """

    _MANAGEMENT_ROLES = {
        UserRole.SYSTEM_ADMIN,
        UserRole.ADMIN,
        UserRole.MANAGER,
    }
    _INTERNAL_ROLES = {
        UserRole.SYSTEM_ADMIN,
        UserRole.ADMIN,
        UserRole.MANAGER,
        UserRole.EDITOR,
        UserRole.VIEWER,
    }

    @staticmethod
    def _role(user: Optional[User]) -> Optional[UserRole]:
        return safe_user_role(user)

    def can_manage_feedback(self, user: Optional[User]) -> bool:
        """List / respond to feedback (replaces require_admin_or_manager)."""
        if not user or not user.is_active:
            return False
        return self._role(user) in self._MANAGEMENT_ROLES

    def can_update_status(self, user: Optional[User]) -> bool:
        """Update feedback status (replaces require_internal_staff)."""
        if not user or not user.is_active:
            return False
        return self._role(user) in self._INTERNAL_ROLES

    def can_view_feedback(
        self,
        user: User,
        feedback,
        contributor_ids: Optional[set] = None,
    ) -> bool:
        """Contributor-based visibility check.

        A user can view feedback if they are:
        - The feedback author,
        - A SYSTEM_ADMIN, or
        - An internal staff member who contributed to the related document.
        """
        if feedback.user_id == user.id:
            return True
        if self._role(user) == UserRole.SYSTEM_ADMIN:
            return True
        if self._role(user) in self._INTERNAL_ROLES and contributor_ids is not None:
            return user.id in contributor_ids
        return False

    def can_see_email(self, user: User) -> bool:
        """Only ADMIN+ may see the submitter email (PII protection)."""
        return self._role(user) in {UserRole.SYSTEM_ADMIN, UserRole.ADMIN}


class AnalyticsAccessPolicy:
    """Policy object for search analytics access decisions."""

    _ANALYTICS_ROLES = {
        UserRole.SYSTEM_ADMIN,
        UserRole.ADMIN,
        UserRole.MANAGER,
    }

    @staticmethod
    def _role(user: Optional[User]) -> Optional[UserRole]:
        return safe_user_role(user)

    def can_view_analytics(self, user: Optional[User]) -> bool:
        """Gate for the /search/analytics endpoint."""
        if not user or not user.is_active:
            return False
        return self._role(user) in self._ANALYTICS_ROLES

    def is_tenant_scoped(self, user: User) -> bool:
        """Non-SYSTEM_ADMIN users are scoped to their own tenant."""
        return self._role(user) != UserRole.SYSTEM_ADMIN
