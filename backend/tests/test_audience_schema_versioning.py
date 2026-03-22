"""Wave T schema header coverage tests for assignment endpoints."""

from __future__ import annotations

import re
from uuid import uuid4

from app.config import settings

SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def test_assignment_endpoints_emit_schema_version_header(
    client,
    system_admin_headers,
    test_tenant,
    test_tenant_2,
):
    create_response = client.post(
        "/api/v1/documents",
        headers=system_admin_headers,
        json={
            "title": "Schema header coverage",
            "visibility": "company",
            "status": "draft",
            "company_ids": [test_tenant.id],
            "platform": "Core Platform",
        },
    )
    assert create_response.status_code == 201
    document = create_response.json()
    document_id = int(document["id"])
    etag = document["etag"]

    get_response = client.get(
        f"/api/v1/documents/{document_id}/assigned-companies",
        headers=system_admin_headers,
    )
    assert get_response.status_code == 200
    assert get_response.headers.get("X-API-Schema-Version") == settings.AUDIENCE_ASSIGNMENT_SCHEMA_VERSION

    assign_response = client.post(
        f"/api/v1/documents/{document_id}/assign-companies",
        headers={**system_admin_headers, "If-Match": etag},
        json={"company_ids": [test_tenant.id, test_tenant_2.id]},
    )
    assert assign_response.status_code == 200
    assert assign_response.headers.get("X-API-Schema-Version") == settings.AUDIENCE_ASSIGNMENT_SCHEMA_VERSION

    next_etag = assign_response.headers["ETag"]
    bulk_response = client.put(
        f"/api/v1/documents/{document_id}/companies/batch",
        headers={
            **system_admin_headers,
            "If-Match": next_etag,
            "Idempotency-Key": f"schema-version-bulk-{uuid4().hex}",
        },
        json={"company_ids": [test_tenant.id, test_tenant_2.id]},
    )
    assert bulk_response.status_code == 200
    assert bulk_response.headers.get("X-API-Schema-Version") == settings.AUDIENCE_ASSIGNMENT_SCHEMA_VERSION

    next_etag = bulk_response.headers["ETag"]
    remove_response = client.delete(
        f"/api/v1/documents/{document_id}/assign-companies/{test_tenant_2.id}",
        headers={**system_admin_headers, "If-Match": next_etag},
    )
    assert remove_response.status_code == 200
    assert remove_response.headers.get("X-API-Schema-Version") == settings.AUDIENCE_ASSIGNMENT_SCHEMA_VERSION

    assert SEMVER_PATTERN.match(settings.AUDIENCE_ASSIGNMENT_SCHEMA_VERSION)

