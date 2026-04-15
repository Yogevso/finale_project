"""System Settings Management API - System Admin Only"""

import json

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.tenant import TenantContext, require_system_admin
from app.models import ActionType
from app.schemas.system_settings import (
    SystemDocumentLifecycleSettingsResponse,
    SystemDocumentLifecycleSettingsUpdate,
    SystemDocumentLifecycleSettingsView,
    SystemEmailSettingsResponse,
    SystemEmailSettingsUpdate,
    SystemEmailSettingsView,
    SystemSettingsResponse,
    SystemSettingsUpdate,
)
from app.services.audit_helper import write_audit_log
from app.services.system_document_lifecycle_settings_service import (
    SystemDocumentLifecycleSettingsService,
)
from app.services.system_email_settings_service import SystemEmailSettingsService
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


@router.get("/email", response_model=SystemEmailSettingsResponse)
def get_system_email_settings(
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    _ = tenant_ctx
    resolved, metadata = SystemEmailSettingsService.get_effective_settings(db)
    return SystemEmailSettingsResponse(
        settings=SystemEmailSettingsView(
            enabled=resolved.enabled,
            host=resolved.host,
            port=resolved.port,
            security=resolved.security,
            username=resolved.username,
            from_email=resolved.from_email,
            from_name=resolved.from_name,
            password_configured=bool(resolved.password),
            password_masked=SystemEmailSettingsService.build_masked_password(resolved.password),
        ),
        source=metadata.source,
        updated_at=metadata.updated_at,
        updated_by=metadata.updated_by,
    )


@router.get("/document-lifecycle", response_model=SystemDocumentLifecycleSettingsResponse)
def get_system_document_lifecycle_settings(
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    _ = tenant_ctx
    resolved, metadata = SystemDocumentLifecycleSettingsService.get_effective_settings(db)
    return SystemDocumentLifecycleSettingsResponse(
        settings=SystemDocumentLifecycleSettingsView(
            auto_archive_enabled=resolved.auto_archive_enabled,
            auto_archive_after_value=resolved.auto_archive_after_value,
            auto_archive_after_unit=resolved.auto_archive_after_unit,
            auto_archive_basis=resolved.auto_archive_basis,
            delete_grace_days=resolved.delete_grace_days,
        ),
        source=metadata.source,
        updated_at=metadata.updated_at,
        updated_by=metadata.updated_by,
    )


@router.put(
    "/document-lifecycle",
    response_model=SystemDocumentLifecycleSettingsResponse,
    status_code=status.HTTP_200_OK,
)
def update_system_document_lifecycle_settings(
    payload: SystemDocumentLifecycleSettingsUpdate,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    changed = SystemDocumentLifecycleSettingsService.update_settings(
        db,
        auto_archive_enabled=payload.auto_archive_enabled,
        auto_archive_after_value=payload.auto_archive_after_value,
        auto_archive_after_unit=payload.auto_archive_after_unit.value,
        updated_by=tenant_ctx.user_id,
    )

    write_audit_log(
        user_id=tenant_ctx.user_id,
        action=ActionType.SYSTEM,
        details=json.dumps(
            {
                "event": "system_document_lifecycle_settings_updated",
                "auto_archive_enabled": changed.auto_archive_enabled,
                "auto_archive_after_value": changed.auto_archive_after_value,
                "auto_archive_after_unit": changed.auto_archive_after_unit,
                "auto_archive_basis": changed.auto_archive_basis,
                "delete_grace_days": changed.delete_grace_days,
            }
        ),
    )
    db.commit()

    return get_system_document_lifecycle_settings(tenant_ctx=tenant_ctx, db=db)


@router.put("/email", response_model=SystemEmailSettingsResponse, status_code=status.HTTP_200_OK)
def update_system_email_settings(
    payload: SystemEmailSettingsUpdate,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    changed = SystemEmailSettingsService.update_settings(
        db,
        enabled=payload.enabled,
        host=payload.host,
        port=payload.port,
        security=payload.security.value,
        username=payload.username,
        password=payload.password,
        clear_password=payload.clear_password,
        from_email=payload.from_email,
        from_name=payload.from_name,
        updated_by=tenant_ctx.user_id,
    )

    write_audit_log(
        user_id=tenant_ctx.user_id,
        action=ActionType.SYSTEM,
        details=json.dumps(
            {
                "event": "system_email_settings_updated",
                "enabled": changed.enabled,
                "host": changed.host,
                "port": changed.port,
                "security": changed.security,
                "username": changed.username,
                "from_email": changed.from_email,
                "from_name": changed.from_name,
                "password_changed": payload.password is not None,
                "password_cleared": payload.clear_password,
            }
        ),
    )
    db.commit()

    return get_system_email_settings(tenant_ctx=tenant_ctx, db=db)
