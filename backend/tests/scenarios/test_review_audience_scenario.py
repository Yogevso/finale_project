"""Scenario builder for review + audience publish flows."""

from __future__ import annotations

import pytest


def _create_document_for_review_flow(client, headers, *, company_id: int) -> int:
    create_response = client.post(
        "/api/v1/documents",
        headers=headers,
        json={
            "title": "Review Audience Scenario Document",
            "description": "Scenario builder document",
            "visibility": "company",
            "status": "draft",
            "company_ids": [company_id],
        },
    )
    assert create_response.status_code == 201
    return int(create_response.json()["id"])


def _create_new_version(client, headers, *, document_id: int) -> int:
    version_response = client.post(
        f"/api/v1/documents/{document_id}/versions",
        headers=headers,
        json={
            "content": "scenario content",
            "changes_summary": "scenario update",
            "bump_type": "patch",
        },
    )
    assert version_response.status_code == 201
    return int(version_response.json()["id"])


def _submit_and_approve_review(
    client,
    submit_headers,
    approve_headers,
    *,
    document_id: int,
    version_id: int,
) -> int:
    submit_response = client.post(
        f"/api/v1/reviews/documents/{document_id}/submit",
        headers=submit_headers,
        json={"version_id": version_id, "message": "submit scenario review"},
    )
    assert submit_response.status_code in (200, 201)
    review_id = int(submit_response.json()["id"])

    approve_response = client.post(
        f"/api/v1/reviews/{review_id}/approve",
        headers=approve_headers,
        json={"comments": "approved in scenario"},
    )
    assert approve_response.status_code == 200
    return review_id


@pytest.mark.integration
@pytest.mark.parametrize(
    ("deactivate_assigned_company", "expected_publish_status"),
    [
        (False, 200),
        (True, 400),
    ],
)
def test_review_audience_submit_approve_publish_cycle(
    client,
    db,
    auth_headers,
    manager_headers,
    test_tenant,
    deactivate_assigned_company: bool,
    expected_publish_status: int,
):
    """
    Scenario: submit -> approve -> publish with audience gates validated at publish time.
    """
    document_id = _create_document_for_review_flow(
        client,
        auth_headers,
        company_id=test_tenant.id,
    )
    version_id = _create_new_version(client, auth_headers, document_id=document_id)
    _submit_and_approve_review(
        client,
        auth_headers,
        manager_headers,
        document_id=document_id,
        version_id=version_id,
    )

    if deactivate_assigned_company:
        test_tenant.is_active = False
        db.commit()

    publish_response = client.post(
        f"/api/v1/documents/{document_id}/versions/{version_id}/publish",
        headers=manager_headers,
    )

    assert publish_response.status_code == expected_publish_status
    if expected_publish_status == 200:
        assert publish_response.json()["is_published"] is True
    else:
        assert "deactivated companies" in publish_response.json()["detail"]
