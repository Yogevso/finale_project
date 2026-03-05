"""Wave T fixture validation against live Pydantic schemas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from app.api.management.documents import CompanyAssignRequest
from app.schemas import DocumentResponse, DocumentUpdate, MessageResponse, TenantSummary

FIXTURE_DIR = Path(__file__).resolve().parent / "contracts" / "audience"


def _load_fixture(name: str) -> dict[str, Any]:
    with (FIXTURE_DIR / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _assert_error_shape(payload: dict[str, Any]) -> None:
    assert isinstance(payload.get("detail"), str)
    assert isinstance(payload.get("error_code"), str)


def test_company_assignment_fixture_payloads_match_pydantic_schemas() -> None:
    fixture = _load_fixture("company_assignment.fixtures.json")
    assert fixture["resource"] == "company_assignment"

    for item in fixture["fixtures"]:
        method = item["endpoint"]["method"].upper()
        request_body = item.get("request", {}).get("body")
        response_body = item["response"].get("body")
        status_code = int(item["response"]["status_code"])

        if method == "POST":
            CompanyAssignRequest.model_validate(request_body)

        if status_code == 200 and item["id"] in {
            "assign_company_set_success",
            "remove_company_assignment_success",
        }:
            MessageResponse.model_validate(response_body)
            continue

        if status_code == 200 and item["id"] == "get_assigned_companies_success":
            TypeAdapter(list[TenantSummary]).validate_python(response_body)
            continue

        if status_code >= 400:
            assert isinstance(response_body, dict)
            _assert_error_shape(response_body)


def test_visibility_fixture_payloads_match_pydantic_schemas() -> None:
    fixture = _load_fixture("visibility.fixtures.json")
    assert fixture["resource"] == "visibility"

    for item in fixture["fixtures"]:
        request_body = item.get("request", {}).get("body") or {}
        response_body = item["response"].get("body")
        status_code = int(item["response"]["status_code"])

        parsed_request = DocumentUpdate.model_validate(request_body)
        if parsed_request.visibility is not None:
            # Wave T reason-capture policy for visibility changes.
            assert isinstance(parsed_request.reason, str)
            assert parsed_request.reason.strip()

        if status_code == 200:
            DocumentResponse.model_validate(response_body)
            continue

        if status_code >= 400:
            assert isinstance(response_body, dict)
            _assert_error_shape(response_body)
