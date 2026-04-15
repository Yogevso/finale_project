"""Tests for the central policy decision point service."""

from app.models import UserRole
from app.services.permissions import (
    Permission,
    evaluate_any_permission,
    evaluate_document_access,
    evaluate_manage_user,
    evaluate_permission,
    get_policy_decision_point,
)


def test_get_policy_decision_point_returns_singleton():
    first = get_policy_decision_point()
    second = get_policy_decision_point()

    assert first is second


def test_permission_decision_denied_includes_reason_code(db, test_viewer):
    decision = evaluate_permission(test_viewer, Permission.DELETE_DOCUMENT)

    assert decision.allowed is False
    assert decision.action == "permission"
    assert decision.reason_code == "missing_permission"
    assert decision.metadata["permission"] == Permission.DELETE_DOCUMENT.value


def test_any_permission_decision_reports_match(db, test_viewer):
    decision = evaluate_any_permission(
        test_viewer,
        [Permission.MANAGE_USERS, Permission.VIEW_PUBLIC_DOCS],
    )

    assert decision.allowed is True
    assert decision.action == "any_permission"
    assert Permission.VIEW_PUBLIC_DOCS.value in decision.metadata["matched_permissions"]


def test_document_publish_denied_for_editor_has_specific_reason(db, test_user, public_document):
    decision = evaluate_document_access(test_user, public_document, "publish")

    assert decision.allowed is False
    assert decision.reason_code == "document_publish_permission_denied"


def test_document_access_unknown_type_falls_back_to_view(db, test_viewer, public_document):
    decision = evaluate_document_access(test_viewer, public_document, "unknown")

    assert decision.allowed is True
    assert decision.action == "document:unknown"


def test_manage_user_decision_enforces_role_boundaries(db, test_manager):
    decision = evaluate_manage_user(test_manager, target_role=UserRole.ADMIN)

    assert decision.allowed is False
    assert decision.reason_code == "target_role_not_manageable"
