import json

from app.models import ActionType, AuditLog


def test_system_settings_update_creates_audit_log(client, db, system_admin_headers):
    payload = {"settings": {"site_name": "DocsPortal", "max_upload_mb": 50}}
    response = client.put("/api/v1/system/settings", headers=system_admin_headers, json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["settings"]["site_name"] == "DocsPortal"
    assert data["settings"]["max_upload_mb"] == 50

    log = db.query(AuditLog).filter(AuditLog.action == ActionType.SYSTEM).first()
    assert log is not None
    details = json.loads(log.details)
    assert details["event"] == "system_settings_updated"
