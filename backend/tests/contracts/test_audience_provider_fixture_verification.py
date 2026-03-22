"""Provider-side verification for frozen audience contract fixtures."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from app.models import Document, DocumentStatus, DocumentVisibility, Platform, Tenant, Version

FIXTURE_DIR = Path(__file__).resolve().parent / "audience"
COMPANY_ASSIGNMENT_FIXTURES_PATH = FIXTURE_DIR / "company_assignment.fixtures.json"
VISIBILITY_FIXTURES_PATH = FIXTURE_DIR / "visibility.fixtures.json"
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")

OPTIONAL_INT_FIELDS = {
    "parent_id",
    "platform_id",
    "versions_count",
    "attachments_count",
    "comments_count",
}
DYNAMIC_INT_FIELDS = {"id", "created_by", "row_version", *OPTIONAL_INT_FIELDS}
DYNAMIC_STRING_FIELDS = {"etag"}
DYNAMIC_DATETIME_FIELDS = {"created_at", "updated_at", "published_at"}


def _load_contract(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _assert_contract_metadata(contract: dict[str, Any], *, resource: str) -> None:
    assert SEMVER_PATTERN.match(contract["contract_version"])
    assert contract["provider"] == "backend"
    assert contract["domain"] == "audience"
    assert contract["resource"] == resource


def _seed_fixture_document(
    *,
    db,
    created_by: int,
    visibility: DocumentVisibility,
    row_version: int,
    with_initial_company: bool,
) -> Document:
    dell = Tenant(id=10, name="Dell", slug="dell", is_active=True, company_type="customer")
    lenovo = Tenant(id=12, name="Lenovo", slug="lenovo", is_active=True, company_type="customer")
    platform = Platform(id=3, name="Dell", slug="dell-platform")
    document = Document(
        id=42,
        title="Intel Driver Release Notes",
        document_number="DOC-20260304-0042",
        description="Release notes for enterprise client distribution.",
        version_label="v3.2",
        category="Release Notes",
        topic="drivers",
        platform="Dell",
        platform_id=platform.id,
        release_branch="main",
        tags="intel,drivers,dell",
        status=DocumentStatus.DRAFT,
        visibility=visibility,
        created_by=created_by,
        tenant_id=dell.id,
        row_version=row_version,
        created_at=datetime(2026, 3, 4, 10, 15, 0),
        updated_at=datetime(2026, 3, 4, 10, 15, 0),
    )
    if with_initial_company:
        document.assigned_companies = [dell]

    db.add_all([dell, lenovo, platform, document])
    db.flush()

    db.add(
        Version(
            document_id=document.id,
            version_number=1,
            semantic_version="1.0.0",
            content="",
            changes_summary="Initial version",
            created_by=created_by,
        )
    )
    db.commit()
    db.refresh(document)
    return document


def _leaf_field(path: str) -> str:
    tail = path.rsplit(".", 1)[-1]
    return tail.split("[", 1)[0]


def _assert_datetime_like(value: str, *, path: str) -> None:
    assert isinstance(value, str), f"{path} expected datetime string"
    normalized = value.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(normalized)
    except ValueError as exc:  # pragma: no cover - defensive assertion path
        raise AssertionError(f"{path} is not ISO-8601 compatible: {value}") from exc


def _assert_payload_compatible(*, actual: Any, expected: Any, path: str = "root") -> None:
    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"{path} expected object"
        for key, expected_value in expected.items():
            assert key in actual, f"{path} missing key '{key}'"
            _assert_payload_compatible(
                actual=actual[key],
                expected=expected_value,
                path=f"{path}.{key}",
            )
        return

    if isinstance(expected, list):
        assert isinstance(actual, list), f"{path} expected list"
        assert len(actual) >= len(expected), f"{path} expected at least {len(expected)} items"
        for index, expected_item in enumerate(expected):
            _assert_payload_compatible(
                actual=actual[index],
                expected=expected_item,
                path=f"{path}[{index}]",
            )
        return

    if expected is None:
        return

    field = _leaf_field(path)
    if field in OPTIONAL_INT_FIELDS and actual is None:
        return
    if field in DYNAMIC_INT_FIELDS:
        assert isinstance(actual, int), f"{path} expected integer, got {type(actual).__name__}"
        return
    if field in DYNAMIC_STRING_FIELDS:
        assert isinstance(actual, str), f"{path} expected string"
        assert actual.strip(), f"{path} expected non-empty string"
        return
    if field in DYNAMIC_DATETIME_FIELDS:
        _assert_datetime_like(actual, path=path)
        return

    assert actual == expected, f"{path} expected {expected!r}, got {actual!r}"


def _render_path(path_template: str, path_params: dict[str, Any]) -> str:
    rendered = path_template
    for key, value in path_params.items():
        rendered = rendered.replace(f"{{{key}}}", str(value))
    return rendered


def _send_request(*, client, method: str, path: str, headers: dict[str, str], body: Any):
    if method == "GET":
        return client.get(path, headers=headers)
    if method == "POST":
        return client.post(path, headers=headers, json=body)
    if method == "PUT":
        return client.put(path, headers=headers, json=body)
    if method == "DELETE":
        return client.delete(path, headers=headers)
    raise AssertionError(f"Unsupported method in contract fixture: {method}")


def _run_fixture_sequence(
    *,
    client,
    system_admin_headers: dict[str, str],
    contract: dict[str, Any],
    current_if_match: str,
) -> None:
    for fixture in contract["fixtures"]:
        request_data: dict[str, Any] = fixture["request"]
        response_contract: dict[str, Any] = fixture["response"]
        method = str(fixture["endpoint"]["method"]).upper()
        path = _render_path(fixture["endpoint"]["path"], request_data.get("path_params", {}))

        headers = dict(system_admin_headers)
        if "If-Match" in request_data.get("headers", {}):
            headers["If-Match"] = current_if_match

        response = _send_request(
            client=client,
            method=method,
            path=path,
            headers=headers,
            body=request_data.get("body"),
        )

        assert response.status_code == response_contract["status_code"], fixture["id"]

        expected_headers = response_contract.get("headers", {})
        if "ETag" in expected_headers:
            actual_etag = response.headers.get("ETag")
            assert actual_etag, f"{fixture['id']} missing ETag header"
            assert actual_etag.strip('"') != current_if_match.strip('"')
            current_if_match = actual_etag

        if "body" in response_contract:
            _assert_payload_compatible(
                actual=response.json(),
                expected=response_contract["body"],
                path=f"fixture[{fixture['id']}]",
            )


def test_company_assignment_provider_fixtures_remain_backend_compatible(
    client, db, system_admin_headers, test_admin
):
    contract = _load_contract(COMPANY_ASSIGNMENT_FIXTURES_PATH)
    _assert_contract_metadata(contract, resource="company_assignment")

    document = _seed_fixture_document(
        db=db,
        created_by=test_admin.id,
        visibility=DocumentVisibility.COMPANY,
        row_version=3,
        with_initial_company=True,
    )

    _run_fixture_sequence(
        client=client,
        system_admin_headers=system_admin_headers,
        contract=contract,
        current_if_match=document.etag,
    )


def test_visibility_provider_fixtures_remain_backend_compatible(
    client, db, system_admin_headers, test_admin
):
    contract = _load_contract(VISIBILITY_FIXTURES_PATH)
    _assert_contract_metadata(contract, resource="visibility")

    document = _seed_fixture_document(
        db=db,
        created_by=test_admin.id,
        visibility=DocumentVisibility.INTERNAL,
        row_version=2,
        with_initial_company=False,
    )

    _run_fixture_sequence(
        client=client,
        system_admin_headers=system_admin_headers,
        contract=contract,
        current_if_match=document.etag,
    )
