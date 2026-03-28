"""System-managed document lifecycle settings for retention policies."""

from __future__ import annotations

import json
from calendar import monthrange
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from sqlalchemy.orm import Session

from app.config import settings
from app.models import SystemSetting

DOCUMENT_LIFECYCLE_SETTINGS_KEY = "__internal.document_lifecycle"
LifecycleSettingsSource = Literal["database", "default"]
ArchiveRetentionUnit = Literal["days", "months", "years"]
AUTO_ARCHIVE_BASIS = "last_published"


@dataclass(frozen=True, slots=True)
class ResolvedDocumentLifecycleSettings:
    auto_archive_enabled: bool
    auto_archive_after_value: int
    auto_archive_after_unit: ArchiveRetentionUnit
    auto_archive_basis: Literal["last_published"]
    delete_grace_days: int
    source: LifecycleSettingsSource

    @classmethod
    def default(cls) -> "ResolvedDocumentLifecycleSettings":
        return cls(
            auto_archive_enabled=False,
            auto_archive_after_value=12,
            auto_archive_after_unit="months",
            auto_archive_basis=AUTO_ARCHIVE_BASIS,
            delete_grace_days=int(settings.DOCUMENT_DELETE_GRACE_DAYS),
            source="default",
        )

    def archive_cutoff(self, now: datetime) -> datetime | None:
        if not self.auto_archive_enabled:
            return None
        return subtract_retention_window(
            now,
            count=self.auto_archive_after_value,
            unit=self.auto_archive_after_unit,
        )


@dataclass(frozen=True, slots=True)
class DocumentLifecycleSettingsMetadata:
    source: LifecycleSettingsSource
    updated_at: datetime | None
    updated_by: int | None


def subtract_retention_window(
    dt: datetime,
    *,
    count: int,
    unit: ArchiveRetentionUnit,
) -> datetime:
    if unit == "days":
        return dt - timedelta(days=count)
    if unit == "months":
        return _shift_months(dt, -count)
    if unit == "years":
        return _shift_years(dt, -count)
    raise ValueError(f"Unsupported archive retention unit: {unit}")


def _shift_months(value: datetime, delta_months: int) -> datetime:
    total_months = value.year * 12 + (value.month - 1) + delta_months
    year, month_index = divmod(total_months, 12)
    month = month_index + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _shift_years(value: datetime, delta_years: int) -> datetime:
    year = value.year + delta_years
    day = min(value.day, monthrange(year, value.month)[1])
    return value.replace(year=year, day=day)


class SystemDocumentLifecycleSettingsService:
    """Persist and resolve SYSADMIN-managed document lifecycle settings."""

    @classmethod
    def get_effective_settings(
        cls,
        db: Session,
    ) -> tuple[ResolvedDocumentLifecycleSettings, DocumentLifecycleSettingsMetadata]:
        row = cls._settings_row(db)
        if row is None:
            defaults = ResolvedDocumentLifecycleSettings.default()
            return (
                defaults,
                DocumentLifecycleSettingsMetadata(
                    source=defaults.source,
                    updated_at=None,
                    updated_by=None,
                ),
            )

        payload = cls._decode_row_value(row.value)
        resolved = ResolvedDocumentLifecycleSettings(
            auto_archive_enabled=bool(payload.get("auto_archive_enabled", False)),
            auto_archive_after_value=cls._normalize_positive_int(
                payload.get("auto_archive_after_value"),
                default=12,
            ),
            auto_archive_after_unit=cls._normalize_unit(payload.get("auto_archive_after_unit")),
            auto_archive_basis=AUTO_ARCHIVE_BASIS,
            delete_grace_days=int(settings.DOCUMENT_DELETE_GRACE_DAYS),
            source="database",
        )
        return (
            resolved,
            DocumentLifecycleSettingsMetadata(
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
        auto_archive_enabled: bool,
        auto_archive_after_value: int,
        auto_archive_after_unit: ArchiveRetentionUnit,
        updated_by: int | None,
    ) -> ResolvedDocumentLifecycleSettings:
        row = cls._settings_row(db)
        payload = {
            "auto_archive_enabled": bool(auto_archive_enabled),
            "auto_archive_after_value": cls._normalize_positive_int(
                auto_archive_after_value,
                default=12,
            ),
            "auto_archive_after_unit": cls._normalize_unit(auto_archive_after_unit),
        }

        encoded = json.dumps(payload)
        if row is None:
            row = SystemSetting(
                key=DOCUMENT_LIFECYCLE_SETTINGS_KEY,
                value=encoded,
                updated_by=updated_by,
            )
            db.add(row)
        else:
            row.value = encoded
            row.updated_by = updated_by
        db.flush()

        return ResolvedDocumentLifecycleSettings(
            auto_archive_enabled=payload["auto_archive_enabled"],
            auto_archive_after_value=payload["auto_archive_after_value"],
            auto_archive_after_unit=payload["auto_archive_after_unit"],
            auto_archive_basis=AUTO_ARCHIVE_BASIS,
            delete_grace_days=int(settings.DOCUMENT_DELETE_GRACE_DAYS),
            source="database",
        )

    @classmethod
    def _settings_row(cls, db: Session) -> SystemSetting | None:
        return (
            db.query(SystemSetting)
            .filter(SystemSetting.key == DOCUMENT_LIFECYCLE_SETTINGS_KEY)
            .first()
        )

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
    def _normalize_positive_int(value: object, *, default: int) -> int:
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            return default
        return normalized if normalized > 0 else default

    @staticmethod
    def _normalize_unit(value: object) -> ArchiveRetentionUnit:
        if value in {"days", "months", "years"}:
            return value
        return "months"
