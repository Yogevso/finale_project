"""System Settings Management API - System Admin Only"""

import json

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.tenant import TenantContext, require_system_admin
from app.models import ActionType
from app.services.audit_helper import write_audit_log
from app.schemas.system_settings import SystemSettingsResponse, SystemSettingsUpdate
from app.services.system_settings_service import SystemSettingsService

router = APIRouter(prefix="/system/settings", tags=["system-settings"])


@router.get("", response_model=SystemSettingsResponse)
def get_system_settings(
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    settings = SystemSettingsService.get_settings(db)
    return SystemSettingsResponse(settings=settings)


@router.put("", response_model=SystemSettingsResponse, status_code=status.HTTP_200_OK)
def update_system_settings(
    payload: SystemSettingsUpdate,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    SystemSettingsService.upsert_settings(db, payload.settings, updated_by=tenant_ctx.user_id)

    write_audit_log(
        user_id=tenant_ctx.user_id,
        action=ActionType.SYSTEM,
        details=json.dumps(
            {"event": "system_settings_updated", "keys": sorted(payload.settings.keys())}
        ),
    )
    db.commit()

    settings = SystemSettingsService.get_settings(db)
    return SystemSettingsResponse(settings=settings)
