"""Wave U tenant-isolation tests for assignment endpoints."""

from __future__ import annotations

from app.models import Document, DocumentStatus, DocumentVisibility, Tenant, User, UserRole
from app.security import get_password_hash


def _login_headers(client, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _build_tenant_scoped_assignment_scenario(db):
    tenant_a = Tenant(
        name="Tenant A",
        slug="wave-u-tenant-a",
        is_active=True,
        company_type="customer",
    )
    tenant_b = Tenant(
        name="Tenant B",
        slug="wave-u-tenant-b",
        is_active=True,
        company_type="customer",
    )
    db.add_all([tenant_a, tenant_b])
    db.flush()

    tenant_a_manager = User(
        email="tenant-a-manager@example.com",
        username="tenant_a_manager",
        full_name="Tenant A Manager",
        hashed_password=get_password_hash("manager123"),
        role=UserRole.MANAGER,
        tenant_id=tenant_a.id,
        is_active=True,
    )
    db.add(tenant_a_manager)
    db.flush()

    document = Document(
        title="Tenant-scoped audience document",
        document_number="DOC-WAVE-U-TENANT-0001",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.COMPANY,
        created_by=tenant_a_manager.id,
        tenant_id=tenant_a.id,
    )
    document.assigned_companies = [tenant_a]
    db.add(document)
    db.commit()
    db.refresh(document)
    db.refresh(tenant_b)
    return tenant_b.id, document.id, document.etag


def test_tenant_manager_cannot_assign_foreign_company_to_owned_document(client, db):
    foreign_company_id, document_id, etag = _build_tenant_scoped_assignment_scenario(db)
    manager_headers = _login_headers(client, "tenant_a_manager", "manager123")

    response = client.post(
        f"/api/v1/documents/{document_id}/assign-companies",
        headers={**manager_headers, "If-Match": etag},
        json={"company_ids": [foreign_company_id]},
    )

    assert response.status_code in {403, 404}


def test_tenant_manager_cannot_bulk_assign_foreign_company_to_owned_document(client, db):
    foreign_company_id, document_id, etag = _build_tenant_scoped_assignment_scenario(db)
    manager_headers = _login_headers(client, "tenant_a_manager", "manager123")

    response = client.post(
        f"/api/v1/documents/{document_id}/companies/bulk",
        headers={
            **manager_headers,
            "If-Match": etag,
            "Idempotency-Key": "wave-u-tenant-bulk-attack-1",
        },
        json={"company_ids": [foreign_company_id]},
    )

    assert response.status_code in {403, 404}
