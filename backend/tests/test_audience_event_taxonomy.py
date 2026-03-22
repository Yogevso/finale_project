"""Wave T taxonomy tests for audience audit event types."""

from __future__ import annotations

from app.models import AudienceEventType, AuditLog


def test_audience_audit_paths_emit_valid_taxonomy_values(
    client,
    db,
    system_admin_headers,
    test_tenant,
    test_tenant_2,
):
    create_response = client.post(
        "/api/v1/documents",
        headers=system_admin_headers,
        json={
            "title": "Audience taxonomy coverage",
            "visibility": "company",
            "status": "draft",
            "company_ids": [test_tenant.id],
            "platform": "Core Platform",
        },
    )
    assert create_response.status_code == 201
    payload = create_response.json()
    document_id = payload["id"]
    etag = payload["etag"]

    assign_response = client.post(
        f"/api/v1/documents/{document_id}/assign-companies",
        headers={**system_admin_headers, "If-Match": f"\"{etag}\""},
        json={"company_ids": [test_tenant.id, test_tenant_2.id]},
    )
    assert assign_response.status_code == 200
    etag = assign_response.headers["ETag"].strip('"')

    remove_response = client.delete(
        f"/api/v1/documents/{document_id}/assign-companies/{test_tenant_2.id}",
        headers={**system_admin_headers, "If-Match": f"\"{etag}\""},
    )
    assert remove_response.status_code == 200
    etag = remove_response.headers["ETag"].strip('"')

    visibility_response = client.put(
        f"/api/v1/documents/{document_id}",
        headers={**system_admin_headers, "If-Match": f"\"{etag}\""},
        json={
            "visibility": "internal",
            "reason": "Reduce external audience after review",
        },
    )
    assert visibility_response.status_code == 200

    archive_response = client.post(
        f"/api/v1/documents/{document_id}/archive",
        headers=system_admin_headers,
    )
    assert archive_response.status_code == 200

    restore_response = client.post(
        f"/api/v1/documents/{document_id}/restore",
        headers=system_admin_headers,
    )
    assert restore_response.status_code == 200

    event_values = {
        row.audience_event_type.value
        for row in db.query(AuditLog).filter(AuditLog.document_id == document_id).all()
        if row.audience_event_type is not None
    }
    expected_values = {item.value for item in AudienceEventType}

    assert AudienceEventType.ASSIGNMENT_CREATED.value in event_values
    assert AudienceEventType.ASSIGNMENT_REMOVED.value in event_values
    assert AudienceEventType.VISIBILITY_CHANGED.value in event_values
    assert AudienceEventType.AUDIENCE_SNAPSHOT_TAKEN.value in event_values
    assert AudienceEventType.AUDIENCE_ROLLBACK.value in event_values
    assert event_values.issubset(expected_values)
