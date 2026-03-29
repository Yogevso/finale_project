import json
from datetime import datetime

from app.models import ActionType, AuditLog, DocumentStatus, SystemSetting, UserRole, Version
from app.services.system_document_lifecycle_settings_service import (
    DOCUMENT_LIFECYCLE_SETTINGS_KEY,
    DocumentLifecycleSettingsMetadata,
    ResolvedDocumentLifecycleSettings,
    subtract_retention_window,
)
from app.workers.cleanup_worker import auto_archive_published_documents
from tests.factories import create_document, create_user


def _payload(**overrides):
    base = {
        "auto_archive_enabled": True,
        "auto_archive_after_value": 1,
        "auto_archive_after_unit": "years",
    }
    base.update(overrides)
    return base


def test_system_document_lifecycle_settings_default_shape(client, system_admin_headers):
    response = client.get("/api/v1/system/settings/document-lifecycle", headers=system_admin_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "default"
    assert payload["settings"]["auto_archive_enabled"] is False
    assert payload["settings"]["auto_archive_after_value"] == 12
    assert payload["settings"]["auto_archive_after_unit"] == "months"
    assert payload["settings"]["auto_archive_basis"] == "last_published"
    assert payload["settings"]["delete_grace_days"] == 30


def test_system_document_lifecycle_settings_update_is_internal_and_audited(
    client, db, system_admin_headers
):
    response = client.put(
        "/api/v1/system/settings/document-lifecycle",
        headers=system_admin_headers,
        json=_payload(auto_archive_after_value=18, auto_archive_after_unit="months"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "database"
    assert payload["settings"]["auto_archive_enabled"] is True
    assert payload["settings"]["auto_archive_after_value"] == 18
    assert payload["settings"]["auto_archive_after_unit"] == "months"

    row = db.query(SystemSetting).filter(SystemSetting.key == DOCUMENT_LIFECYCLE_SETTINGS_KEY).one()
    stored = json.loads(row.value)
    assert stored["auto_archive_enabled"] is True
    assert stored["auto_archive_after_value"] == 18
    assert stored["auto_archive_after_unit"] == "months"

    generic_get = client.get("/api/v1/system/settings", headers=system_admin_headers)
    assert generic_get.status_code == 200
    assert DOCUMENT_LIFECYCLE_SETTINGS_KEY not in generic_get.json()["settings"]

    log = db.query(AuditLog).filter(AuditLog.action == ActionType.SYSTEM).order_by(AuditLog.id.desc()).first()
    assert log is not None
    details = json.loads(log.details)
    assert details["event"] == "system_document_lifecycle_settings_updated"


def test_auto_archive_published_documents_uses_latest_published_age(db, monkeypatch):
    now = datetime(2026, 3, 28, 12, 0, 0)
    sysadmin = create_user(db, role=UserRole.SYSTEM_ADMIN)

    class _SessionProxy:
        def __init__(self, session):
            self._session = session

        def __getattr__(self, name):
            return getattr(self._session, name)

        def close(self):
            return None

    class _FakeChatSession:
        def query(self, *_args, **_kwargs):
            return self

        def filter(self, *_args, **_kwargs):
            return self

        def update(self, *_args, **_kwargs):
            return 0

        def commit(self):
            return None

        def close(self):
            return None

    monkeypatch.setattr(
        "app.workers.cleanup_worker._document_model_columns_available",
        lambda _db: True,
    )
    monkeypatch.setattr(
        "app.workers.cleanup_worker.SessionLocal",
        lambda: _SessionProxy(db),
    )
    monkeypatch.setattr(
        "app.workers.cleanup_worker.ChatSessionLocal",
        lambda: _FakeChatSession(),
    )
    monkeypatch.setattr(
        "app.workers.cleanup_worker.SystemDocumentLifecycleSettingsService.get_effective_settings",
        lambda _db: (
            ResolvedDocumentLifecycleSettings(
                auto_archive_enabled=True,
                auto_archive_after_value=6,
                auto_archive_after_unit="months",
                auto_archive_basis="last_published",
                delete_grace_days=30,
                source="database",
            ),
            DocumentLifecycleSettingsMetadata(
                source="database",
                updated_at=now,
                updated_by=sysadmin.id,
            ),
        ),
    )

    old_doc = create_document(
        db,
        created_by=sysadmin.id,
        status=DocumentStatus.ACTIVE,
        title="Old published doc",
    )
    old_version = Version(
        document_id=old_doc.id,
        version_number=1,
        content="old",
        is_published=True,
        published_at=datetime(2025, 8, 1, 9, 0, 0),
        created_by=sysadmin.id,
        published_by=sysadmin.id,
    )

    recent_doc = create_document(
        db,
        created_by=sysadmin.id,
        status=DocumentStatus.ACTIVE,
        title="Recent published doc",
    )
    recent_version = Version(
        document_id=recent_doc.id,
        version_number=1,
        content="recent",
        is_published=True,
        published_at=datetime(2026, 2, 20, 9, 0, 0),
        created_by=sysadmin.id,
        published_by=sysadmin.id,
    )

    never_published_doc = create_document(
        db,
        created_by=sysadmin.id,
        status=DocumentStatus.ACTIVE,
        title="Never published doc",
    )
    db.add_all([old_version, recent_version])
    db.commit()

    archived_count = auto_archive_published_documents(now, dry_run=False)

    db.refresh(old_doc)
    db.refresh(recent_doc)
    db.refresh(never_published_doc)

    assert archived_count == 1
    assert old_doc.status == DocumentStatus.ARCHIVED
    assert recent_doc.status == DocumentStatus.ACTIVE
    assert never_published_doc.status == DocumentStatus.ACTIVE


def test_subtract_retention_window_clamps_calendar_boundaries():
    source = datetime(2026, 3, 31, 14, 30, 0)

    one_month = subtract_retention_window(source, count=1, unit="months")
    one_year = subtract_retention_window(source, count=1, unit="years")

    assert one_month == datetime(2026, 2, 28, 14, 30, 0)
    assert one_year == datetime(2025, 3, 31, 14, 30, 0)
