"""Tests for BFF document endpoints."""

from __future__ import annotations

from tests.scenarios import (
    create_cross_tenant_document_scenario,
    create_document_detail_bundle_scenario,
)


def test_document_detail_page_bundle_returns_composed_payload(
    client,
    db,
    auth_headers,
    test_user,
    test_tenant,
):
    scenario = create_document_detail_bundle_scenario(
        db,
        user=test_user,
        tenant=test_tenant,
    )

    response = client.get(
        f"/api/v1/bff/documents/{scenario.document.id}/detail-page",
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["document"]["id"] == scenario.document.id
    assert len(payload["attachments"]) == 1
    assert payload["attachments"][0]["id"] == scenario.attachment.id
    assert len(payload["assigned_companies"]) == 1
    assert payload["assigned_companies"][0]["id"] == scenario.tenant.id
    assert payload["review_history"]["total"] == 1
    assert payload["review_history"]["items"][0]["id"] == scenario.review.id


def test_document_detail_page_bundle_is_tenant_scoped(client, db, auth_headers, test_user):
    scenario = create_cross_tenant_document_scenario(
        db,
        actor=test_user,
        actor_tenant_name="Bff Tenant A",
        target_tenant_name="Bff Tenant B",
        document_title="Cross Tenant Bundle",
    )

    response = client.get(
        f"/api/v1/bff/documents/{scenario.document.id}/detail-page",
        headers=auth_headers,
    )

    assert response.status_code == 404
