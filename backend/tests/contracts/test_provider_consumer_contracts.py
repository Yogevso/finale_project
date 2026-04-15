"""Consumer-driven contract verification for backend provider payloads."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from app.adapters import CollaborationContractAdapter
from app.auth_context import COLLABORATION_TOKEN_TYPE, CollaborationAuthService
from app.main import app
from app.models import User, UserRole

# Local runs from monorepo root resolve through `backend/` to workspace root,
# while Dockerized backend tests are mounted at `/app` without sibling projects.
BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent if (BACKEND_ROOT.parent / "frontend").exists() else BACKEND_ROOT
FRONTEND_CONTRACT_PATH = (
    REPO_ROOT / "frontend" / "src" / "test" / "contracts" / "backendProvider.contract.json"
)
COLLAB_SERVER_CONTRACT_PATH = (
    REPO_ROOT
    / "collab-server"
    / "src"
    / "__tests__"
    / "contracts"
    / "backendProvider.contract.json"
)
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        pytest.skip(f"Contract fixture not available in this runtime: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _resolve_schema(schema: dict[str, Any], components: dict[str, Any]) -> dict[str, Any]:
    current = schema
    while "$ref" in current:
        ref = current["$ref"]
        assert isinstance(ref, str)
        assert ref.startswith("#/components/schemas/")
        schema_name = ref.split("/")[-1]
        current = components[schema_name]
    return current


def _collect_object_shape(
    schema: dict[str, Any],
    components: dict[str, Any],
) -> tuple[dict[str, Any], set[str]]:
    resolved = _resolve_schema(schema, components)
    properties: dict[str, Any] = dict(resolved.get("properties", {}))
    required: set[str] = set(resolved.get("required", []))

    for nested in resolved.get("allOf", []):
        nested_properties, nested_required = _collect_object_shape(nested, components)
        properties.update(nested_properties)
        required.update(nested_required)

    return properties, required


def _schema_for_required_path(
    schema: dict[str, Any],
    required_path: str,
    components: dict[str, Any],
) -> dict[str, Any]:
    current = schema
    for raw_segment in required_path.split("."):
        is_array_segment = raw_segment.endswith("[]")
        segment = raw_segment[:-2] if is_array_segment else raw_segment

        properties, required = _collect_object_shape(current, components)
        assert segment in properties, f"Missing contract property '{required_path}' at '{segment}'"
        assert segment in required, f"Contract property '{required_path}' is not required"

        current = _resolve_schema(properties[segment], components)
        if is_array_segment:
            assert (
                current.get("type") == "array"
            ), f"Contract path '{required_path}' expects array segment '{segment}'"
            assert "items" in current, f"Contract path '{required_path}' missing items schema"
            current = current["items"]

    return _resolve_schema(current, components)


def test_frontend_contract_endpoints_match_backend_openapi_provider_shape():
    contract = _load_json(FRONTEND_CONTRACT_PATH)
    assert SEMVER_PATTERN.match(contract["contract_version"])
    assert contract["consumer"] == "frontend"
    assert contract["provider"] == "backend"

    openapi = app.openapi()
    paths = openapi["paths"]
    components = openapi["components"]["schemas"]

    for endpoint in contract["endpoints"]:
        method = endpoint["method"].lower()
        path = endpoint["path"]
        expected_schema_name = endpoint["response_schema"]
        required_paths = endpoint["required_paths"]

        assert path in paths, f"Missing contract path: {path}"
        assert method in paths[path], f"Missing contract method: {method} {path}"

        operation = paths[path][method]
        response = operation.get("responses", {}).get("200")
        assert response is not None, f"Missing 200 response for {method} {path}"

        response_schema = response.get("content", {}).get("application/json", {}).get("schema")
        assert isinstance(
            response_schema, dict
        ), f"Missing JSON response schema for {method} {path}"
        assert response_schema.get("$ref") == (
            f"#/components/schemas/{expected_schema_name}"
        ), f"Unexpected response schema for {method} {path}"

        resolved_response_schema = _resolve_schema(response_schema, components)
        for required_path in required_paths:
            _schema_for_required_path(resolved_response_schema, required_path, components)


def test_collab_server_token_contract_matches_backend_token_payload_provider_shape():
    contract = _load_json(COLLAB_SERVER_CONTRACT_PATH)
    token_contract = contract["collaboration_token"]
    fixture = token_contract["fixture"]
    required_claims = token_contract["required_claims"]
    allowed_permissions = token_contract["allowed_permissions"]
    token_type = token_contract["token_type"]

    assert SEMVER_PATTERN.match(contract["contract_version"])
    assert contract["consumer"] == "collab-server"
    assert contract["provider"] == "backend"
    assert token_type == COLLABORATION_TOKEN_TYPE
    assert allowed_permissions == ["read", "write"]

    user = User(
        id=int(fixture["sub"]),
        email=fixture["email"],
        username=fixture["username"],
        full_name="Contract User",
        hashed_password="not-used",
        role=UserRole(fixture["role"]),
        is_active=True,
        tenant_id=fixture["tenant_id"],
    )

    auth_service = CollaborationAuthService(
        secret_key="contract-test-secret",
        algorithm="HS256",
    )
    token = auth_service.create_collab_token(
        user=user,
        document_id=int(fixture["document_id"]),
        permissions=list(fixture["permissions"]),
    )
    decoded = auth_service.verify_collab_token(token)
    assert decoded is not None
    assert decoded["type"] == token_type

    for claim in required_claims:
        assert claim in decoded

    normalized_permissions = CollaborationContractAdapter().normalize_permissions(
        fixture["permissions"]
    )
    assert normalized_permissions == allowed_permissions
