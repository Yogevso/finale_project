"""Regression tests for idempotency-key handling on write endpoints."""

from __future__ import annotations

import uuid

from app.models import (
    Comment,
    Document,
    DocumentStatus,
    DocumentVisibility,
    DomainEventOutbox,
    Invitation,
)


def _new_idempotency_key() -> str:
    return f"idem-{uuid.uuid4().hex}"


def test_duplicate_comment_create_replays_response(client, db, admin_token, sample_document):
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Idempotency-Key": _new_idempotency_key(),
    }
    path = f"/api/v1/documents/{sample_document['id']}/comments"
    payload = {"content": "idempotent comment payload"}

    first = client.post(path, headers=headers, json=payload)
    second = client.post(path, headers=headers, json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.headers.get("x-idempotent-replay") == "true"
    assert second.json() == first.json()

    comment_id = first.json()["id"]
    assert db.query(Comment).filter(Comment.id == comment_id).count() == 1
    assert db.query(Comment).filter(Comment.document_id == sample_document["id"]).count() == 1


def test_reused_key_with_different_comment_payload_returns_conflict(
    client, db, admin_token, sample_document
):
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Idempotency-Key": _new_idempotency_key(),
    }
    path = f"/api/v1/documents/{sample_document['id']}/comments"

    first = client.post(path, headers=headers, json={"content": "first payload"})
    second = client.post(path, headers=headers, json={"content": "second payload"})

    assert first.status_code == 201
    assert second.status_code == 409
    assert "already used" in second.json()["detail"]
    assert db.query(Comment).filter(Comment.document_id == sample_document["id"]).count() == 1


def test_duplicate_invitation_create_replays_response(client, db, system_admin_headers):
    headers = dict(system_admin_headers)
    headers["Idempotency-Key"] = _new_idempotency_key()

    email = f"idem-invite-{uuid.uuid4().hex[:10]}@example.com"
    payload = {"email": email, "role": "viewer", "message": "welcome"}

    first = client.post("/api/v1/invitations", headers=headers, json=payload)
    second = client.post("/api/v1/invitations", headers=headers, json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.headers.get("x-idempotent-replay") == "true"
    assert second.json() == first.json()

    invitation_id = first.json()["id"]
    assert db.query(Invitation).filter(Invitation.id == invitation_id).count() == 1
    assert db.query(Invitation).filter(Invitation.email == email).count() == 1


def test_duplicate_publish_replays_response_and_avoids_duplicate_side_effects(
    client, db, admin_token, manager_headers, sample_document
):
    auth_headers = {"Authorization": f"Bearer {admin_token}"}

    create_version = client.post(
        f"/api/v1/documents/{sample_document['id']}/versions",
        headers=auth_headers,
        json={"content": "publish me", "changes_summary": "idempotency"},
    )
    assert create_version.status_code == 201
    version_id = create_version.json()["id"]

    submit = client.post(
        f"/api/v1/reviews/documents/{sample_document['id']}/submit",
        headers=auth_headers,
        json={"version_id": version_id, "message": "ready"},
    )
    assert submit.status_code in [200, 201]
    review_id = submit.json()["id"]

    approve = client.post(
        f"/api/v1/reviews/{review_id}/approve",
        headers=manager_headers,
        json={"comments": "ok"},
    )
    assert approve.status_code == 200

    publish_headers = dict(auth_headers)
    publish_headers["Idempotency-Key"] = _new_idempotency_key()
    publish_path = f"/api/v1/documents/{sample_document['id']}/versions/{version_id}/publish"

    first = client.post(publish_path, headers=publish_headers)
    second = client.post(publish_path, headers=publish_headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.headers.get("x-idempotent-replay") == "true"
    assert second.json() == first.json()

    event_key = f"document_published:{version_id}"
    published_event_count = (
        db.query(DomainEventOutbox)
        .filter(
            DomainEventOutbox.event_type == "DocumentPublished",
            DomainEventOutbox.event_key == event_key,
        )
        .count()
    )
    assert published_event_count == 1


def test_duplicate_bulk_company_assignment_replays_response(
    client,
    db,
    system_admin_headers,
    test_admin,
    test_tenant,
):
    document = Document(
        title="Idempotent Bulk Assignment",
        document_number="DOC-IDEMP-BULK-0001",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.COMPANY,
        created_by=test_admin.id,
        tenant_id=test_admin.tenant_id,
    )
    document.assigned_companies = [test_tenant]
    db.add(document)
    db.commit()
    db.refresh(document)

    headers = dict(system_admin_headers)
    headers["Idempotency-Key"] = _new_idempotency_key()
    headers["If-Match"] = document.etag
    path = f"/api/v1/documents/{document.id}/companies/batch"
    payload = {"company_ids": [test_tenant.id]}

    first = client.put(path, headers=headers, json=payload)
    second = client.put(path, headers=headers, json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.headers.get("x-idempotent-replay") == "true"
    assert second.json() == first.json()

