"""Tests for policy explanation objects."""

import asyncio

import pytest
from fastapi import HTTPException

from app.dependencies.permissions import DocumentAccessChecker, require_manager, require_permission
from app.models import UserRole
from app.policy import explain_decision
from app.services.permissions import (
    Permission,
    evaluate_manage_user,
    evaluate_permission,
    evaluate_role_membership,
)


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_explain_decision_includes_stable_reason_code(db, test_viewer):
    decision = evaluate_permission(test_viewer, Permission.DELETE_DOCUMENT)
    explanation = explain_decision(decision, summary="Permission denied: delete_document")

    assert explanation.reason_code == "missing_permission"
    assert "reason_code=missing_permission" in explanation.message
    assert explanation.to_http_headers()["X-Policy-Reason"] == "missing_permission"


def test_explain_decision_handles_role_denial(db, test_viewer):
    decision = evaluate_role_membership(test_viewer, [UserRole.SYSTEM_ADMIN, UserRole.ADMIN])
    explanation = explain_decision(decision, summary="Access denied: admin privileges required")

    assert explanation.reason_code == "role_not_allowed"
    assert explanation.reason_description == "The subject role is not allowed for this action"
    assert explanation.to_http_headers()["X-Policy-Action"] == "role_membership"


def test_explain_decision_manage_user_denial_has_context(db, test_manager):
    decision = evaluate_manage_user(test_manager, target_role=UserRole.ADMIN)
    explanation = explain_decision(decision, summary="Access denied: cannot manage target role")
    log_context = explanation.to_log_context()

    assert explanation.reason_code == "target_role_not_manageable"
    assert log_context["policy_reason_code"] == "target_role_not_manageable"
    assert log_context["policy_action"] == "manage_user"


def test_permission_dependency_denial_exposes_policy_reason_header(db, test_viewer):
    dependency = require_permission(Permission.DELETE_DOCUMENT)

    with pytest.raises(HTTPException) as exc_info:
        run_async(dependency(current_user=test_viewer))

    assert exc_info.value.headers["X-Policy-Reason"] == "missing_permission"
    assert exc_info.value.headers["X-Policy-Action"] == "permission"
    assert "reason_code=missing_permission" in exc_info.value.detail


def test_role_dependency_denial_exposes_policy_reason_header(db, test_user):
    with pytest.raises(HTTPException) as exc_info:
        run_async(require_manager(current_user=test_user))

    assert exc_info.value.headers["X-Policy-Reason"] == "role_not_allowed"
    assert exc_info.value.headers["X-Policy-Action"] == "role_membership"
    assert "reason_code=role_not_allowed" in exc_info.value.detail


def test_document_access_denial_exposes_policy_reason_header(db, test_viewer, public_document):
    checker = DocumentAccessChecker("edit")

    with pytest.raises(HTTPException) as exc_info:
        run_async(checker(document_id=public_document.id, current_user=test_viewer, db=db))

    assert exc_info.value.headers["X-Policy-Reason"] == "document_edit_permission_denied"
    assert exc_info.value.headers["X-Policy-Action"] == "document:edit"
    assert "reason_code=document_edit_permission_denied" in exc_info.value.detail
