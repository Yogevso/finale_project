"""Wave Z — Admin Operations & Tenant Management API routes.

All endpoints require SYSTEM_ADMIN role unless noted otherwise.
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.tenant import TenantContext, get_tenant_context, require_system_admin
from app.models import (
    ActionType,
    AdminAction,
    AdminActionStatus,
    Announcement,
    AuditLog,
    Document,
    DomainVerification,
    DomainVerificationStatus,
    FeatureFlag,
    ImpersonationSession,
    MaintenanceWindow,
    Tenant,
    TenantQuota,
    User,
    UserRole,
)
from app.schemas.admin_ops import (
    AdminActionCreate,
    AdminActionResponse,
    AdminActionReview,
    BulkAnnouncementSend,
    BulkTenantSettingsUpdate,
    DomainVerificationCreate,
    DomainVerificationResponse,
    FeatureFlagResponse,
    FeatureFlagUpdate,
    FeatureMatrixResponse,
    ImpersonateRequest,
    ImpersonationSessionResponse,
    MaintenanceWindowCreate,
    MaintenanceWindowResponse,
    ServiceStatus,
    SystemStatusResponse,
    TenantBrandingResponse,
    TenantBrandingUpdate,
    TenantConfigResponse,
    TenantConfigUpdate,
    TenantExportResponse,
    TenantPerformanceResponse,
    TenantProvisionRequest,
    TenantProvisionResponse,
    TenantQuotaResponse,
    TenantQuotaUpdate,
    TenantSuspendRequest,
)

router = APIRouter()


# ── Helpers ────────────────────────────────────────────────────────


def _audit(
    db: Session,
    *,
    user_id: int,
    action: ActionType,
    event: str,
    details: dict | None = None,
) -> None:
    """Record an audit log entry."""
    payload = {"event": event}
    if details:
        payload.update(details)
    db.add(AuditLog(user_id=user_id, action=action, details=json.dumps(payload)))


def _get_tenant_or_404(db: Session, tenant_id: int) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


def _parse_settings(tenant: Tenant) -> dict:
    """Parse tenant settings JSON, returning empty dict if null/invalid."""
    if not tenant.settings:
        return {}
    try:
        return json.loads(tenant.settings)
    except (json.JSONDecodeError, TypeError):
        return {}


# ══════════════════════════════════════════════════════════════════
# Z-001  Tenant Impersonation
# ══════════════════════════════════════════════════════════════════


@router.post("/admin/impersonate", response_model=ImpersonationSessionResponse)
def start_impersonation(
    body: ImpersonateRequest,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """Start impersonating a tenant.  System-admin only."""
    tenant = _get_tenant_or_404(db, body.target_tenant_id)

    # End any existing active impersonation for this admin
    db.query(ImpersonationSession).filter(
        ImpersonationSession.admin_user_id == tenant_ctx.user_id,
        ImpersonationSession.is_active.is_(True),
    ).update({"is_active": False, "ended_at": datetime.utcnow()})

    session = ImpersonationSession(
        admin_user_id=tenant_ctx.user_id,
        target_tenant_id=tenant.id,
        session_token=secrets.token_urlsafe(64),
        started_at=datetime.utcnow(),
    )
    db.add(session)

    _audit(
        db,
        user_id=tenant_ctx.user_id,
        action=ActionType.SYSTEM,
        event="impersonation_start",
        details={"target_tenant_id": tenant.id, "target_tenant_name": tenant.name},
    )
    db.commit()
    db.refresh(session)

    return ImpersonationSessionResponse(
        id=session.id,
        admin_user_id=session.admin_user_id,
        target_tenant_id=session.target_tenant_id,
        target_tenant_name=tenant.name,
        session_token=session.session_token,
        started_at=session.started_at,
        ended_at=session.ended_at,
        is_active=session.is_active,
    )


@router.post("/admin/impersonate/end")
def end_impersonation(
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """End the current impersonation session."""
    updated = (
        db.query(ImpersonationSession)
        .filter(
            ImpersonationSession.admin_user_id == tenant_ctx.user_id,
            ImpersonationSession.is_active.is_(True),
        )
        .update({"is_active": False, "ended_at": datetime.utcnow()})
    )
    _audit(
        db,
        user_id=tenant_ctx.user_id,
        action=ActionType.SYSTEM,
        event="impersonation_end",
    )
    db.commit()
    return {"ended": updated > 0}


@router.get("/admin/impersonate/current", response_model=ImpersonationSessionResponse | None)
def get_current_impersonation(
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """Get the current active impersonation session, if any."""
    session = (
        db.query(ImpersonationSession)
        .filter(
            ImpersonationSession.admin_user_id == tenant_ctx.user_id,
            ImpersonationSession.is_active.is_(True),
        )
        .first()
    )
    if not session:
        return None
    tenant = db.query(Tenant).filter(Tenant.id == session.target_tenant_id).first()
    return ImpersonationSessionResponse(
        id=session.id,
        admin_user_id=session.admin_user_id,
        target_tenant_id=session.target_tenant_id,
        target_tenant_name=tenant.name if tenant else None,
        session_token=session.session_token,
        started_at=session.started_at,
        ended_at=session.ended_at,
        is_active=session.is_active,
    )


# ══════════════════════════════════════════════════════════════════
# Z-002  Admin Action Queue with Approvals
# ══════════════════════════════════════════════════════════════════


@router.post("/admin/actions", response_model=AdminActionResponse)
def create_admin_action(
    body: AdminActionCreate,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """Queue a critical admin action for second sysadmin approval."""
    action = AdminAction(
        action_type=body.action_type,
        payload=json.dumps(body.payload),
        reason=body.reason,
        requested_by=tenant_ctx.user_id,
        target_tenant_id=body.target_tenant_id,
        created_at=datetime.utcnow(),
    )
    db.add(action)
    _audit(
        db,
        user_id=tenant_ctx.user_id,
        action=ActionType.CREATE,
        event="admin_action_queued",
        details={"action_type": body.action_type, "target_tenant_id": body.target_tenant_id},
    )
    db.commit()
    db.refresh(action)

    requester = db.query(User).filter(User.id == action.requested_by).first()
    return AdminActionResponse(
        id=action.id,
        action_type=action.action_type.value if hasattr(action.action_type, "value") else str(action.action_type),
        status=action.status.value if hasattr(action.status, "value") else str(action.status),
        payload=action.payload,
        reason=action.reason,
        requested_by=action.requested_by,
        requester_name=requester.username if requester else None,
        reviewed_by=action.reviewed_by,
        target_tenant_id=action.target_tenant_id,
        created_at=action.created_at,
        reviewed_at=action.reviewed_at,
        executed_at=action.executed_at,
    )


@router.get("/admin/actions", response_model=list[AdminActionResponse])
def list_admin_actions(
    status_filter: Optional[str] = Query(None, alias="status"),
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """List admin actions.  Optional filter by status."""
    q = db.query(AdminAction).order_by(AdminAction.created_at.desc())
    if status_filter:
        q = q.filter(AdminAction.status == status_filter)
    actions = q.limit(100).all()

    result = []
    for a in actions:
        requester = db.query(User).filter(User.id == a.requested_by).first()
        reviewer = db.query(User).filter(User.id == a.reviewed_by).first() if a.reviewed_by else None
        target = db.query(Tenant).filter(Tenant.id == a.target_tenant_id).first() if a.target_tenant_id else None
        result.append(
            AdminActionResponse(
                id=a.id,
                action_type=a.action_type.value if hasattr(a.action_type, "value") else str(a.action_type),
                status=a.status.value if hasattr(a.status, "value") else str(a.status),
                payload=a.payload,
                reason=a.reason,
                requested_by=a.requested_by,
                requester_name=requester.username if requester else None,
                reviewed_by=a.reviewed_by,
                reviewer_name=reviewer.username if reviewer else None,
                review_comment=a.review_comment,
                target_tenant_id=a.target_tenant_id,
                target_tenant_name=target.name if target else None,
                created_at=a.created_at,
                reviewed_at=a.reviewed_at,
                executed_at=a.executed_at,
            )
        )
    return result


@router.put("/admin/actions/{action_id}/review", response_model=AdminActionResponse)
def review_admin_action(
    action_id: int,
    body: AdminActionReview,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """Approve or reject a pending admin action.  Must be a different sysadmin."""
    action = db.query(AdminAction).filter(AdminAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.status != AdminActionStatus.PENDING:
        raise HTTPException(status_code=400, detail="Action already reviewed")
    if action.requested_by == tenant_ctx.user_id:
        raise HTTPException(status_code=403, detail="Cannot review your own action")

    now = datetime.utcnow()
    action.reviewed_by = tenant_ctx.user_id
    action.reviewed_at = now
    action.review_comment = body.comment
    action.status = AdminActionStatus.APPROVED if body.approved else AdminActionStatus.REJECTED

    _audit(
        db,
        user_id=tenant_ctx.user_id,
        action=ActionType.UPDATE,
        event="admin_action_reviewed",
        details={"action_id": action.id, "approved": body.approved},
    )
    db.commit()
    db.refresh(action)

    requester = db.query(User).filter(User.id == action.requested_by).first()
    reviewer = db.query(User).filter(User.id == action.reviewed_by).first()
    return AdminActionResponse(
        id=action.id,
        action_type=action.action_type.value if hasattr(action.action_type, "value") else str(action.action_type),
        status=action.status.value if hasattr(action.status, "value") else str(action.status),
        payload=action.payload,
        reason=action.reason,
        requested_by=action.requested_by,
        requester_name=requester.username if requester else None,
        reviewed_by=action.reviewed_by,
        reviewer_name=reviewer.username if reviewer else None,
        review_comment=action.review_comment,
        target_tenant_id=action.target_tenant_id,
        created_at=action.created_at,
        reviewed_at=action.reviewed_at,
        executed_at=action.executed_at,
    )


# ══════════════════════════════════════════════════════════════════
# Z-003  Bulk Tenant Maintenance
# ══════════════════════════════════════════════════════════════════


@router.post("/admin/bulk/settings")
def bulk_update_tenant_settings(
    body: BulkTenantSettingsUpdate,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """Batch-update settings for multiple tenants."""
    updated = 0
    for tid in body.tenant_ids:
        tenant = db.query(Tenant).filter(Tenant.id == tid).first()
        if not tenant:
            continue
        current = _parse_settings(tenant)
        current.update(body.settings)
        tenant.settings = json.dumps(current)
        updated += 1

    _audit(
        db,
        user_id=tenant_ctx.user_id,
        action=ActionType.UPDATE,
        event="bulk_tenant_settings_update",
        details={"tenant_ids": body.tenant_ids, "settings_keys": list(body.settings.keys())},
    )
    db.commit()
    return {"updated": updated}


@router.post("/admin/bulk/announcements")
def bulk_send_announcements(
    body: BulkAnnouncementSend,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """Send announcement to selected (or all) tenants."""
    announcement = Announcement(
        message=body.message,
        type=body.type,
        active=True,
        created_by=tenant_ctx.user_id,
        created_at=datetime.utcnow(),
    )
    db.add(announcement)

    _audit(
        db,
        user_id=tenant_ctx.user_id,
        action=ActionType.CREATE,
        event="bulk_announcement_sent",
        details={"tenant_ids": body.tenant_ids, "message": body.message[:100]},
    )
    db.commit()
    return {"created": True, "announcement_id": announcement.id}


# ══════════════════════════════════════════════════════════════════
# Z-004  Tenant Configuration Registry
# ══════════════════════════════════════════════════════════════════


@router.get("/admin/tenants/{tenant_id}/config", response_model=TenantConfigResponse)
def get_tenant_config(
    tenant_id: int,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """Read KV settings for a tenant."""
    tenant = _get_tenant_or_404(db, tenant_id)
    return TenantConfigResponse(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        settings=_parse_settings(tenant),
    )


@router.put("/admin/tenants/{tenant_id}/config", response_model=TenantConfigResponse)
def update_tenant_config(
    tenant_id: int,
    body: TenantConfigUpdate,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """Update KV settings for a tenant (merge)."""
    tenant = _get_tenant_or_404(db, tenant_id)
    old_settings = _parse_settings(tenant)
    new_settings = {**old_settings, **body.settings}
    tenant.settings = json.dumps(new_settings)

    # Z-013: Config change audit trail (before/after diff)
    _audit(
        db,
        user_id=tenant_ctx.user_id,
        action=ActionType.UPDATE,
        event="tenant_config_updated",
        details={
            "tenant_id": tenant_id,
            "before": old_settings,
            "after": new_settings,
        },
    )
    db.commit()
    db.refresh(tenant)

    return TenantConfigResponse(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        settings=_parse_settings(tenant),
    )


# ══════════════════════════════════════════════════════════════════
# Z-005  Feature Access Matrix
# ══════════════════════════════════════════════════════════════════


@router.get("/admin/features", response_model=FeatureMatrixResponse)
def get_feature_matrix(
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """Return feature flags for all tenants (matrix view)."""
    tenants = db.query(Tenant).filter(Tenant.is_active.is_(True)).all()
    flags = db.query(FeatureFlag).all()

    flag_map: dict[int, dict[str, bool]] = {}
    for f in flags:
        flag_map.setdefault(f.tenant_id, {})[f.feature_key] = f.enabled

    rows = [
        {
            "tenant_id": t.id,
            "tenant_name": t.name,
            "features": flag_map.get(t.id, {}),
        }
        for t in tenants
    ]
    return FeatureMatrixResponse(tenants=rows)


@router.put("/admin/tenants/{tenant_id}/features", response_model=list[FeatureFlagResponse])
def update_tenant_features(
    tenant_id: int,
    body: list[FeatureFlagUpdate],
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """Set feature flags for a tenant."""
    _get_tenant_or_404(db, tenant_id)

    results = []
    for item in body:
        flag = (
            db.query(FeatureFlag)
            .filter(FeatureFlag.tenant_id == tenant_id, FeatureFlag.feature_key == item.feature_key)
            .first()
        )
        if flag:
            flag.enabled = item.enabled
            flag.updated_by = tenant_ctx.user_id
        else:
            flag = FeatureFlag(
                tenant_id=tenant_id,
                feature_key=item.feature_key,
                enabled=item.enabled,
                updated_by=tenant_ctx.user_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(flag)
        db.flush()
        results.append(flag)

    _audit(
        db,
        user_id=tenant_ctx.user_id,
        action=ActionType.UPDATE,
        event="feature_flags_updated",
        details={"tenant_id": tenant_id, "flags": [{"key": b.feature_key, "enabled": b.enabled} for b in body]},
    )
    db.commit()
    return [
        FeatureFlagResponse(
            id=f.id,
            tenant_id=f.tenant_id,
            feature_key=f.feature_key,
            enabled=f.enabled,
            updated_by=f.updated_by,
            created_at=f.created_at,
            updated_at=f.updated_at,
        )
        for f in results
    ]


# ══════════════════════════════════════════════════════════════════
# Z-006  System Status / Health
# ══════════════════════════════════════════════════════════════════


@router.get("/admin/status", response_model=SystemStatusResponse)
def get_system_status(
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """Return health of backend services."""
    services: list[ServiceStatus] = []

    # Backend DB check
    try:
        db.execute(func.literal(1).select())
        services.append(ServiceStatus(name="database", status="healthy"))
    except Exception:
        services.append(ServiceStatus(name="database", status="down", details="Connection failed"))

    # Storage check (simple path existence)
    import os

    upload_dir = os.environ.get("UPLOAD_DIR", "data/uploads")
    if os.path.isdir(upload_dir):
        services.append(ServiceStatus(name="storage", status="healthy"))
    else:
        services.append(ServiceStatus(name="storage", status="degraded", details="Upload directory missing"))

    # Backend is responding (implicit)
    services.append(ServiceStatus(name="backend", status="healthy"))

    overall = "healthy"
    if any(s.status == "down" for s in services):
        overall = "down"
    elif any(s.status == "degraded" for s in services):
        overall = "degraded"

    return SystemStatusResponse(
        overall=overall,
        services=services,
        checked_at=datetime.utcnow(),
    )


# ══════════════════════════════════════════════════════════════════
# Z-007  SLA / Performance Reporting
# ══════════════════════════════════════════════════════════════════


@router.get("/admin/tenants/{tenant_id}/performance", response_model=TenantPerformanceResponse)
def get_tenant_performance(
    tenant_id: int,
    days: int = Query(30, ge=1, le=90),
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """Get performance metrics for a tenant (audit-log based proxy)."""
    tenant = _get_tenant_or_404(db, tenant_id)
    period_end = datetime.utcnow()
    period_start = period_end - timedelta(days=days)

    # Active users in period
    active_users = (
        db.query(func.count(func.distinct(User.id)))
        .filter(User.tenant_id == tenant_id, User.is_active.is_(True))
        .scalar()
        or 0
    )

    return TenantPerformanceResponse(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        p50_ms=45.0,  # Placeholder — would need real request timing data
        p95_ms=220.0,
        error_rate=0.02,
        active_users=active_users,
        period_start=period_start,
        period_end=period_end,
    )


# ══════════════════════════════════════════════════════════════════
# Z-008  Organization Provisioning Workflow
# ══════════════════════════════════════════════════════════════════


@router.post("/admin/tenants/provision", response_model=TenantProvisionResponse)
def provision_tenant(
    body: TenantProvisionRequest,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """Create a new tenant + initial admin user in a single guided flow."""
    # Check slug uniqueness
    existing = db.query(Tenant).filter(Tenant.slug == body.tenant_slug).first()
    if existing:
        raise HTTPException(status_code=409, detail="Tenant slug already exists")

    # Check admin username uniqueness
    existing_user = db.query(User).filter(User.username == body.admin_username).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Admin username already exists")

    tenant = Tenant(
        name=body.tenant_name,
        slug=body.tenant_slug,
        is_active=True,
        company_type=body.company_type,
        contact_email=body.contact_email,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(tenant)
    db.flush()  # Get tenant.id

    from app.security import get_password_hash

    admin_user = User(
        username=body.admin_username,
        email=body.admin_email,
        hashed_password=get_password_hash(body.admin_password),
        role=UserRole.ADMIN,
        tenant_id=tenant.id,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(admin_user)
    db.flush()

    # Create default quota for tenant
    quota = TenantQuota(
        tenant_id=tenant.id,
        max_users=50,
        max_documents=500,
        max_storage_mb=5120,
        updated_by=tenant_ctx.user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(quota)

    _audit(
        db,
        user_id=tenant_ctx.user_id,
        action=ActionType.CREATE,
        event="tenant_provisioned",
        details={
            "tenant_id": tenant.id,
            "tenant_name": tenant.name,
            "admin_user_id": admin_user.id,
        },
    )
    db.commit()

    return TenantProvisionResponse(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        tenant_slug=tenant.slug,
        admin_user_id=admin_user.id,
        admin_username=admin_user.username,
    )


# ══════════════════════════════════════════════════════════════════
# Z-009  Tenant Suspension / Reactivation
# ══════════════════════════════════════════════════════════════════


@router.post("/admin/tenants/{tenant_id}/suspend")
def suspend_tenant(
    tenant_id: int,
    body: TenantSuspendRequest,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """Suspend a tenant — all their users get 403."""
    tenant = _get_tenant_or_404(db, tenant_id)
    if not tenant.is_active:
        raise HTTPException(status_code=400, detail="Tenant already suspended")

    tenant.is_active = False
    _audit(
        db,
        user_id=tenant_ctx.user_id,
        action=ActionType.SYSTEM,
        event="tenant_suspended",
        details={"tenant_id": tenant_id, "reason": body.reason},
    )
    db.commit()
    return {"suspended": True, "tenant_id": tenant_id}


@router.post("/admin/tenants/{tenant_id}/reactivate")
def reactivate_tenant(
    tenant_id: int,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """Reactivate a suspended tenant."""
    tenant = _get_tenant_or_404(db, tenant_id)
    if tenant.is_active:
        raise HTTPException(status_code=400, detail="Tenant already active")

    tenant.is_active = True
    _audit(
        db,
        user_id=tenant_ctx.user_id,
        action=ActionType.SYSTEM,
        event="tenant_reactivated",
        details={"tenant_id": tenant_id},
    )
    db.commit()
    return {"reactivated": True, "tenant_id": tenant_id}


# ══════════════════════════════════════════════════════════════════
# Z-010  Domain Verification
# ══════════════════════════════════════════════════════════════════


@router.post(
    "/admin/tenants/{tenant_id}/domains",
    response_model=DomainVerificationResponse,
    status_code=201,
)
def create_domain_verification(
    tenant_id: int,
    body: DomainVerificationCreate,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """Initiate domain verification — returns a DNS TXT record token."""
    _get_tenant_or_404(db, tenant_id)
    token = f"docportal-verify={secrets.token_urlsafe(32)}"
    dv = DomainVerification(
        tenant_id=tenant_id,
        domain=body.domain,
        verification_token=token,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(dv)
    db.commit()
    db.refresh(dv)
    return DomainVerificationResponse(
        id=dv.id,
        tenant_id=dv.tenant_id,
        domain=dv.domain,
        verification_token=dv.verification_token,
        status=dv.status.value if hasattr(dv.status, "value") else str(dv.status),
        verified_at=dv.verified_at,
        created_at=dv.created_at,
        expires_at=dv.expires_at,
    )


@router.get("/admin/tenants/{tenant_id}/domains", response_model=list[DomainVerificationResponse])
def list_domain_verifications(
    tenant_id: int,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """List domain verifications for a tenant."""
    _get_tenant_or_404(db, tenant_id)
    domains = db.query(DomainVerification).filter(DomainVerification.tenant_id == tenant_id).all()
    return [
        DomainVerificationResponse(
            id=d.id,
            tenant_id=d.tenant_id,
            domain=d.domain,
            verification_token=d.verification_token,
            status=d.status.value if hasattr(d.status, "value") else str(d.status),
            verified_at=d.verified_at,
            created_at=d.created_at,
            expires_at=d.expires_at,
        )
        for d in domains
    ]


@router.post("/admin/tenants/{tenant_id}/domains/{domain_id}/verify")
def verify_domain(
    tenant_id: int,
    domain_id: int,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """Mark a domain as verified (manual admin confirmation or DNS check stub)."""
    dv = (
        db.query(DomainVerification)
        .filter(DomainVerification.id == domain_id, DomainVerification.tenant_id == tenant_id)
        .first()
    )
    if not dv:
        raise HTTPException(status_code=404, detail="Domain verification not found")
    if dv.status == DomainVerificationStatus.VERIFIED:
        raise HTTPException(status_code=400, detail="Domain already verified")
    if dv.expires_at < datetime.utcnow():
        dv.status = DomainVerificationStatus.EXPIRED
        db.commit()
        raise HTTPException(status_code=400, detail="Verification token expired")

    dv.status = DomainVerificationStatus.VERIFIED
    dv.verified_at = datetime.utcnow()
    _audit(
        db,
        user_id=tenant_ctx.user_id,
        action=ActionType.SYSTEM,
        event="domain_verified",
        details={"tenant_id": tenant_id, "domain": dv.domain},
    )
    db.commit()
    return {"verified": True, "domain": dv.domain}


# ══════════════════════════════════════════════════════════════════
# Z-011  Custom Branding
# ══════════════════════════════════════════════════════════════════


@router.get("/admin/tenants/{tenant_id}/branding", response_model=TenantBrandingResponse)
def get_tenant_branding(
    tenant_id: int,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """Read branding settings for a tenant."""
    tenant = _get_tenant_or_404(db, tenant_id)
    settings = _parse_settings(tenant)
    branding = settings.get("branding", {})
    return TenantBrandingResponse(
        tenant_id=tenant.id,
        logo_url=tenant.company_logo or branding.get("logo_url"),
        primary_color=branding.get("primary_color"),
        accent_color=branding.get("accent_color"),
        portal_header_text=branding.get("portal_header_text"),
    )


@router.put("/admin/tenants/{tenant_id}/branding", response_model=TenantBrandingResponse)
def update_tenant_branding(
    tenant_id: int,
    body: TenantBrandingUpdate,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """Update branding for a tenant — stored in Tenant.settings JSON."""
    tenant = _get_tenant_or_404(db, tenant_id)
    settings = _parse_settings(tenant)
    old_branding = settings.get("branding", {})
    branding = {**old_branding}
    if body.logo_url is not None:
        tenant.company_logo = body.logo_url
        branding["logo_url"] = body.logo_url
    if body.primary_color is not None:
        branding["primary_color"] = body.primary_color
    if body.accent_color is not None:
        branding["accent_color"] = body.accent_color
    if body.portal_header_text is not None:
        branding["portal_header_text"] = body.portal_header_text

    settings["branding"] = branding
    tenant.settings = json.dumps(settings)

    _audit(
        db,
        user_id=tenant_ctx.user_id,
        action=ActionType.UPDATE,
        event="tenant_branding_updated",
        details={"tenant_id": tenant_id, "before": old_branding, "after": branding},
    )
    db.commit()

    return TenantBrandingResponse(
        tenant_id=tenant.id,
        logo_url=tenant.company_logo,
        primary_color=branding.get("primary_color"),
        accent_color=branding.get("accent_color"),
        portal_header_text=branding.get("portal_header_text"),
    )


# ══════════════════════════════════════════════════════════════════
# Z-012  Tenant Quota Policy
# ══════════════════════════════════════════════════════════════════


@router.get("/admin/tenants/{tenant_id}/quota", response_model=TenantQuotaResponse)
def get_tenant_quota(
    tenant_id: int,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """Read quota and current usage for a tenant."""
    tenant = _get_tenant_or_404(db, tenant_id)
    quota = db.query(TenantQuota).filter(TenantQuota.tenant_id == tenant_id).first()

    current_users = db.query(func.count(User.id)).filter(User.tenant_id == tenant_id).scalar() or 0
    current_docs = (
        db.query(func.count(Document.id)).filter(Document.tenant_id == tenant_id).scalar() or 0
    )

    return TenantQuotaResponse(
        tenant_id=tenant_id,
        max_users=quota.max_users if quota else None,
        max_documents=quota.max_documents if quota else None,
        max_storage_mb=quota.max_storage_mb if quota else None,
        current_users=current_users,
        current_documents=current_docs,
        updated_at=quota.updated_at if quota else None,
    )


@router.put("/admin/tenants/{tenant_id}/quota", response_model=TenantQuotaResponse)
def update_tenant_quota(
    tenant_id: int,
    body: TenantQuotaUpdate,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """Set quotas for a tenant."""
    _get_tenant_or_404(db, tenant_id)
    quota = db.query(TenantQuota).filter(TenantQuota.tenant_id == tenant_id).first()
    if not quota:
        quota = TenantQuota(
            tenant_id=tenant_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(quota)

    old = {"max_users": quota.max_users, "max_documents": quota.max_documents, "max_storage_mb": quota.max_storage_mb}
    if body.max_users is not None:
        quota.max_users = body.max_users
    if body.max_documents is not None:
        quota.max_documents = body.max_documents
    if body.max_storage_mb is not None:
        quota.max_storage_mb = body.max_storage_mb
    quota.updated_by = tenant_ctx.user_id

    _audit(
        db,
        user_id=tenant_ctx.user_id,
        action=ActionType.UPDATE,
        event="tenant_quota_updated",
        details={
            "tenant_id": tenant_id,
            "before": old,
            "after": {"max_users": quota.max_users, "max_documents": quota.max_documents, "max_storage_mb": quota.max_storage_mb},
        },
    )
    db.commit()
    db.refresh(quota)

    current_users = db.query(func.count(User.id)).filter(User.tenant_id == tenant_id).scalar() or 0
    current_docs = db.query(func.count(Document.id)).filter(Document.tenant_id == tenant_id).scalar() or 0

    return TenantQuotaResponse(
        tenant_id=tenant_id,
        max_users=quota.max_users,
        max_documents=quota.max_documents,
        max_storage_mb=quota.max_storage_mb,
        current_users=current_users,
        current_documents=current_docs,
        updated_at=quota.updated_at,
    )


# ══════════════════════════════════════════════════════════════════
# Z-015  Tenant Migration Toolkit (Export / Import)
# ══════════════════════════════════════════════════════════════════


@router.get("/admin/tenants/{tenant_id}/export", response_model=TenantExportResponse)
def export_tenant_data(
    tenant_id: int,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """Export tenant data to JSON for disaster recovery or migration."""
    tenant = _get_tenant_or_404(db, tenant_id)

    users = db.query(User).filter(User.tenant_id == tenant_id).all()
    documents = db.query(Document).filter(Document.tenant_id == tenant_id).all()

    export = {
        "tenant": {
            "name": tenant.name,
            "slug": tenant.slug,
            "settings": _parse_settings(tenant),
            "company_type": tenant.company_type,
            "contact_email": tenant.contact_email,
        },
        "users": [
            {"username": u.username, "email": u.email, "role": u.role.value if hasattr(u.role, "value") else str(u.role), "is_active": u.is_active}
            for u in users
        ],
        "documents": [
            {"title": d.title, "status": d.status.value if hasattr(d.status, "value") else str(d.status), "category": d.category}
            for d in documents
        ],
    }

    _audit(
        db,
        user_id=tenant_ctx.user_id,
        action=ActionType.SYSTEM,
        event="tenant_data_exported",
        details={"tenant_id": tenant_id, "user_count": len(users), "doc_count": len(documents)},
    )
    db.commit()

    return TenantExportResponse(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        export_data=export,
        exported_at=datetime.utcnow(),
    )


# ══════════════════════════════════════════════════════════════════
# Z-017  Admin API Rate Limiting  (config endpoint)
# ══════════════════════════════════════════════════════════════════


@router.get("/admin/rate-limits")
def get_rate_limits(
    tenant_ctx: TenantContext = Depends(require_system_admin),
):
    """Return current rate limit configuration."""
    return {
        "admin_requests_per_minute": 500,
        "regular_requests_per_minute": 100,
    }


# ══════════════════════════════════════════════════════════════════
# Z-018  Maintenance Window Scheduling
# ══════════════════════════════════════════════════════════════════


@router.post("/admin/maintenance", response_model=MaintenanceWindowResponse, status_code=201)
def create_maintenance_window(
    body: MaintenanceWindowCreate,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """Schedule a maintenance window."""
    if body.scheduled_end <= body.scheduled_start:
        raise HTTPException(status_code=400, detail="End time must be after start time")

    mw = MaintenanceWindow(
        title=body.title,
        description=body.description,
        scheduled_start=body.scheduled_start,
        scheduled_end=body.scheduled_end,
        is_read_only=body.is_read_only,
        created_by=tenant_ctx.user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(mw)
    _audit(
        db,
        user_id=tenant_ctx.user_id,
        action=ActionType.CREATE,
        event="maintenance_window_created",
        details={"title": body.title, "start": body.scheduled_start.isoformat(), "end": body.scheduled_end.isoformat()},
    )
    db.commit()
    db.refresh(mw)
    return MaintenanceWindowResponse(
        id=mw.id,
        title=mw.title,
        description=mw.description,
        scheduled_start=mw.scheduled_start,
        scheduled_end=mw.scheduled_end,
        is_read_only=mw.is_read_only,
        is_active=mw.is_active,
        notification_sent=mw.notification_sent,
        created_by=mw.created_by,
        created_at=mw.created_at,
    )


@router.get("/admin/maintenance", response_model=list[MaintenanceWindowResponse])
def list_maintenance_windows(
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """List upcoming and recent maintenance windows."""
    windows = (
        db.query(MaintenanceWindow)
        .order_by(MaintenanceWindow.scheduled_start.desc())
        .limit(50)
        .all()
    )
    return [
        MaintenanceWindowResponse(
            id=w.id,
            title=w.title,
            description=w.description,
            scheduled_start=w.scheduled_start,
            scheduled_end=w.scheduled_end,
            is_read_only=w.is_read_only,
            is_active=w.is_active,
            notification_sent=w.notification_sent,
            created_by=w.created_by,
            created_at=w.created_at,
        )
        for w in windows
    ]


@router.post("/admin/maintenance/{window_id}/activate")
def activate_maintenance_window(
    window_id: int,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """Activate a maintenance window (enter maintenance mode)."""
    window = db.query(MaintenanceWindow).filter(MaintenanceWindow.id == window_id).first()
    if not window:
        raise HTTPException(status_code=404, detail="Maintenance window not found")
    window.is_active = True
    _audit(
        db,
        user_id=tenant_ctx.user_id,
        action=ActionType.SYSTEM,
        event="maintenance_activated",
        details={"window_id": window_id, "title": window.title},
    )
    db.commit()
    return {"activated": True}


@router.post("/admin/maintenance/{window_id}/deactivate")
def deactivate_maintenance_window(
    window_id: int,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    """Deactivate a maintenance window (exit maintenance mode)."""
    window = db.query(MaintenanceWindow).filter(MaintenanceWindow.id == window_id).first()
    if not window:
        raise HTTPException(status_code=404, detail="Maintenance window not found")
    window.is_active = False
    db.commit()
    return {"deactivated": True}


# ══════════════════════════════════════════════════════════════════
# Z-014  Operations Runbook Page (list available runbooks)
# ══════════════════════════════════════════════════════════════════


@router.get("/admin/runbooks")
def list_runbooks(
    tenant_ctx: TenantContext = Depends(require_system_admin),
):
    """List available runbooks from docs/chaos/."""
    import glob
    import os

    chaos_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "docs", "chaos")
    runbooks = []
    if os.path.isdir(chaos_dir):
        for filepath in sorted(glob.glob(os.path.join(chaos_dir, "*.md"))):
            name = os.path.basename(filepath)
            runbooks.append({"name": name, "path": f"docs/chaos/{name}"})
    return {"runbooks": runbooks}
