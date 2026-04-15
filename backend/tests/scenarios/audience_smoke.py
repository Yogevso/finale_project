"""Critical audience-path smoke scenarios."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.models import Document, DocumentVisibility
from app.services.version_service import VersionService

pytestmark = pytest.mark.smoke


def _create_publish_ready_version(
    *,
    client: TestClient,
    document_id: int,
    system_admin_headers: dict,
    manager_headers: dict,
) -> int:
    create_resp = client.post(
        f"/api/v1/documents/{document_id}/versions",
        headers=system_admin_headers,
        json={"content": "Smoke publish candidate", "changes_summary": "smoke"},
    )
    assert create_resp.status_code == 201
    version_id = create_resp.json()["id"]

    submit_resp = client.post(
        f"/api/v1/reviews/documents/{document_id}/submit",
        headers=system_admin_headers,
        json={"version_id": version_id, "message": "smoke review"},
    )
    assert submit_resp.status_code in [200, 201]
    review_id = submit_resp.json()["id"]

    approve_resp = client.post(
        f"/api/v1/reviews/{review_id}/approve",
        headers=manager_headers,
        json={"comments": "approved"},
    )
    assert approve_resp.status_code == 200
    return version_id


def _force_invalid_company_audience(*, db, document_id: int) -> None:
    document = db.query(Document).filter(Document.id == document_id).first()
    assert document is not None
    document.visibility = DocumentVisibility.COMPANY
    document.assigned_companies = []
    db.commit()


def test_smoke_assign_companies_requires_auth(
    client: TestClient, sample_document: dict, test_tenant
):
    resp = client.post(
        f"/api/v1/documents/{sample_document['id']}/assign-companies",
        json={"company_ids": [test_tenant.id]},
    )
    assert resp.status_code == 401


def test_smoke_bulk_assign_companies_requires_auth(
    client: TestClient, sample_document: dict, test_tenant
):
    resp = client.put(
        f"/api/v1/documents/{sample_document['id']}/companies/batch",
        json={"company_ids": [test_tenant.id]},
    )
    assert resp.status_code == 401


def test_smoke_assign_companies_accepts_valid_payload(
    client: TestClient,
    system_admin_headers: dict,
    sample_document: dict,
    test_tenant,
):
    resp = client.post(
        f"/api/v1/documents/{sample_document['id']}/assign-companies",
        headers={**system_admin_headers, "If-Match": sample_document["etag"]},
        json={"company_ids": [test_tenant.id]},
    )
    assert resp.status_code == 200
    assert "Assigned company set updated" in resp.json()["message"]


def test_smoke_bulk_assign_companies_accepts_valid_payload(
    client: TestClient,
    system_admin_headers: dict,
    sample_document: dict,
    test_tenant,
):
    resp = client.put(
        f"/api/v1/documents/{sample_document['id']}/companies/batch",
        headers={
            **system_admin_headers,
            "If-Match": sample_document["etag"],
            "Idempotency-Key": f"smoke-{uuid4().hex}",
        },
        json={"company_ids": [test_tenant.id]},
    )
    assert resp.status_code == 200
    assert "Batch company assignment updated" in resp.json()["message"]


def test_smoke_document_update_rejects_company_visibility_without_assignments(
    client: TestClient,
    system_admin_headers: dict,
    sample_document: dict,
):
    resp = client.put(
        f"/api/v1/documents/{sample_document['id']}",
        headers={**system_admin_headers, "If-Match": sample_document["etag"]},
        json={
            "visibility": "company",
            "reason": "Smoke: restrict without assignments",
            "company_ids": [],
        },
    )
    assert resp.status_code == 400
    assert "Company visibility requires at least one assigned company" in resp.json()["detail"]


def test_smoke_publish_requires_approved_review(
    client: TestClient,
    system_admin_headers: dict,
    sample_document: dict,
):
    create_resp = client.post(
        f"/api/v1/documents/{sample_document['id']}/versions",
        headers=system_admin_headers,
        json={"content": "Smoke no review", "changes_summary": "should block"},
    )
    assert create_resp.status_code == 201
    version_id = create_resp.json()["id"]

    publish_resp = client.post(
        f"/api/v1/documents/{sample_document['id']}/versions/{version_id}/publish",
        headers=system_admin_headers,
    )
    assert publish_resp.status_code == 409


def test_smoke_publish_blocks_invalid_audience_when_enforcement_enabled(
    client: TestClient,
    db,
    system_admin_headers: dict,
    manager_headers: dict,
    sample_document: dict,
    monkeypatch,
):
    monkeypatch.setattr(settings, "FEATURE_FLAG_COMPANY_AUDIENCE_ENFORCEMENT", True)
    version_id = _create_publish_ready_version(
        client=client,
        document_id=sample_document["id"],
        system_admin_headers=system_admin_headers,
        manager_headers=manager_headers,
    )
    _force_invalid_company_audience(db=db, document_id=sample_document["id"])

    publish_resp = client.post(
        f"/api/v1/documents/{sample_document['id']}/versions/{version_id}/publish",
        headers=system_admin_headers,
    )
    assert publish_resp.status_code == 400
    assert (
        "Company visibility requires at least one assigned company" in publish_resp.json()["detail"]
    )


def test_smoke_publish_warns_when_enforcement_disabled(
    client: TestClient,
    db,
    system_admin_headers: dict,
    manager_headers: dict,
    sample_document: dict,
    monkeypatch,
):
    monkeypatch.setattr(settings, "FEATURE_FLAG_COMPANY_AUDIENCE_ENFORCEMENT", False)
    version_id = _create_publish_ready_version(
        client=client,
        document_id=sample_document["id"],
        system_admin_headers=system_admin_headers,
        manager_headers=manager_headers,
    )
    _force_invalid_company_audience(db=db, document_id=sample_document["id"])

    publish_resp = client.post(
        f"/api/v1/documents/{sample_document['id']}/versions/{version_id}/publish",
        headers=system_admin_headers,
    )
    assert publish_resp.status_code == 200
    payload = publish_resp.json()
    assert payload["warnings"]
    assert any("Audience enforcement disabled" in warning for warning in payload["warnings"])


def test_smoke_publish_blocks_when_validation_unreachable_and_safe_mode_off(
    client: TestClient,
    system_admin_headers: dict,
    manager_headers: dict,
    sample_document: dict,
    monkeypatch,
):
    monkeypatch.setattr(settings, "AUDIENCE_VALIDATION_SAFE_MODE_ENABLED", False)
    version_id = _create_publish_ready_version(
        client=client,
        document_id=sample_document["id"],
        system_admin_headers=system_admin_headers,
        manager_headers=manager_headers,
    )

    def _raise_unreachable(_document) -> None:  # noqa: ANN001
        raise ConnectionError("validation unavailable")

    monkeypatch.setattr(
        VersionService,
        "_run_publish_audience_validation_gate",
        staticmethod(_raise_unreachable),
    )
    publish_resp = client.post(
        f"/api/v1/documents/{sample_document['id']}/versions/{version_id}/publish",
        headers=system_admin_headers,
    )
    assert publish_resp.status_code == 400
    assert "Audience validation service is unavailable" in publish_resp.json()["detail"]


def test_smoke_publish_warns_when_validation_unreachable_and_safe_mode_on(
    client: TestClient,
    system_admin_headers: dict,
    manager_headers: dict,
    sample_document: dict,
    monkeypatch,
):
    monkeypatch.setattr(settings, "AUDIENCE_VALIDATION_SAFE_MODE_ENABLED", True)
    version_id = _create_publish_ready_version(
        client=client,
        document_id=sample_document["id"],
        system_admin_headers=system_admin_headers,
        manager_headers=manager_headers,
    )

    def _raise_unreachable(_document) -> None:  # noqa: ANN001
        raise TimeoutError("validation timeout")

    monkeypatch.setattr(
        VersionService,
        "_run_publish_audience_validation_gate",
        staticmethod(_raise_unreachable),
    )
    publish_resp = client.post(
        f"/api/v1/documents/{sample_document['id']}/versions/{version_id}/publish",
        headers=system_admin_headers,
    )
    assert publish_resp.status_code == 200
    payload = publish_resp.json()
    assert payload["warnings"]
    assert any("safe-mode fallback allowed publish" in warning for warning in payload["warnings"])
