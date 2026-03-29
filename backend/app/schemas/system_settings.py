"""System settings schemas."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class SystemSettingsUpdate(BaseModel):
    """Update system settings"""

    settings: Dict[str, Any]


class SystemSettingsResponse(BaseModel):
    """System settings response"""

    settings: Dict[str, Any]


class EmailSecurityMode(str, Enum):
    SSL_TLS = "ssl_tls"
    STARTTLS = "starttls"
    NONE = "none"


class ArchiveRetentionUnit(str, Enum):
    DAYS = "days"
    MONTHS = "months"
    YEARS = "years"


class SystemEmailSettingsUpdate(BaseModel):
    """Update SYSADMIN-managed email delivery settings."""

    enabled: bool = False
    host: str | None = Field(None, max_length=255)
    port: int = Field(587, ge=1, le=65535)
    security: EmailSecurityMode = EmailSecurityMode.SSL_TLS
    username: str | None = Field(None, max_length=255)
    password: str | None = Field(None, min_length=1, max_length=255)
    clear_password: bool = False
    from_email: EmailStr
    from_name: str = Field(..., min_length=1, max_length=255)

    @field_validator("host", "username", "password", mode="before")
    @classmethod
    def _blank_strings_to_none(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value

    @field_validator("from_name", mode="before")
    @classmethod
    def _normalize_from_name(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def _validate_payload(self) -> "SystemEmailSettingsUpdate":
        if self.enabled and not self.host:
            raise ValueError("SMTP host is required when email delivery is enabled")
        if self.clear_password and self.password:
            raise ValueError("Provide a new password or clear the existing one, not both")
        return self


class SystemEmailSettingsView(BaseModel):
    """Visible SYSADMIN email delivery settings."""

    enabled: bool
    host: str | None = None
    port: int
    security: EmailSecurityMode
    username: str | None = None
    from_email: str
    from_name: str
    password_configured: bool
    password_masked: str | None = None


class SystemEmailSettingsResponse(BaseModel):
    """System email settings response."""

    settings: SystemEmailSettingsView
    source: Literal["database", "environment"]
    updated_at: datetime | None = None
    updated_by: int | None = None


class SystemDocumentLifecycleSettingsUpdate(BaseModel):
    """Update SYSADMIN-managed document lifecycle settings."""

    auto_archive_enabled: bool = False
    auto_archive_after_value: int = Field(12, ge=1, le=1200)
    auto_archive_after_unit: ArchiveRetentionUnit = ArchiveRetentionUnit.MONTHS


class SystemDocumentLifecycleSettingsView(BaseModel):
    """Visible SYSADMIN lifecycle settings for document retention."""

    auto_archive_enabled: bool
    auto_archive_after_value: int
    auto_archive_after_unit: ArchiveRetentionUnit
    auto_archive_basis: Literal["last_published"]
    delete_grace_days: int


class SystemDocumentLifecycleSettingsResponse(BaseModel):
    """Document lifecycle settings response."""

    settings: SystemDocumentLifecycleSettingsView
    source: Literal["database", "default"]
    updated_at: datetime | None = None
    updated_by: int | None = None
