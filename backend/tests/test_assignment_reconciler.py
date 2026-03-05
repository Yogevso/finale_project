"""Tests for assignment reconciliation worker/service."""

from __future__ import annotations

import json

from app.models import AuditLog, Document, DocumentStatus, DocumentVisibility
from app.services.assignment_reconciler import process_assignment_reconciliation_batch


def test_assignment_reconciler_removes_inactive_company_assignments(
    db,
    test_admin,
    test_tenant,
    test_tenant_2,
):
    test_tenant_2.is_active = False
    document = Document(
        title="Reconciler mixed assignment document",
        document_number="DOC-RECON-0001",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.COMPANY,
        created_by=test_admin.id,
    )
    document.assigned_companies = [test_tenant, test_tenant_2]
    db.add(document)
    db.commit()
    db.refresh(document)

    report = process_assignment_reconciliation_batch(db=db, batch_size=25)
    db.refresh(document)

    assert report.attempted == 1
    assert report.completed == 1
    assert report.recovered == 1
    assert sorted(company.id for company in document.assigned_companies) == [test_tenant.id]
    assert document.visibility == DocumentVisibility.COMPANY

    audit_rows = db.query(AuditLog).filter(AuditLog.document_id == document.id).all()
    assert len(audit_rows) == 1
    details = json.loads(audit_rows[0].details or "{}")
    assert details.get("event") == "assignment_reconciler_cleanup"
    assert details.get("removed_inactive_company_ids") == [test_tenant_2.id]


def test_assignment_reconciler_downgrades_visibility_when_no_active_companies_remain(
    db,
    test_admin,
    test_tenant,
):
    test_tenant.is_active = False
    document = Document(
        title="Reconciler full-orphan document",
        document_number="DOC-RECON-0002",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.COMPANY,
        created_by=test_admin.id,
    )
    document.assigned_companies = [test_tenant]
    db.add(document)
    db.commit()
    db.refresh(document)

    report = process_assignment_reconciliation_batch(db=db, batch_size=25)
    db.refresh(document)

    assert report.attempted == 1
    assert report.completed == 1
    assert report.recovered == 1
    assert document.assigned_companies == []
    assert document.visibility == DocumentVisibility.INTERNAL

    audit_row = db.query(AuditLog).filter(AuditLog.document_id == document.id).one()
    details = json.loads(audit_row.details or "{}")
    assert details.get("visibility_downgraded_to_internal") is True


def test_assignment_reconciler_returns_empty_report_when_nothing_to_reconcile(db):
    report = process_assignment_reconciliation_batch(db=db, batch_size=25)

    assert report.attempted == 0
    assert report.completed == 0
    assert report.recovered == 0
