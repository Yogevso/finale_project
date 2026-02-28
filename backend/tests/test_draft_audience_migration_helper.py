"""Tests for Wave P draft audience migration helper."""

from app.migrations import DraftAudienceMigrationStrategy, run_draft_audience_migration
from app.models import ActionType, AuditLog, DocumentStatus, DocumentVisibility
from tests.factories import create_document, create_tenant


def _create_invalid_draft_company_document(db, *, created_by: int, tenant_id: int | None = None):
    return create_document(
        db,
        created_by=created_by,
        tenant_id=tenant_id,
        status=DocumentStatus.DRAFT,
        visibility=DocumentVisibility.COMPANY,
    )


def test_draft_audience_migration_dry_run_does_not_mutate_state(db, test_admin, test_tenant):
    document = _create_invalid_draft_company_document(
        db,
        created_by=test_admin.id,
        tenant_id=test_tenant.id,
    )

    report = run_draft_audience_migration(
        db,
        strategy=DraftAudienceMigrationStrategy.AUTO,
        apply_changes=False,
    )

    assert report.mode == "dry-run"
    assert report.total_candidates == 1
    assert report.applied_count == 0
    assert report.unresolved_count == 0
    assert report.planned_actions[0].action.value == "assign_owner"

    db.refresh(document)
    assert document.visibility == DocumentVisibility.COMPANY
    assert document.assigned_companies == []
    assert db.query(AuditLog).filter(AuditLog.document_id == document.id).count() == 0


def test_draft_audience_migration_apply_assigns_owner_and_is_idempotent(
    db, test_admin, test_tenant
):
    document = _create_invalid_draft_company_document(
        db,
        created_by=test_admin.id,
        tenant_id=test_tenant.id,
    )

    first = run_draft_audience_migration(
        db,
        strategy=DraftAudienceMigrationStrategy.AUTO,
        apply_changes=True,
        actor_user_id=test_admin.id,
    )

    db.refresh(document)
    assert first.mode == "apply"
    assert first.total_candidates == 1
    assert first.applied_count == 1
    assert first.unresolved_count == 0
    assert sorted(company.id for company in document.assigned_companies) == [test_tenant.id]

    audit_count_after_first = (
        db.query(AuditLog)
        .filter(
            AuditLog.document_id == document.id,
            AuditLog.action == ActionType.SYSTEM,
        )
        .count()
    )
    assert audit_count_after_first == 1

    second = run_draft_audience_migration(
        db,
        strategy=DraftAudienceMigrationStrategy.AUTO,
        apply_changes=True,
        actor_user_id=test_admin.id,
    )

    assert second.total_candidates == 0
    assert second.applied_count == 0
    assert second.audit_entries_created == 0
    assert (
        db.query(AuditLog)
        .filter(
            AuditLog.document_id == document.id,
            AuditLog.action == ActionType.SYSTEM,
        )
        .count()
        == audit_count_after_first
    )


def test_draft_audience_migration_apply_demotes_when_owner_tenant_is_inactive(db, test_admin):
    inactive_tenant = create_tenant(
        db,
        name="Inactive Owner",
        slug="inactive-owner",
        is_active=False,
    )
    document = _create_invalid_draft_company_document(
        db,
        created_by=test_admin.id,
        tenant_id=inactive_tenant.id,
    )

    report = run_draft_audience_migration(
        db,
        strategy=DraftAudienceMigrationStrategy.AUTO,
        apply_changes=True,
        actor_user_id=test_admin.id,
    )

    db.refresh(document)
    assert report.total_candidates == 1
    assert report.applied_count == 1
    assert report.unresolved_count == 0
    assert report.planned_actions[0].action.value == "demote_internal"
    assert document.visibility == DocumentVisibility.INTERNAL
    assert document.assigned_companies == []
