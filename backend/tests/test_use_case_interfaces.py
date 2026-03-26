"""Tests for explicit application use-case service interfaces."""

from datetime import datetime, timedelta

import pytest

from app.application.interfaces.dependencies import (
    get_assign_company_set_use_case,
    get_publish_approved_version_use_case,
)
from app.application.interfaces.use_cases import AssignCompanySet, PublishApprovedVersion
from app.dependencies.tenant import TenantContext
from app.errors import ValidationError
from app.models import AuditLog, Document, DocumentStatus, DocumentVisibility, UserRole
from app.services.document_service import DocumentService
from app.services.version_service import VersionService


def test_publish_use_case_provider_returns_contract_implementation(db):
    use_case = get_publish_approved_version_use_case(db)

    assert isinstance(use_case, VersionService)
    assert isinstance(use_case, PublishApprovedVersion)


def test_version_service_publish_use_case_alias_delegates(db, test_user, monkeypatch):
    service = VersionService(db)
    expected = {"status": "ok"}
    calls: dict[str, object] = {}

    def fake_publish(document_id: int, version_id: int, current_user):
        calls["document_id"] = document_id
        calls["version_id"] = version_id
        calls["current_user"] = current_user
        return expected

    monkeypatch.setattr(service, "publish_version", fake_publish)

    result = service.publish_approved_version(12, 34, test_user)

    assert result == expected
    assert calls["document_id"] == 12
    assert calls["version_id"] == 34
    assert calls["current_user"] == test_user


def test_version_service_publish_delegates_to_publication_service(db, test_user, monkeypatch):
    service = VersionService(db)
    expected = {"published": True}
    calls: dict[str, object] = {}

    def fake_publish(document_id: int, version_id: int, current_user):
        calls["document_id"] = document_id
        calls["version_id"] = version_id
        calls["current_user"] = current_user
        return expected

    monkeypatch.setattr(service.publication_service, "publish_version", fake_publish)

    result = service.publish_version(77, 88, test_user)

    assert result == expected
    assert calls["document_id"] == 77
    assert calls["version_id"] == 88
    assert calls["current_user"] == test_user


def test_version_service_schedule_delegates_to_scheduling_service(db, test_user, monkeypatch):
    service = VersionService(db)
    expected = {"scheduled": True}
    calls: dict[str, object] = {}
    scheduled_at = datetime.utcnow() + timedelta(hours=1)

    def fake_schedule(document_id: int, version_id: int, when: datetime, current_user):
        calls["document_id"] = document_id
        calls["version_id"] = version_id
        calls["scheduled_at"] = when
        calls["current_user"] = current_user
        return expected

    monkeypatch.setattr(service.scheduling_service, "schedule_publish", fake_schedule)

    result = service.schedule_publish(55, 66, scheduled_at, test_user)

    assert result == expected
    assert calls["document_id"] == 55
    assert calls["version_id"] == 66
    assert calls["scheduled_at"] == scheduled_at
    assert calls["current_user"] == test_user


def test_assign_use_case_provider_returns_contract_implementation(db, test_admin):
    tenant_ctx = TenantContext(
        tenant_id=test_admin.tenant_id,
        user_id=test_admin.id,
        user_role=test_admin.role,
        is_system_admin=test_admin.role == UserRole.SYSTEM_ADMIN,
    )
    use_case = get_assign_company_set_use_case(db, tenant_ctx)

    assert isinstance(use_case, DocumentService)
    assert isinstance(use_case, AssignCompanySet)


def test_assign_company_set_use_case_replaces_assignments(
    db, test_admin, test_tenant, test_tenant_2
):
    document = Document(
        title="Use-case assignment document",
        document_number="DOC-USE-CASE-0001",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.COMPANY,
        created_by=test_admin.id,
        tenant_id=test_admin.tenant_id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    service = DocumentService(db)

    assigned_count = service.assign_company_set(
        document.id,
        [test_tenant.id, test_tenant.id, test_tenant_2.id],
    )
    assert assigned_count == 2
    db.refresh(document)
    assert sorted(company.id for company in document.assigned_companies) == sorted(
        [test_tenant.id, test_tenant_2.id]
    )


def test_assign_company_set_use_case_replay_is_state_idempotent(
    db, test_admin, test_tenant, test_tenant_2
):
    document = Document(
        title="Use-case replay-safe assignment document",
        document_number="DOC-USE-CASE-0002",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.COMPANY,
        created_by=test_admin.id,
        tenant_id=test_admin.tenant_id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    service = DocumentService(db)
    first_count = service.assign_company_set(
        document.id,
        [test_tenant.id, test_tenant_2.id],
    )
    assert first_count == 2
    db.refresh(document)
    row_version_after_first = int(document.row_version)
    etag_after_first = document.etag
    audit_count_after_first = db.query(AuditLog).filter(AuditLog.document_id == document.id).count()

    replay_count = service.assign_company_set(
        document.id,
        [test_tenant_2.id, test_tenant.id],
    )
    assert replay_count == 2

    db.refresh(document)
    assert sorted(company.id for company in document.assigned_companies) == sorted(
        [test_tenant.id, test_tenant_2.id]
    )
    assert int(document.row_version) == row_version_after_first
    assert document.etag == etag_after_first
    assert db.query(AuditLog).filter(AuditLog.document_id == document.id).count() == audit_count_after_first

    with pytest.raises(ValidationError) as exc_info:
        service.assign_company_set(document.id, [])
    assert exc_info.value.error_code == "missing_company_assignment"

    db.refresh(document)
    assert sorted(company.id for company in document.assigned_companies) == sorted(
        [test_tenant.id, test_tenant_2.id]
    )
