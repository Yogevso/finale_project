"""Tests for authorization capability object mapping and evaluation."""

from app.domain.capabilities import CanAssignCompanies, CanPublish, PermissionCapability
from app.services.permissions import (
    Permission,
    evaluate_customer,
    evaluate_document_access,
    evaluate_manager_or_above,
    evaluate_permission_capability,
    resolve_permission_capability,
)


def test_resolve_permission_capability_returns_specialized_objects():
    publish_capability = resolve_permission_capability(Permission.PUBLISH_DOCUMENT)
    assign_capability = resolve_permission_capability(Permission.ASSIGN_COMPANIES)
    generic_capability = resolve_permission_capability(Permission.MANAGE_USERS)

    assert isinstance(publish_capability, CanPublish)
    assert isinstance(assign_capability, CanAssignCompanies)
    assert isinstance(generic_capability, PermissionCapability)
    assert generic_capability.name == "CanManageUsers"


def test_evaluate_permission_capability_includes_capability_metadata(db, test_viewer):
    capability = resolve_permission_capability(Permission.DELETE_DOCUMENT)
    decision = evaluate_permission_capability(test_viewer, capability)

    assert decision.allowed is False
    assert decision.reason_code == "missing_permission"
    assert decision.metadata["permission"] == Permission.DELETE_DOCUMENT.value
    assert decision.metadata["capability"] == "CanDeleteDocument"


def test_role_and_document_decisions_include_capability_metadata(db, test_user, public_document):
    role_decision = evaluate_manager_or_above(test_user)
    publish_decision = evaluate_document_access(test_user, public_document, "publish")

    assert role_decision.allowed is False
    assert role_decision.reason_code == "role_not_allowed"
    assert role_decision.metadata["capability"] == "CanManagerOrAbove"

    assert publish_decision.allowed is False
    assert publish_decision.reason_code == "document_publish_permission_denied"
    assert publish_decision.metadata["capability"] == "CanPublishDocument"


def test_customer_decision_uses_customer_capability(db, test_admin):
    decision = evaluate_customer(test_admin)

    assert decision.allowed is False
    assert decision.reason_code == "customer_user_required"
    assert decision.metadata["capability"] == "CanAccessCustomerPortal"
