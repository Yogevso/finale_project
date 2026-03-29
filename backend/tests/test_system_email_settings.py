import asyncio

from app.models import SystemSetting
from app.services.email_service import EmailService
from app.services.system_email_settings_service import (
    EMAIL_SETTINGS_KEY,
    SystemEmailSettingsService,
)


def _payload(**overrides):
    base = {
        "enabled": True,
        "host": "smtp.mail.test",
        "port": 587,
        "security": "starttls",
        "username": "mailbox@example.com",
        "password": "smtp-pass-123",
        "clear_password": False,
        "from_email": "mailbox@example.com",
        "from_name": "Ops Mailbox",
    }
    base.update(overrides)
    return base


def test_system_email_settings_update_encrypts_password_and_masks_response(
    client, db, system_admin_headers
):
    response = client.put(
        "/api/v1/system/settings/email",
        headers=system_admin_headers,
        json=_payload(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "database"
    assert payload["settings"]["password_configured"] is True
    assert payload["settings"]["password_masked"] == "********"
    assert payload["settings"]["from_email"] == "mailbox@example.com"

    row = db.query(SystemSetting).filter(SystemSetting.key == EMAIL_SETTINGS_KEY).one()
    assert "smtp-pass-123" not in (row.value or "")

    resolved, metadata = SystemEmailSettingsService.get_effective_settings(db)
    assert resolved.password == "smtp-pass-123"
    assert resolved.security == "starttls"
    assert metadata.source == "database"


def test_system_email_settings_preserves_existing_password_when_omitted(
    client, db, system_admin_headers
):
    first_response = client.put(
        "/api/v1/system/settings/email",
        headers=system_admin_headers,
        json=_payload(password="first-pass-123"),
    )
    assert first_response.status_code == 200

    second_response = client.put(
        "/api/v1/system/settings/email",
        headers=system_admin_headers,
        json=_payload(
            password=None,
            from_email="mailbox2@example.com",
            username="mailbox2@example.com",
        ),
    )
    assert second_response.status_code == 200

    resolved, _metadata = SystemEmailSettingsService.get_effective_settings(db)
    assert resolved.password == "first-pass-123"
    assert resolved.from_email == "mailbox2@example.com"


def test_generic_system_settings_does_not_delete_or_expose_internal_email_settings(
    client, db, system_admin_headers
):
    email_response = client.put(
        "/api/v1/system/settings/email",
        headers=system_admin_headers,
        json=_payload(),
    )
    assert email_response.status_code == 200

    generic_update = client.put(
        "/api/v1/system/settings",
        headers=system_admin_headers,
        json={"settings": {"site_name": "DocsPortal"}},
    )
    assert generic_update.status_code == 200
    assert generic_update.json()["settings"]["site_name"] == "DocsPortal"
    assert EMAIL_SETTINGS_KEY not in generic_update.json()["settings"]

    email_row = db.query(SystemSetting).filter(SystemSetting.key == EMAIL_SETTINGS_KEY).first()
    assert email_row is not None

    generic_get = client.get("/api/v1/system/settings", headers=system_admin_headers)
    assert generic_get.status_code == 200
    assert EMAIL_SETTINGS_KEY not in generic_get.json()["settings"]


def test_email_service_uses_runtime_database_settings(client, system_admin_headers, monkeypatch):
    save_response = client.put(
        "/api/v1/system/settings/email",
        headers=system_admin_headers,
        json=_payload(),
    )
    assert save_response.status_code == 200

    sent_messages = []

    class _FakeSMTP:
        instances = []

        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.logged_in = None
            _FakeSMTP.instances.append(self)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def login(self, username, password):
            self.logged_in = (username, password)

        async def send_message(self, message):
            sent_messages.append(message)

    monkeypatch.setattr("app.services.email_service.aiosmtplib.SMTP", _FakeSMTP)

    result = asyncio.get_event_loop().run_until_complete(
        EmailService().send_email(
            to_email="recipient@example.com",
            subject="Runtime email config",
            html_content="<p>hello</p>",
            text_content="hello",
        )
    )

    assert result is True
    smtp = _FakeSMTP.instances[0]
    assert smtp.kwargs["hostname"] == "smtp.mail.test"
    assert smtp.kwargs["port"] == 587
    assert smtp.kwargs["use_tls"] is False
    assert smtp.kwargs["start_tls"] is True
    assert smtp.logged_in == ("mailbox@example.com", "smtp-pass-123")
    assert sent_messages[0]["From"] == "Ops Mailbox <mailbox@example.com>"
