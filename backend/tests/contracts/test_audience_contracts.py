"""Audience-focused contract verification against live backend OpenAPI."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from app.main import app

AUDIENCE_CONTRACT_PATH = Path(__file__).resolve().parent / "audience_contracts.json"
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def _load_json(path: Path) -> dict[str, Any]:
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


def _schema_for_path(
    schema: dict[str, Any],
    field_path: str,
    components: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    current = schema
    leaf_required = False

    for raw_segment in field_path.split("."):
        is_array_segment = raw_segment.endswith("[]")
        segment = raw_segment[:-2] if is_array_segment else raw_segment

        properties, required = _collect_object_shape(current, components)
        assert segment in properties, f"Missing contract property '{field_path}' at '{segment}'"
        leaf_required = segment in required

        current = _resolve_schema(properties[segment], components)
        if is_array_segment:
            assert current.get("type") == "array", (
                f"Contract path '{field_path}' expects array segment '{segment}'"
            )
            assert "items" in current, f"Contract path '{field_path}' missing items schema"
            current = current["items"]

    return _resolve_schema(current, components), leaf_required


def _assert_type_expectation(
    *,
    endpoint_id: str,
    field_path: str,
    field_schema: dict[str, Any],
    leaf_required: bool,
    expectation: dict[str, Any],
) -> None:
    expected_type = expectation.get("type")
    if expected_type is not None:
        assert field_schema.get("type") == expected_type, (
            f"{endpoint_id}:{field_path} expected type '{expected_type}', "
            f"got '{field_schema.get('type')}'"
        )

    if "required" in expectation:
        assert leaf_required is bool(expectation["required"]), (
            f"{endpoint_id}:{field_path} expected required={expectation['required']}, "
            f"got required={leaf_required}"
        )

    expected_default = expectation.get("default")
    if expected_default is not None:
        assert field_schema.get("default") == expected_default, (
            f"{endpoint_id}:{field_path} expected default '{expected_default}', "
            f"got '{field_schema.get('default')}'"
        )

    expected_enum_values = expectation.get("enum_values")
    if expected_enum_values is not None:
        actual_enum = field_schema.get("enum")
        assert isinstance(actual_enum, list), (
            f"{endpoint_id}:{field_path} expected enum values {expected_enum_values}, "
            "but schema has no enum list"
        )
        missing_values = [value for value in expected_enum_values if value not in actual_enum]
        assert not missing_values, (
            f"{endpoint_id}:{field_path} missing enum values {missing_values}; "
            f"actual enum={actual_enum}"
        )


@pytest.mark.parametrize(
    "endpoint_contract",
    _load_json(AUDIENCE_CONTRACT_PATH)["audience_contracts"],
    ids=lambda endpoint: str(endpoint["id"]),
)
def test_audience_contract_endpoints_match_backend_openapi(endpoint_contract: dict[str, Any]):
    contract = _load_json(AUDIENCE_CONTRACT_PATH)
    assert SEMVER_PATTERN.match(contract["contract_version"])
    assert contract["provider"] == "backend"

    openapi = app.openapi()
    paths = openapi["paths"]
    components = openapi["components"]["schemas"]

    method = endpoint_contract["method"].lower()
    path = endpoint_contract["path"]
    expected_schema_name = endpoint_contract["response_schema"]
    required_paths: list[str] = endpoint_contract["required_paths"]
    type_expectations: dict[str, dict[str, Any]] = endpoint_contract.get("type_expectations", {})

    assert path in paths, f"Missing contract path: {path}"
    assert method in paths[path], f"Missing contract method: {method} {path}"

    operation = paths[path][method]
    response = operation.get("responses", {}).get("200")
    assert response is not None, f"Missing 200 response for {method} {path}"

    response_schema = response.get("content", {}).get("application/json", {}).get("schema")
    assert isinstance(response_schema, dict), f"Missing JSON schema for {method} {path}"
    assert response_schema.get("$ref") == f"#/components/schemas/{expected_schema_name}", (
        f"Unexpected response schema for {method} {path}"
    )

    resolved_response_schema = _resolve_schema(response_schema, components)
    for required_path in required_paths:
        _schema_for_path(resolved_response_schema, required_path, components)

    for field_path, expectation in type_expectations.items():
        field_schema, leaf_required = _schema_for_path(
            resolved_response_schema,
            field_path,
            components,
        )
        _assert_type_expectation(
            endpoint_id=endpoint_contract["id"],
            field_path=field_path,
            field_schema=field_schema,
            leaf_required=leaf_required,
            expectation=expectation,
        )
