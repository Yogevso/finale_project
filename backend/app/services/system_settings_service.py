"""System settings service"""

from __future__ import annotations

import json
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.models import SystemSetting

_INTERNAL_KEY_PREFIX = "__internal."


class SystemSettingsService:
    """Service for reading/writing system settings"""

    @staticmethod
    def get_settings(db: Session, *, include_internal: bool = False) -> Dict[str, Any]:
        settings: Dict[str, Any] = {}
        rows = db.query(SystemSetting).order_by(SystemSetting.key).all()
        for row in rows:
            if not include_internal and row.key.startswith(_INTERNAL_KEY_PREFIX):
                continue
            if row.value is None:
                settings[row.key] = None
                continue
            try:
                settings[row.key] = json.loads(row.value)
            except json.JSONDecodeError:
                settings[row.key] = row.value
        return settings

    @staticmethod
    def upsert_settings(db: Session, settings: Dict[str, Any], updated_by: int | None) -> None:
        existing_rows = db.query(SystemSetting).all()
        managed_rows = [
            row for row in existing_rows if not row.key.startswith(_INTERNAL_KEY_PREFIX)
        ]
        existing_keys = {row.key for row in managed_rows}
        incoming_keys = set(settings.keys())

        # Remove keys that were deleted in the UI
        keys_to_delete = existing_keys - incoming_keys
        if keys_to_delete:
            db.query(SystemSetting).filter(SystemSetting.key.in_(keys_to_delete)).delete(
                synchronize_session=False
            )

        for key, value in settings.items():
            encoded = json.dumps(value)
            row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
            if row:
                row.value = encoded
                row.updated_by = updated_by
            else:
                row = SystemSetting(key=key, value=encoded, updated_by=updated_by)
                db.add(row)
        db.commit()
