"""System-managed email delivery settings with encrypted SMTP password storage."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy.orm import Session

from app.config import settings
from app.models import SystemSetting

EMAIL_SETTINGS_KEY = "__internal.email_delivery"
_ENCRYPTED_PREFIX = "enc:v1:"
_NONCE_BYTES = 16
_TAG_BYTES = 32
_CONTEXT = b"system-email-settings"
EmailSettingsSource = Literal["database", "environment"]
EmailSecurityMode = Literal["ssl_tls", "starttls", "none"]


@dataclass(frozen=True, slots=True)
class ResolvedEmailSettings:
    enabled: bool
    host: str | None
    port: int
    security: EmailSecurityMode
    username: str | None
    password: str | None
    from_email: str
    from_name: str
    source: EmailSettingsSource

    @classmethod
    def from_environment(cls) -> "ResolvedEmailSettings":
        return cls(
            enabled=bool(settings.EMAIL_ENABLED),
            host=settings.SMTP_HOST,
            port=int(settings.SMTP_PORT),
            security="ssl_tls",
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            from_email=settings.EMAIL_FROM,
            from_name=settings.EMAIL_FROM_NAME,
            source="environment",
        )


@dataclass(frozen=True, slots=True)
class EmailSettingsMetadata:
    source: EmailSettingsSource
    updated_at: datetime | None
    updated_by: int | None


class SystemEmailSettingsService:
    """Persist and resolve SYSADMIN-managed SMTP settings."""

    _runtime_override: ResolvedEmailSettings | None = None

    @classmethod
    def active_runtime_settings(cls) -> ResolvedEmailSettings:
        return cls._runtime_override or ResolvedEmailSettings.from_environment()

    @classmethod
    def reset_runtime_override(cls) -> None:
        cls._runtime_override = None

    @classmethod
    def load_runtime_override(cls, db: Session) -> ResolvedEmailSettings:
        stored_settings, _metadata = cls.get_effective_settings(db)
        cls._runtime_override = stored_settings if stored_settings.source == "database" else None
        return cls.active_runtime_settings()

    @classmethod
    def get_effective_settings(
        cls, db: Session
    ) -> tuple[ResolvedEmailSettings, EmailSettingsMetadata]:
        row = cls._settings_row(db)
        if row is None:
            return (
                ResolvedEmailSettings.from_environment(),
                EmailSettingsMetadata(source="environment", updated_at=None, updated_by=None),
            )

        payload = cls._decode_row_value(row.value)
        resolved = ResolvedEmailSettings(
            enabled=bool(payload.get("enabled", False)),
            host=cls._normalize_optional_str(payload.get("host")),
            port=int(payload.get("port") or 587),
            security=cls._normalize_security(payload.get("security")),
            username=cls._normalize_optional_str(payload.get("username")),
            password=cls._decrypt_optional_secret(payload.get("password")),
            from_email=str(payload.get("from_email") or settings.EMAIL_FROM),
            from_name=str(payload.get("from_name") or settings.EMAIL_FROM_NAME),
            source="database",
        )
        return (
            resolved,
            EmailSettingsMetadata(
                source="database",
                updated_at=row.updated_at,
                updated_by=row.updated_by,
            ),
        )

    @classmethod
    def update_settings(
        cls,
        db: Session,
        *,
        enabled: bool,
        host: str | None,
        port: int,
        security: EmailSecurityMode,
        username: str | None,
        password: str | None,
        clear_password: bool,
        from_email: str,
        from_name: str,
        updated_by: int | None,
    ) -> ResolvedEmailSettings:
        row = cls._settings_row(db)
        previous_settings = None
        if row is not None:
            previous_settings, _metadata = cls.get_effective_settings(db)

        effective_password = password
        if effective_password is None and previous_settings and not clear_password:
            effective_password = previous_settings.password
        if clear_password:
            effective_password = None

        stored_payload = {
            "enabled": enabled,
            "host": cls._normalize_optional_str(host),
            "port": int(port),
            "security": cls._normalize_security(security),
            "username": cls._normalize_optional_str(username),
            "password": cls._encrypt_optional_secret(effective_password),
            "from_email": from_email,
            "from_name": from_name,
        }

        encoded = json.dumps(stored_payload)
        if row is None:
            row = SystemSetting(key=EMAIL_SETTINGS_KEY, value=encoded, updated_by=updated_by)
            db.add(row)
        else:
            row.value = encoded
            row.updated_by = updated_by
        db.flush()

        cls._runtime_override = ResolvedEmailSettings(
            enabled=enabled,
            host=cls._normalize_optional_str(host),
            port=int(port),
            security=cls._normalize_security(security),
            username=cls._normalize_optional_str(username),
            password=effective_password,
            from_email=from_email,
            from_name=from_name,
            source="database",
        )
        return cls._runtime_override

    @staticmethod
    def build_masked_password(password: str | None) -> str | None:
        if not password:
            return None
        return "*" * 8

    @classmethod
    def _settings_row(cls, db: Session) -> SystemSetting | None:
        return db.query(SystemSetting).filter(SystemSetting.key == EMAIL_SETTINGS_KEY).first()

    @staticmethod
    def _decode_row_value(raw_value: str | None) -> dict[str, object]:
        if not raw_value:
            return {}
        try:
            decoded = json.loads(raw_value)
        except json.JSONDecodeError:
            return {}
        return decoded if isinstance(decoded, dict) else {}

    @staticmethod
    def _normalize_optional_str(value: object) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @staticmethod
    def _normalize_security(value: object) -> EmailSecurityMode:
        if value in {"ssl_tls", "starttls", "none"}:
            return value
        return "ssl_tls"

    @classmethod
    def _master_key_candidates(cls) -> list[bytes]:
        candidates = [settings.SECRET_KEY]
        if settings.SECRET_KEY_OLD:
            candidates.append(settings.SECRET_KEY_OLD)

        key_material: list[bytes] = []
        for secret in candidates:
            digest = hashlib.sha256(_CONTEXT + b":" + secret.encode("utf-8")).digest()
            key_material.append(digest)
        return key_material

    @staticmethod
    def _derive_subkey(master_key: bytes, label: bytes) -> bytes:
        return hmac.new(master_key, label, hashlib.sha256).digest()

    @classmethod
    def _keystream(cls, key: bytes, nonce: bytes, length: int) -> bytes:
        chunks = bytearray()
        counter = 0
        while len(chunks) < length:
            counter_bytes = counter.to_bytes(4, "big")
            chunks.extend(hmac.new(key, nonce + counter_bytes, hashlib.sha256).digest())
            counter += 1
        return bytes(chunks[:length])

    @classmethod
    def _encrypt_optional_secret(cls, value: str | None) -> str | None:
        if not value:
            return None
        master_key = cls._master_key_candidates()[0]
        nonce = os.urandom(_NONCE_BYTES)
        plaintext = value.encode("utf-8")
        encryption_key = cls._derive_subkey(master_key, b"enc")
        mac_key = cls._derive_subkey(master_key, b"mac")
        stream = cls._keystream(encryption_key, nonce, len(plaintext))
        ciphertext = bytes(left ^ right for left, right in zip(plaintext, stream, strict=False))
        tag = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()
        token = base64.urlsafe_b64encode(nonce + tag + ciphertext).decode("utf-8")
        return f"{_ENCRYPTED_PREFIX}{token}"

    @classmethod
    def _decrypt_optional_secret(cls, value: object) -> str | None:
        if value is None:
            return None
        raw_value = str(value)
        if not raw_value:
            return None
        if not raw_value.startswith(_ENCRYPTED_PREFIX):
            return raw_value

        encoded_token = raw_value[len(_ENCRYPTED_PREFIX) :].encode("utf-8")
        try:
            token = base64.urlsafe_b64decode(encoded_token)
        except Exception as exc:  # policy: BOUNDARY — malformed admin setting should fail closed
            raise ValueError("Unable to decode stored system email settings") from exc

        if len(token) < (_NONCE_BYTES + _TAG_BYTES):
            raise ValueError("Stored system email settings are malformed")

        nonce = token[:_NONCE_BYTES]
        tag = token[_NONCE_BYTES : _NONCE_BYTES + _TAG_BYTES]
        ciphertext = token[_NONCE_BYTES + _TAG_BYTES :]

        for master_key in cls._master_key_candidates():
            mac_key = cls._derive_subkey(master_key, b"mac")
            expected_tag = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()
            if not hmac.compare_digest(tag, expected_tag):
                continue
            encryption_key = cls._derive_subkey(master_key, b"enc")
            stream = cls._keystream(encryption_key, nonce, len(ciphertext))
            plaintext = bytes(left ^ right for left, right in zip(ciphertext, stream, strict=False))
            try:
                return plaintext.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError("Stored system email settings are malformed") from exc
        raise ValueError("Unable to decrypt stored system email settings")
