"""M-29: RBAC test matrix for support, feedback, and analytics policies.

Tests every role against each policy method to ensure the access-control matrix
is enforced correctly.  This prevents regressions when route-level auth is
refactored.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.application.policies.access_policies import (
    AnalyticsAccessPolicy,
    FeedbackAccessPolicy,
    SupportAccessPolicy,
)
from app.models import UserRole


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user(role: UserRole, *, user_id: int = 1, is_active: bool = True, tenant_id: int = 1):
    """Create a minimal user-like object accepted by the policies."""
    return SimpleNamespace(
        id=user_id,
        role=role,
        is_active=is_active,
        tenant_id=tenant_id,
    )


ALL_ROLES = [
    UserRole.SYSTEM_ADMIN,
    UserRole.ADMIN,
    UserRole.MANAGER,
    UserRole.EDITOR,
    UserRole.VIEWER,
    UserRole.CUSTOMER,
]

# ---------------------------------------------------------------------------
# SupportAccessPolicy
# ---------------------------------------------------------------------------

_support = SupportAccessPolicy()


class TestSupportAccessPolicy:
    @pytest.mark.parametrize(
        "role,expected",
        [
            (UserRole.SYSTEM_ADMIN, True),
            (UserRole.ADMIN, True),
            (UserRole.MANAGER, True),
            (UserRole.EDITOR, True),
            (UserRole.VIEWER, True),
            (UserRole.CUSTOMER, False),
        ],
    )
    def test_can_access_support(self, role, expected):
        assert _support.can_access_support(_user(role)) is expected

    @pytest.mark.parametrize(
        "role,expected",
        [
            (UserRole.SYSTEM_ADMIN, True),
            (UserRole.ADMIN, True),
            (UserRole.MANAGER, True),
            (UserRole.EDITOR, False),
            (UserRole.VIEWER, False),
            (UserRole.CUSTOMER, False),
        ],
    )
    def test_can_manage_ticket(self, role, expected):
        assert _support.can_manage_ticket(_user(role)) is expected

    def test_inactive_user_denied(self):
        assert _support.can_access_support(_user(UserRole.ADMIN, is_active=False)) is False

    def test_none_user_denied(self):
        assert _support.can_access_support(None) is False


# ---------------------------------------------------------------------------
# FeedbackAccessPolicy
# ---------------------------------------------------------------------------

_feedback = FeedbackAccessPolicy()


class TestFeedbackAccessPolicy:
    @pytest.mark.parametrize(
        "role,expected",
        [
            (UserRole.SYSTEM_ADMIN, True),
            (UserRole.ADMIN, True),
            (UserRole.MANAGER, True),
            (UserRole.EDITOR, False),
            (UserRole.VIEWER, False),
            (UserRole.CUSTOMER, False),
        ],
    )
    def test_can_manage_feedback(self, role, expected):
        assert _feedback.can_manage_feedback(_user(role)) is expected

    @pytest.mark.parametrize(
        "role,expected",
        [
            (UserRole.SYSTEM_ADMIN, True),
            (UserRole.ADMIN, True),
            (UserRole.MANAGER, True),
            (UserRole.EDITOR, True),
            (UserRole.VIEWER, True),
            (UserRole.CUSTOMER, False),
        ],
    )
    def test_can_update_status(self, role, expected):
        assert _feedback.can_update_status(_user(role)) is expected

    def test_author_can_always_view(self):
        fb = SimpleNamespace(user_id=42, document_id=1)
        assert _feedback.can_view_feedback(_user(UserRole.CUSTOMER, user_id=42), fb) is True

    def test_system_admin_can_always_view(self):
        fb = SimpleNamespace(user_id=99, document_id=1)
        assert _feedback.can_view_feedback(_user(UserRole.SYSTEM_ADMIN, user_id=1), fb) is True

    def test_contributor_can_view(self):
        fb = SimpleNamespace(user_id=99, document_id=1)
        user = _user(UserRole.EDITOR, user_id=5)
        assert _feedback.can_view_feedback(user, fb, contributor_ids={5, 10}) is True

    def test_non_contributor_cannot_view(self):
        fb = SimpleNamespace(user_id=99, document_id=1)
        user = _user(UserRole.EDITOR, user_id=5)
        assert _feedback.can_view_feedback(user, fb, contributor_ids={10, 20}) is False

    @pytest.mark.parametrize(
        "role,expected",
        [
            (UserRole.SYSTEM_ADMIN, True),
            (UserRole.ADMIN, True),
            (UserRole.MANAGER, False),
            (UserRole.EDITOR, False),
            (UserRole.VIEWER, False),
            (UserRole.CUSTOMER, False),
        ],
    )
    def test_can_see_email(self, role, expected):
        assert _feedback.can_see_email(_user(role)) is expected

    def test_inactive_user_denied(self):
        assert _feedback.can_manage_feedback(_user(UserRole.ADMIN, is_active=False)) is False


# ---------------------------------------------------------------------------
# AnalyticsAccessPolicy
# ---------------------------------------------------------------------------

_analytics = AnalyticsAccessPolicy()


class TestAnalyticsAccessPolicy:
    @pytest.mark.parametrize(
        "role,expected",
        [
            (UserRole.SYSTEM_ADMIN, True),
            (UserRole.ADMIN, True),
            (UserRole.MANAGER, True),
            (UserRole.EDITOR, False),
            (UserRole.VIEWER, False),
            (UserRole.CUSTOMER, False),
        ],
    )
    def test_can_view_analytics(self, role, expected):
        assert _analytics.can_view_analytics(_user(role)) is expected

    @pytest.mark.parametrize(
        "role,expected",
        [
            (UserRole.SYSTEM_ADMIN, False),
            (UserRole.ADMIN, True),
            (UserRole.MANAGER, True),
        ],
    )
    def test_is_tenant_scoped(self, role, expected):
        assert _analytics.is_tenant_scoped(_user(role)) is expected

    def test_inactive_user_denied(self):
        assert _analytics.can_view_analytics(_user(UserRole.ADMIN, is_active=False)) is False

    def test_none_user_denied(self):
        assert _analytics.can_view_analytics(None) is False
