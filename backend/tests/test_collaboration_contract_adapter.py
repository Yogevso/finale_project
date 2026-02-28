"""Tests for collaboration anti-corruption adapters."""

from __future__ import annotations

import jwt
import pytest

from app.adapters import CollaborationContractAdapter
from app.config import settings
from app.services.collaboration_service import CollaborationService


def test_collaboration_contract_adapter_coerces_document_id():
    adapter = CollaborationContractAdapter()

    assert adapter.coerce_document_id(12) == 12
    assert adapter.coerce_document_id("34") == 34

    with pytest.raises(ValueError, match="positive integer"):
        adapter.coerce_document_id("abc")


def test_collaboration_contract_adapter_normalizes_permissions():
    adapter = CollaborationContractAdapter()

    assert adapter.normalize_permissions(["WRITE", " write ", "read", "unknown"]) == [
        "read",
        "write",
    ]
    assert adapter.normalize_permissions(["write"]) == ["read", "write"]
    assert adapter.normalize_permissions([]) == []


def test_collaboration_contract_adapter_builds_permissions_from_access():
    adapter = CollaborationContractAdapter()

    assert adapter.permissions_from_access(can_view=True, can_edit=True) == ["read", "write"]
    assert adapter.permissions_from_access(can_view=True, can_edit=False) == ["read"]
    assert adapter.permissions_from_access(can_view=False, can_edit=False) == []


def test_collaboration_service_issues_token_with_normalized_contract(test_user):
    service = CollaborationService()

    token = service.issue_collab_token(
        user=test_user,
        document_id=77,
        permissions=["WRITE", "unknown", "read"],
    )
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    assert payload["document_id"] == "77"
    assert payload["permissions"] == ["read", "write"]
