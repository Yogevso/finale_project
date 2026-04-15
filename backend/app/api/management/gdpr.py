"""Wave AA — GDPR data export, deletion, and audit integrity endpoints.

AA-001: POST /gdpr/export — request data export
        GET  /gdpr/export/{request_id}/download — download export ZIP
AA-002: POST /gdpr/deletion — request data deletion
        PUT  /gdpr/deletion/{request_id}/review — admin approves/rejects
        POST /gdpr/deletion/{request_id}/execute — execute approved deletion
AA-004: GET  /audit/integrity — verify audit log HMAC integrity
        POST /audit/immutability — install immutability triggers
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.db import get_analytics_db, get_db
from app.dependencies.tenant import TenantContext, get_tenant_context, require_system_admin
from app.models import (
    ActionType,
    DataRequest,
    DataRequestStatus,
    DataRequestType,
)
from app.schemas.gdpr import (
    AuditIntegrityResult,
    DataDeletionApproval,
    DataDeletionRequest,
    DataDeletionResponse,
    DataExportRequest,
    DataExportResponse,
    DataRequestListItem,
)
from app.services.gdpr_service import (
    approve_data_deletion,
    check_audit_integrity,
    execute_data_deletion,
    execute_data_export,
    install_audit_immutability_trigger,
    request_data_deletion,
    request_data_export,
)

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════
# AA-001  Data Export Requests
# ═══════════════════════════════════════════════════════════════════


@router.post("/gdpr/export", response_model=DataExportResponse, status_code=201)
def create_export_request(
    body: DataExportRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """Request a full personal data export (GDPR Article 20)."""
    req = request_data_export(db, user_id=tenant_ctx.user_id, reason=body.reason)
    return DataExportResponse(
        id=req.id,
        user_id=req.user_id,
        status=req.status.value,
        reason=req.reason,
        requested_at=req.requested_at,
    )


@router.post("/gdpr/export/{request_id}/generate", response_model=DataExportResponse)
def generate_export(
    request_id: int,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
    analytics_db: Session = Depends(get_analytics_db),
):
    """Admin triggers export generation for a pending request."""
    req = db.query(DataRequest).filter(DataRequest.id == request_id).first()
    if not req or req.request_type != DataRequestType.EXPORT:
        raise HTTPException(status_code=404, detail="Export request not found")

    execute_data_export(db, request_id, analytics_db=analytics_db)
    db.refresh(req)
    return DataExportResponse(
        id=req.id,
        user_id=req.user_id,
        status=req.status.value,
        reason=req.reason,
        requested_at=req.requested_at,
        completed_at=req.completed_at,
        download_url=f"/api/v1/gdpr/export/{req.id}/download",
    )


@router.get("/gdpr/export/{request_id}/download")
def download_export(
    request_id: int,
    token: str,
    db: Session = Depends(get_db),
    analytics_db: Session = Depends(get_analytics_db),
):
    """Download a completed data export ZIP.  Requires the one-time download token."""
    from datetime import datetime

    req = db.query(DataRequest).filter(DataRequest.id == request_id).first()
    if not req or req.request_type != DataRequestType.EXPORT:
        raise HTTPException(status_code=404, detail="Export request not found")
    if req.status != DataRequestStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Export not ready")
    if not req.download_token or req.download_token != token:
        raise HTTPException(status_code=403, detail="Invalid download token")
    if req.download_expires_at and req.download_expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Download link expired")

    # Re-generate export (in production, this would be fetched from storage)
    zip_bytes = execute_data_export(db, request_id, analytics_db=analytics_db)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=data-export-{request_id}.zip"},
    )


# ═══════════════════════════════════════════════════════════════════
# AA-002  Data Deletion Requests
# ═══════════════════════════════════════════════════════════════════


@router.post("/gdpr/deletion", response_model=DataDeletionResponse, status_code=201)
def create_deletion_request(
    body: DataDeletionRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """Request account data deletion (GDPR Article 17 — right to erasure)."""
    if not body.confirm_deletion:
        raise HTTPException(status_code=400, detail="Must confirm deletion")
    req = request_data_deletion(db, user_id=tenant_ctx.user_id, reason=body.reason)
    return DataDeletionResponse(
        id=req.id,
        user_id=req.user_id,
        status=req.status.value,
        reason=req.reason,
        requested_at=req.requested_at,
    )


@router.put("/gdpr/deletion/{request_id}/review", response_model=DataDeletionResponse)
def review_deletion_request(
    request_id: int,
    body: DataDeletionApproval,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """Admin approves or rejects a data deletion request."""
    req = approve_data_deletion(
        db,
        request_id,
        admin_id=tenant_ctx.user_id,
        approved=body.approved,
        comment=body.comment,
    )
    return DataDeletionResponse(
        id=req.id,
        user_id=req.user_id,
        status=req.status.value,
        reason=req.reason,
        requested_at=req.requested_at,
        approved_at=req.approved_at,
    )


@router.post("/gdpr/deletion/{request_id}/execute", response_model=DataDeletionResponse)
def run_deletion(
    request_id: int,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
    analytics_db: Session = Depends(get_analytics_db),
):
    """Execute an approved data deletion — anonymizes user data."""
    execute_data_deletion(db, request_id, analytics_db=analytics_db)
    req = db.query(DataRequest).filter(DataRequest.id == request_id).first()
    return DataDeletionResponse(
        id=req.id,
        user_id=req.user_id,
        status=req.status.value,
        reason=req.reason,
        requested_at=req.requested_at,
        approved_at=req.approved_at,
        executed_at=req.executed_at,
    )


# ═══════════════════════════════════════════════════════════════════
# Admin — list all data requests
# ═══════════════════════════════════════════════════════════════════


@router.get("/gdpr/requests", response_model=list[DataRequestListItem])
def list_data_requests(
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """List all GDPR data requests (admin view)."""
    requests = (
        db.query(DataRequest)
        .options(joinedload(DataRequest.user))
        .order_by(DataRequest.requested_at.desc())
        .limit(100)
        .all()
    )
    result = []
    for r in requests:
        user = r.user
        result.append(
            DataRequestListItem(
                id=r.id,
                user_id=r.user_id,
                user_email=user.email if user else "unknown",
                request_type=r.request_type.value,
                status=r.status.value,
                reason=r.reason,
                requested_at=r.requested_at,
                completed_at=r.completed_at,
            )
        )
    return result


# ═══════════════════════════════════════════════════════════════════
# AA-004  Audit Integrity & Immutability
# ═══════════════════════════════════════════════════════════════════


@router.get("/audit/integrity", response_model=AuditIntegrityResult)
def verify_audit_integrity(
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
    analytics_db: Session = Depends(get_analytics_db),
):
    """Verify HMAC signatures on all signed audit log entries."""
    result = check_audit_integrity(db, analytics_db=analytics_db)
    return AuditIntegrityResult(**result)


@router.post("/audit/immutability", status_code=200)
def enable_audit_immutability(
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
    analytics_db: Session = Depends(get_analytics_db),
):
    """Install DB triggers preventing UPDATE/DELETE on audit_logs."""
    install_audit_immutability_trigger(db, analytics_db=analytics_db)
    from app.services.audit_helper import write_audit_log

    write_audit_log(
        user_id=tenant_ctx.user_id,
        action=ActionType.SYSTEM,
        details=json.dumps({"event": "audit_immutability_enabled"}),
    )
    return {"status": "immutability_triggers_installed"}
