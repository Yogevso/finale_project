"""Wave T governance + analytics integration tests."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timedelta

from app.models import ActionType, AudienceEventType, AuditLog, Document, DocumentStatus, DocumentVisibility
from app.utils.audience_audit_signing import verify_payload_signature


def _create_document_with_visibility(
    client,
    headers: dict[str, str],
    *,
    title: str,
    visibility: str,
    company_ids: list[int] | None = None,
) -> dict:
    payload = {"title": title, "status": "draft", "visibility": visibility, "platform": "Core Platform"}
    if company_ids is not None:
        payload["company_ids"] = company_ids
    response = client.post("/api/v1/documents", headers=headers, json=payload)
    assert response.status_code == 201
    return response.json()


def test_audit_export_csv_date_filter_and_role_gate(
    client,
    db,
    manager_headers,
    auth_headers,
    viewer_auth_headers,
    test_admin,
):
    old_log = AuditLog(
        user_id=test_admin.id,
        action=ActionType.SYSTEM,
        details="old-log-outside-window",
        created_at=datetime.utcnow() - timedelta(days=120),
    )
    in_range_log = AuditLog(
        user_id=test_admin.id,
        action=ActionType.SYSTEM,
        details="in-range-log",
        created_at=datetime.utcnow() - timedelta(days=1),
    )
    db.add_all([old_log, in_range_log])
    db.commit()

    date_from = (datetime.utcnow() - timedelta(days=5)).date().isoformat()
    date_to = datetime.utcnow().date().isoformat()
    response = client.get(
        "/api/v1/audit/export",
        headers=manager_headers,
        params={"format": "csv", "date_from": date_from, "date_to": date_to},
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")

    rows = list(csv.DictReader(io.StringIO(response.text)))
    details_values = {row.get("details") for row in rows}
    assert "in-range-log" in details_values
    assert "old-log-outside-window" not in details_values

    editor_response = client.get("/api/v1/audit/export", headers=auth_headers)
    assert editor_response.status_code == 403

    viewer_response = client.get("/api/v1/audit/export", headers=viewer_auth_headers)
    assert viewer_response.status_code == 403


def test_signed_visibility_change_audit_record_is_verifiable(
    client,
    db,
    admin_headers,
    test_admin,
):
    created = _create_document_with_visibility(
        client,
        admin_headers,
        title="Signed visibility log",
        visibility="internal",
    )
    document_id = created["id"]

    update_response = client.put(
        f"/api/v1/documents/{document_id}",
        headers={**admin_headers, "If-Match": created["etag"]},
        json={
            "visibility": "public",
            "reason": "Release approved for public publication",
        },
    )
    assert update_response.status_code == 200

    audit_row = (
        db.query(AuditLog)
        .filter(
            AuditLog.document_id == document_id,
            AuditLog.audience_event_type == AudienceEventType.VISIBILITY_CHANGED,
        )
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit_row is not None
    assert audit_row.signature_key_id is not None
    assert audit_row.signature is not None

    details = json.loads(audit_row.details or "{}")
    signed_payload = {
        "event": AudienceEventType.VISIBILITY_CHANGED.value,
        "document_id": int(document_id),
        "user_id": int(test_admin.id),
        "from_visibility": details.get("from_visibility"),
        "to_visibility": details.get("to_visibility"),
        "reason": details.get("reason"),
    }
    assert verify_payload_signature(
        signed_payload,
        key_id=audit_row.signature_key_id,
        signature=audit_row.signature,
    )


def test_exposure_risk_and_assignment_churn_metrics(
    client,
    db,
    system_admin_headers,
    manager_headers,
    test_tenant,
    test_tenant_2,
):
    exposure_doc = _create_document_with_visibility(
        client,
        system_admin_headers,
        title="Exposure transition doc",
        visibility="internal",
    )
    exposure_update = client.put(
        f"/api/v1/documents/{exposure_doc['id']}",
        headers={**system_admin_headers, "If-Match": exposure_doc["etag"]},
        json={"visibility": "public", "reason": "Intentional public release"},
    )
    assert exposure_update.status_code == 200

    churn_doc = _create_document_with_visibility(
        client,
        system_admin_headers,
        title="Churn metric doc",
        visibility="company",
        company_ids=[test_tenant.id],
    )

    assign_response = client.post(
        f"/api/v1/documents/{churn_doc['id']}/assign-companies",
        headers={**system_admin_headers, "If-Match": churn_doc["etag"]},
        json={"company_ids": [test_tenant.id, test_tenant_2.id]},
    )
    assert assign_response.status_code == 200
    next_etag = assign_response.headers["ETag"]

    remove_response = client.delete(
        f"/api/v1/documents/{churn_doc['id']}/assign-companies/{test_tenant_2.id}",
        headers={**system_admin_headers, "If-Match": next_etag},
    )
    assert remove_response.status_code == 200

    overview_response = client.get("/api/v1/analytics/overview", headers=manager_headers)
    assert overview_response.status_code == 200
    overview = overview_response.json()
    assert int(overview["exposure_risk_transitions_30d"]) >= 1

    churn_entries = {
        int(item["document_id"]): int(item["churn_count"])
        for item in overview["assignment_churn_90d"]
    }
    assert churn_entries.get(churn_doc["id"], 0) >= 2

    churn_endpoint_response = client.get(
        f"/api/v1/analytics/documents/{churn_doc['id']}/audience-churn",
        headers=manager_headers,
    )
    assert churn_endpoint_response.status_code == 200
    assert int(churn_endpoint_response.json()["assignment_churn_90d"]) >= 2


def test_document_audience_churn_requires_document_in_manager_scope(
    client,
    db,
    manager_headers,
    test_admin,
    test_tenant_2,
):
    other_tenant_doc = Document(
        title="Other tenant churn doc",
        document_number="DOC-CHURN-OTHER-001",
        status=DocumentStatus.DRAFT,
        visibility=DocumentVisibility.INTERNAL,
        tenant_id=test_tenant_2.id,
        created_by=test_admin.id,
    )
    db.add(other_tenant_doc)
    db.commit()
    db.refresh(other_tenant_doc)

    response = client.get(
        f"/api/v1/analytics/documents/{other_tenant_doc.id}/audience-churn",
        headers=manager_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


def test_audit_export_redacts_pii_for_non_system_admin(
    client,
    db,
    manager_headers,
    system_admin_headers,
    test_admin,
):
    pii_log = AuditLog(
        user_id=test_admin.id,
        action=ActionType.SYSTEM,
        details="contact admin@example.com from 198.51.100.42",
        ip_address="198.51.100.42",
        created_at=datetime.utcnow(),
    )
    db.add(pii_log)
    db.commit()

    admin_response = client.get("/api/v1/audit/export", headers=system_admin_headers)
    assert admin_response.status_code == 200
    admin_items = admin_response.json()["items"]
    admin_row = next(item for item in admin_items if int(item["id"]) == pii_log.id)
    assert admin_row["user_email"] == test_admin.email
    assert admin_row["ip_address"] == "198.51.100.42"
    assert "admin@example.com" in (admin_row["details"] or "")

    manager_response = client.get("/api/v1/audit/export", headers=manager_headers)
    assert manager_response.status_code == 200
    manager_items = manager_response.json()["items"]
    manager_row = next(item for item in manager_items if int(item["id"]) == pii_log.id)
    assert manager_row["user_email"] == "[redacted-email]"
    assert manager_row["ip_address"] == "[redacted-ip]"
    assert "[redacted-email]" in (manager_row["details"] or "")
