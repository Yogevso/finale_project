"""Central Policy Decision Point (PDP) for authorization checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Sequence

from app.application.policies import DocumentAccessPolicy, InvitationPolicy, ReviewPolicy
from app.models import Document, User, UserRole

PermissionResolver = Callable[[UserRole], set[object]]


@dataclass(frozen=True)
class AuthorizationDecision:
    """Structured allow/deny response for authorization decisions."""

    allowed: bool
    action: str
    reason_code: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def allow(
        cls,
        action: str,
        *,
        reason_code: str = "granted",
        metadata: Optional[dict[str, Any]] = None,
    ) -> AuthorizationDecision:
        return cls(allowed=True, action=action, reason_code=reason_code, metadata=metadata or {})

    @classmethod
    def deny(
        cls,
        action: str,
        reason_code: str,
        *,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AuthorizationDecision:
        return cls(allowed=False, action=action, reason_code=reason_code, metadata=metadata or {})


def _value(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw)


class PolicyDecisionPoint:
    """Centralized policy decision logic across route and service layers."""

    def __init__(
        self,
        *,
        document_policy: DocumentAccessPolicy,
        review_policy: ReviewPolicy,
        invitation_policy: InvitationPolicy,
        permission_resolver: PermissionResolver,
    ) -> None:
        self._document_policy = document_policy
        self._review_policy = review_policy
        self._invitation_policy = invitation_policy
        self._permission_resolver = permission_resolver

    @staticmethod
    def _role(user: Optional[User]) -> Optional[UserRole]:
        if not user:
            return None
        try:
            if isinstance(user.role, UserRole):
                return user.role
            return UserRole(user.role)
        except ValueError:
            return None

    def _validate_user(self, user: Optional[User], action: str) -> tuple[Optional[UserRole], Optional[AuthorizationDecision]]:
        if user is None:
            return None, AuthorizationDecision.deny(action, "missing_subject")
        if not user.is_active:
            return None, AuthorizationDecision.deny(
                action,
                "inactive_subject",
                metadata={"user_id": user.id},
            )
        role = self._role(user)
        if role is None:
            return None, AuthorizationDecision.deny(
                action,
                "invalid_subject_role",
                metadata={"user_id": user.id},
            )
        return role, None

    def permission(self, user: Optional[User], permission: object) -> AuthorizationDecision:
        action = "permission"
        role, denied = self._validate_user(user, action)
        if denied:
            return denied

        assert role is not None
        allowed = permission in self._permission_resolver(role)
        permission_name = _value(permission)
        if allowed:
            return AuthorizationDecision.allow(
                action,
                metadata={"permission": permission_name, "role": role.value},
            )
        return AuthorizationDecision.deny(
            action,
            "missing_permission",
            metadata={"permission": permission_name, "role": role.value},
        )

    def any_permission(self, user: Optional[User], permissions: Sequence[object]) -> AuthorizationDecision:
        action = "any_permission"
        if not permissions:
            return AuthorizationDecision.deny(action, "missing_permissions")

        role, denied = self._validate_user(user, action)
        if denied:
            return denied

        assert role is not None
        granted = self._permission_resolver(role)
        matched = [permission for permission in permissions if permission in granted]
        if matched:
            return AuthorizationDecision.allow(
                action,
                metadata={
                    "matched_permissions": [_value(permission) for permission in matched],
                    "role": role.value,
                },
            )
        return AuthorizationDecision.deny(
            action,
            "missing_any_permission",
            metadata={
                "permissions": [_value(permission) for permission in permissions],
                "role": role.value,
            },
        )

    def role_membership(self, user: Optional[User], roles: Sequence[UserRole]) -> AuthorizationDecision:
        action = "role_membership"
        role, denied = self._validate_user(user, action)
        if denied:
            return denied

        assert role is not None
        if role in roles:
            return AuthorizationDecision.allow(
                action,
                metadata={"role": role.value, "allowed_roles": [entry.value for entry in roles]},
            )
        return AuthorizationDecision.deny(
            action,
            "role_not_allowed",
            metadata={"role": role.value, "allowed_roles": [entry.value for entry in roles]},
        )

    def internal_user(self, user: Optional[User]) -> AuthorizationDecision:
        action = "internal_user"
        role, denied = self._validate_user(user, action)
        if denied:
            return denied

        assert role is not None
        if self._document_policy.is_internal_user(user):
            return AuthorizationDecision.allow(action, metadata={"role": role.value})
        return AuthorizationDecision.deny(
            action,
            "internal_user_required",
            metadata={"role": role.value},
        )

    def customer_user(self, user: Optional[User]) -> AuthorizationDecision:
        action = "customer_user"
        role, denied = self._validate_user(user, action)
        if denied:
            return denied

        assert role is not None
        if role == UserRole.CUSTOMER:
            return AuthorizationDecision.allow(action, metadata={"role": role.value})
        return AuthorizationDecision.deny(
            action,
            "customer_user_required",
            metadata={"role": role.value},
        )

    def admin_or_above(self, user: Optional[User]) -> AuthorizationDecision:
        return self.role_membership(user, [UserRole.SYSTEM_ADMIN, UserRole.ADMIN])

    def manager_or_above(self, user: Optional[User]) -> AuthorizationDecision:
        return self.role_membership(
            user, [UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER]
        )

    def editor_or_above(self, user: Optional[User]) -> AuthorizationDecision:
        return self.role_membership(
            user, [UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER, UserRole.EDITOR]
        )

    def document_access(
        self,
        user: Optional[User],
        document: Optional[Document],
        *,
        access_type: str,
        edit_permission: object,
        delete_permission: object,
        publish_permission: object,
    ) -> AuthorizationDecision:
        action = f"document:{access_type}"
        if document is None:
            return AuthorizationDecision.deny(action, "document_missing")

        resolved_access = access_type if access_type in {"view", "edit", "delete", "publish"} else "view"
        if resolved_access == "view":
            allowed = self._document_policy.can_view_document(user, document)
            if allowed:
                return AuthorizationDecision.allow(action, metadata={"document_id": document.id})
            return AuthorizationDecision.deny(
                action,
                "document_view_denied",
                metadata={"document_id": document.id},
            )

        role, denied = self._validate_user(user, action)
        if denied:
            return denied
        assert role is not None

        permission_by_access = {
            "edit": edit_permission,
            "delete": delete_permission,
            "publish": publish_permission,
        }
        required_permission = permission_by_access[resolved_access]
        permission_decision = self.permission(user, required_permission)
        if not permission_decision.allowed:
            return AuthorizationDecision.deny(
                action,
                f"document_{resolved_access}_permission_denied",
                metadata={
                    "document_id": document.id,
                    "required_permission": _value(required_permission),
                    "permission_reason": permission_decision.reason_code,
                    "role": role.value,
                },
            )

        if resolved_access == "edit":
            allowed = self._document_policy.can_edit_document(
                user,
                document,
                has_edit_permission=True,
            )
        elif resolved_access == "delete":
            allowed = self._document_policy.can_delete_document(
                user,
                document,
                has_delete_permission=True,
            )
        else:
            allowed = self._document_policy.can_publish_document(
                user,
                document,
                has_publish_permission=True,
            )
        if allowed:
            return AuthorizationDecision.allow(action, metadata={"document_id": document.id})
        return AuthorizationDecision.deny(
            action,
            "document_tenant_boundary_denied",
            metadata={"document_id": document.id, "role": role.value},
        )

    def review_approval(
        self,
        reviewer: Optional[User],
        submitter: Optional[User],
        *,
        approve_permission: object,
        peer_approve_permission: object,
    ) -> AuthorizationDecision:
        action = "review_approval"

        role, denied = self._validate_user(reviewer, action)
        if denied:
            return denied
        assert role is not None

        approve_decision = self.permission(reviewer, approve_permission)
        peer_decision = self.permission(reviewer, peer_approve_permission)

        allowed = self._review_policy.can_approve_review(
            reviewer=reviewer,
            submitter=submitter,
            has_approve_permission=approve_decision.allowed,
            has_peer_approve_permission=peer_decision.allowed,
        )
        if allowed:
            return AuthorizationDecision.allow(action, metadata={"reviewer_role": role.value})

        if submitter and reviewer and submitter.id == reviewer.id:
            reason = "self_review_forbidden"
        elif not approve_decision.allowed and not peer_decision.allowed:
            reason = "missing_review_permission"
        else:
            reason = "review_policy_denied"
        return AuthorizationDecision.deny(
            action,
            reason,
            metadata={"reviewer_role": role.value},
        )

    def manage_user(
        self,
        current_user: Optional[User],
        *,
        target_user: Optional[User] = None,
        target_role: Optional[UserRole] = None,
    ) -> AuthorizationDecision:
        action = "manage_user"
        current_role, denied = self._validate_user(current_user, action)
        if denied:
            return denied
        assert current_role is not None

        role_to_check = target_role
        if role_to_check is None and target_user is not None:
            role_to_check = self._role(target_user)

        if current_role == UserRole.SYSTEM_ADMIN:
            return AuthorizationDecision.allow(action)

        if current_role == UserRole.ADMIN:
            if role_to_check in (UserRole.SYSTEM_ADMIN, UserRole.ADMIN):
                return AuthorizationDecision.deny(action, "target_role_not_manageable")
            return AuthorizationDecision.allow(action)

        if current_role == UserRole.MANAGER:
            if role_to_check in (UserRole.EDITOR, UserRole.VIEWER):
                return AuthorizationDecision.allow(action)
            return AuthorizationDecision.deny(action, "target_role_not_manageable")

        return AuthorizationDecision.deny(
            action,
            "role_not_allowed",
            metadata={"role": current_role.value},
        )

