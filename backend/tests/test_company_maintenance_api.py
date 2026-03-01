"""Regression tests for company maintenance lifecycle endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from app.models import (
    Document,
    DocumentStatus,
    DocumentVisibility,
    Invitation,
    InvitationStatus,
    UserRole,
)
from tests.factories import create_tenant, create_user


def _create_document(
    db,
    *,
    created_by: int,
    tenant_id: int | None = None,
    visibility: DocumentVisibility = DocumentVisibility.INTERNAL,
    status: DocumentStatus = DocumentStatus.DRAFT,
) -> Document:
    doc = Document(
        title=f"Maintenance Doc {uuid.uuid4().hex[:8]}",
        document_number=f"DOC-MAINT-{uuid.uuid4().hex[:10].upper()}",
        description="maintenance test document",
        status=status,
        visibility=visibility,
        created_by=created_by,
        tenant_id=tenant_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def _create_pending_invitation(db, *, tenant_id: int, invited_by: int, email_prefix: str) -> Invitation:
    invitation = Invitation(
        email=f"{email_prefix}-{uuid.uuid4().hex[:8]}@example.com",
        token=f"token-{uuid.uuid4().hex}",
        role=UserRole.CUSTOMER,
        tenant_id=tenant_id,
        invited_by=invited_by,
        status=InvitationStatus.PENDING,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation


def test_deactivate_impact_report_counts_dependencies(
    client,
    db,
    system_admin_headers,
    test_system_admin,
    test_tenant,
):
    _create_document(
        db,
        created_by=test_system_admin.id,
        tenant_id=test_tenant.id,
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.INTERNAL,
    )
    assigned = _create_document(
        db,
        created_by=test_system_admin.id,
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.COMPANY,
    )
    assigned.assigned_companies.append(test_tenant)
    db.commit()

    _create_pending_invitation(
        db,
        tenant_id=test_tenant.id,
        invited_by=test_system_admin.id,
        email_prefix="impact",
    )

    response = client.get(
        f"/api/v1/companies/maintenance/deactivate-impact/{test_tenant.id}",
        headers=system_admin_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["impact"]["owned_document_count"] == 1
    assert payload["impact"]["assigned_document_count"] == 1
    assert payload["impact"]["pending_invitation_count"] == 1
    assert payload["impact"]["active_customer_visible_document_count"] == 1


def test_merge_plan_reports_conflicting_assignments(
    client,
    db,
    system_admin_headers,
    test_system_admin,
):
    source = create_tenant(db, name="Merge Source", slug=f"merge-source-{uuid.uuid4().hex[:6]}")
    target = create_tenant(db, name="Merge Target", slug=f"merge-target-{uuid.uuid4().hex[:6]}")

    create_user(
        db,
        email=f"merge-user-{uuid.uuid4().hex[:6]}@example.com",
        username=f"merge_user_{uuid.uuid4().hex[:6]}",
        role=UserRole.CUSTOMER,
        tenant_id=source.id,
        plain_password="merge-pass-123",
    )
    _create_pending_invitation(
        db,
        tenant_id=source.id,
        invited_by=test_system_admin.id,
        email_prefix="merge",
    )

    _create_document(
        db,
        created_by=test_system_admin.id,
        tenant_id=source.id,
        status=DocumentStatus.DRAFT,
    )
    overlap = _create_document(
        db,
        created_by=test_system_admin.id,
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.COMPANY,
    )
    overlap.assigned_companies.extend([source, target])
    db.commit()

    response = client.get(
        f"/api/v1/companies/maintenance/merge-plan/{source.id}/{target.id}",
        headers=system_admin_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["can_merge"] is True
    assert payload["impact_summary"]["owned_documents"] == 1
    assert payload["impact_summary"]["assigned_documents"] >= 1
    assert payload["impact_summary"]["assignment_conflicts"] == 1
    assert payload["impact_summary"]["users_to_transfer"] == 1
    assert payload["impact_summary"]["pending_invitations_to_transfer"] == 1


def test_rename_propagation_detects_slug_conflict(
    client,
    db,
    system_admin_headers,
):
    tenant = create_tenant(db, name="Rename Source", slug=f"rename-source-{uuid.uuid4().hex[:6]}")
    conflicting = create_tenant(db, name="Rename Conflict", slug=f"rename-conflict-{uuid.uuid4().hex[:6]}")

    response = client.get(
        f"/api/v1/companies/maintenance/rename-propagation/{tenant.id}",
        params={"new_slug": conflicting.slug},
        headers=system_admin_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["can_rename"] is False
    assert any("already used" in blocker for blocker in payload["blockers"])


def test_hard_delete_safety_reports_blockers(
    client,
    db,
    system_admin_headers,
    test_system_admin,
    test_tenant,
):
    create_user(
        db,
        email=f"delete-user-{uuid.uuid4().hex[:6]}@example.com",
        username=f"delete_user_{uuid.uuid4().hex[:6]}",
        role=UserRole.CUSTOMER,
        tenant_id=test_tenant.id,
        plain_password="delete-pass-123",
    )
    _create_pending_invitation(
        db,
        tenant_id=test_tenant.id,
        invited_by=test_system_admin.id,
        email_prefix="delete",
    )
    _create_document(
        db,
        created_by=test_system_admin.id,
        tenant_id=test_tenant.id,
        status=DocumentStatus.ACTIVE,
    )

    response = client.get(
        f"/api/v1/companies/maintenance/deletion-safety/{test_tenant.id}",
        headers=system_admin_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["can_hard_delete"] is False
    assert payload["counts"]["users"] >= 1
    assert payload["counts"]["invitations_total"] >= 1
    assert payload["counts"]["owned_documents"] >= 1
    assert payload["blockers"]


def test_hierarchy_baseline_supports_parent_assignment_and_cycle_guard(
    client,
    db,
    system_admin_headers,
):
    root = create_tenant(db, name="Hierarchy Root", slug=f"hier-root-{uuid.uuid4().hex[:6]}")
    child = create_tenant(db, name="Hierarchy Child", slug=f"hier-child-{uuid.uuid4().hex[:6]}")
    grandchild = create_tenant(
        db,
        name="Hierarchy Grandchild",
        slug=f"hier-grand-{uuid.uuid4().hex[:6]}",
    )

    set_child_parent = client.put(
        f"/api/v1/companies/maintenance/hierarchy/{child.id}/parent",
        headers=system_admin_headers,
        json={"parent_company_id": root.id},
    )
    assert set_child_parent.status_code == 200

    set_grand_parent = client.put(
        f"/api/v1/companies/maintenance/hierarchy/{grandchild.id}/parent",
        headers=system_admin_headers,
        json={"parent_company_id": child.id},
    )
    assert set_grand_parent.status_code == 200

    cycle_attempt = client.put(
        f"/api/v1/companies/maintenance/hierarchy/{root.id}/parent",
        headers=system_admin_headers,
        json={"parent_company_id": grandchild.id},
    )
    assert cycle_attempt.status_code == 400
    assert "cycle" in cycle_attempt.json()["detail"].lower()

    hierarchy = client.get(
        f"/api/v1/companies/maintenance/hierarchy/{grandchild.id}",
        headers=system_admin_headers,
    )
    assert hierarchy.status_code == 200
    payload = hierarchy.json()
    assert payload["parent_company_id"] == child.id
    assert payload["ancestry_path"] == [root.id, child.id, grandchild.id]
    assert payload["depth"] == 2


def test_archive_validation_counts_assigned_documents_via_tenant_column(
    client,
    db,
    system_admin_headers,
    test_system_admin,
):
    tenant = create_tenant(db, name="Archive Scope", slug=f"archive-scope-{uuid.uuid4().hex[:6]}")
    assigned = _create_document(
        db,
        created_by=test_system_admin.id,
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.COMPANY,
    )
    assigned.assigned_companies.append(tenant)
    db.commit()

    response = client.get(
        f"/api/v1/companies/maintenance/archive-validation/{tenant.id}",
        headers=system_admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["assigned_documents"] == 1
