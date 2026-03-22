"""Integration tests for centralized domain-error -> HTTP mapping."""


def test_assign_companies_not_found_uses_domain_error_mapping(client, system_admin_headers):
    response = client.post(
        "/api/v1/documents/999999/assign-companies",
        headers=system_admin_headers,
        json={"company_ids": []},
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["detail"] == "Document not found"
    assert payload["error_code"] == "not_found"


def test_assign_companies_invalid_set_uses_domain_error_mapping(client, system_admin_headers, sample_document):
    response = client.post(
        f"/api/v1/documents/{sample_document['id']}/assign-companies",
        headers=system_admin_headers,
        json={"company_ids": [999999]},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["detail"] == "Some company IDs are invalid"
    assert payload["error_code"] == "invalid_company_set"


def test_publish_version_conflict_uses_domain_error_mapping(client, system_admin_headers, sample_document):
    create_resp = client.post(
        f"/api/v1/documents/{sample_document['id']}/versions",
        headers=system_admin_headers,
        json={"content": "No approval yet", "changes_summary": "candidate"},
    )
    assert create_resp.status_code == 201
    version_id = create_resp.json()["id"]

    publish_resp = client.post(
        f"/api/v1/documents/{sample_document['id']}/versions/{version_id}/publish",
        headers=system_admin_headers,
    )

    assert publish_resp.status_code == 409
    payload = publish_resp.json()
    assert payload["detail"] == "Cannot publish without an approved review for this version"
    assert payload["error_code"] == "conflict"

