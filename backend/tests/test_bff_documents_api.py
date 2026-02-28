"""Tests for BFF document endpoints."""

from __future__ import annotations

import uuid

from app.models import (
    Attachment,
    Document,
    DocumentStatus,
    DocumentVisibility,
    ReviewRequest,
    ReviewStatus,
    Tenant,
)


def test_document_detail_page_bundle_returns_composed_payload(
    client,
    db,
    auth_headers,
    test_user,
    test_tenant,
):
    test_user.tenant_id = test_tenant.id
    db.commit()

    document = Document(
        title="BFF Detail Document",
        document_number=f"DOC-BFF-{uuid.uuid4().hex[:6].upper()}",
        description="Bundled detail page payload",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.COMPANY,
        created_by=test_user.id,
        tenant_id=test_tenant.id,
    )
    db.add(document)
    db.flush()
    document.assigned_companies.append(test_tenant)

    attachment = Attachment(
        document_id=document.id,
        filename="spec.pdf",
        original_filename="spec.pdf",
        file_size=128,
        size_bytes=128,
        mime_type="application/pdf",
        storage_path="uploads/spec.pdf",
        storage_key="uploads/spec.pdf",
        uploaded_by=test_user.id,
    )
    review = ReviewRequest(
        document_id=document.id,
        submitted_by=test_user.id,
        status=ReviewStatus.PENDING,
        message="Please review",
    )
    db.add_all([attachment, review])
    db.commit()

    response = client.get(
        f"/api/v1/bff/documents/{document.id}/detail-page",
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["document"]["id"] == document.id
    assert len(payload["attachments"]) == 1
    assert payload["attachments"][0]["id"] == attachment.id
    assert len(payload["assigned_companies"]) == 1
    assert payload["assigned_companies"][0]["id"] == test_tenant.id
    assert payload["review_history"]["total"] == 1
    assert payload["review_history"]["items"][0]["id"] == review.id


def test_document_detail_page_bundle_is_tenant_scoped(client, db, auth_headers, test_user):
    tenant_a = Tenant(
        name="Bff Tenant A",
        slug=f"bff-tenant-a-{uuid.uuid4().hex[:6]}",
        is_active=True,
        company_type="customer",
    )
    tenant_b = Tenant(
        name="Bff Tenant B",
        slug=f"bff-tenant-b-{uuid.uuid4().hex[:6]}",
        is_active=True,
        company_type="customer",
    )
    db.add_all([tenant_a, tenant_b])
    db.commit()
    db.refresh(tenant_a)
    db.refresh(tenant_b)

    test_user.tenant_id = tenant_a.id
    db.commit()

    cross_tenant_document = Document(
        title="Cross Tenant Bundle",
        document_number=f"DOC-BFF-XTEN-{uuid.uuid4().hex[:6].upper()}",
        status=DocumentStatus.DRAFT,
        visibility=DocumentVisibility.INTERNAL,
        created_by=test_user.id,
        tenant_id=tenant_b.id,
    )
    db.add(cross_tenant_document)
    db.commit()

    response = client.get(
        f"/api/v1/bff/documents/{cross_tenant_document.id}/detail-page",
        headers=auth_headers,
    )

    assert response.status_code == 404

