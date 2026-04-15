"""API endpoints for Wave AB — Experimentation and Growth Systems."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_analytics_db, get_db
from app.dependencies.tenant import TenantContext, get_tenant_context, require_system_admin
from app.models import Experiment, ExperimentStatus
from app.schemas.experimentation import (
    ActivationMilestoneResponse,
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    ChurnPredictionResponse,
    ChurnRiskUser,
    ExperimentAssignmentResponse,
    ExperimentCreate,
    ExperimentKillRequest,
    ExperimentMetricSnapshotCreate,
    ExperimentMetricSnapshotResponse,
    ExperimentResponse,
    FeatureFlagTargetingResponse,
    FeatureFlagTargetingUpdate,
    IntegrationHealthResponse,
    OnboardingEventCreate,
    OnboardingFunnelResponse,
    RetentionCohortResponse,
    RetentionCohortRow,
    UserActivationSummary,
    WebhookCreate,
    WebhookDeliveryLogResponse,
    WebhookDeliveryResponse,
    WebhookResponse,
    WebhookUpdate,
)
from app.services.experimentation_service import (
    assign_user_to_experiment,
    authenticate_api_key,
    check_guardrails,
    create_api_key,
    create_experiment,
    create_webhook,
    delete_webhook,
    deliver_webhook_event,
    get_activation_summary,
    get_churn_risk_users,
    get_experiment,
    get_integration_health,
    get_onboarding_funnel,
    get_retention_cohorts,
    get_user_assignment,
    get_user_milestones,
    get_webhook_delivery_log,
    kill_experiment,
    list_api_keys,
    list_experiments,
    list_feature_flags_for_tenant,
    list_webhooks,
    record_metric_snapshot,
    record_milestone,
    record_onboarding_event,
    revoke_api_key,
    start_experiment,
    stop_experiment,
    update_feature_flag_targeting,
    update_webhook,
)

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────


def _parse_json_field(val: str | None) -> list[Any] | None:
    if val is None:
        return None
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return None


def _experiment_to_response(exp: Experiment) -> ExperimentResponse:
    return ExperimentResponse(
        id=exp.id,
        name=exp.name,
        description=exp.description,
        feature_flag_key=exp.feature_flag_key,
        status=exp.status.value if isinstance(exp.status, ExperimentStatus) else exp.status,
        variants=_parse_json_field(exp.variants) or [],
        traffic_percentage=exp.traffic_percentage,
        primary_metric=exp.primary_metric,
        guardrail_metrics=_parse_json_field(exp.guardrail_metrics),
        guardrail_threshold=exp.guardrail_threshold,
        winner_variant=exp.winner_variant,
        tenant_id=exp.tenant_id,
        created_by=exp.created_by,
        started_at=exp.started_at,
        ended_at=exp.ended_at,
        created_at=exp.created_at,
        updated_at=exp.updated_at,
    )


def _flag_response(flag) -> FeatureFlagTargetingResponse:
    return FeatureFlagTargetingResponse(
        id=flag.id,
        tenant_id=flag.tenant_id,
        feature_key=flag.feature_key,
        enabled=flag.enabled,
        rollout_percentage=flag.rollout_percentage,
        target_tenant_ids=_parse_json_field(flag.target_tenant_ids),
        updated_by=flag.updated_by,
        created_at=flag.created_at,
        updated_at=flag.updated_at,
    )


# ╔═══════════════════════════════════════════════════════════════╗
# ║  AB-001: Feature Flag Targeting                               ║
# ╚═══════════════════════════════════════════════════════════════╝


@router.get("/admin/feature-flags", response_model=list[FeatureFlagTargetingResponse])
def list_flags(
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
    tenant_id: int = Query(...),
):
    flags = list_feature_flags_for_tenant(db, tenant_id)
    return [_flag_response(f) for f in flags]


@router.put("/admin/feature-flags", response_model=FeatureFlagTargetingResponse)
def upsert_flag(
    body: FeatureFlagTargetingUpdate,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
    tenant_id: int = Query(...),
):
    flag = update_feature_flag_targeting(
        db,
        tenant_id=tenant_id,
        feature_key=body.feature_key,
        enabled=body.enabled,
        rollout_percentage=body.rollout_percentage,
        target_tenant_ids=body.target_tenant_ids,
        updated_by=tenant_ctx.user_id,
    )
    return _flag_response(flag)


# ╔═══════════════════════════════════════════════════════════════╗
# ║  AB-002/003/004: Experiments                                  ║
# ╚═══════════════════════════════════════════════════════════════╝


@router.get("/experiments", response_model=list[ExperimentResponse])
def list_experiments_endpoint(
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    exps = list_experiments(db)
    return [_experiment_to_response(e) for e in exps]


@router.post("/experiments", response_model=ExperimentResponse, status_code=201)
def create_experiment_endpoint(
    body: ExperimentCreate,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    exp = create_experiment(
        db,
        name=body.name,
        description=body.description,
        feature_flag_key=body.feature_flag_key,
        variants=body.variants,
        traffic_percentage=body.traffic_percentage,
        primary_metric=body.primary_metric,
        guardrail_metrics=body.guardrail_metrics,
        guardrail_threshold=body.guardrail_threshold,
        created_by=tenant_ctx.user_id,
        tenant_id=tenant_ctx.tenant_id,
    )
    return _experiment_to_response(exp)


@router.get("/experiments/{experiment_id}", response_model=ExperimentResponse)
def get_experiment_endpoint(
    experiment_id: int,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    exp = get_experiment(db, experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return _experiment_to_response(exp)


@router.post("/experiments/{experiment_id}/start", response_model=ExperimentResponse)
def start_experiment_endpoint(
    experiment_id: int,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    try:
        exp = start_experiment(db, experiment_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _experiment_to_response(exp)


@router.post("/experiments/{experiment_id}/stop", response_model=ExperimentResponse)
def stop_experiment_endpoint(
    experiment_id: int,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    try:
        exp = stop_experiment(db, experiment_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _experiment_to_response(exp)


@router.post("/experiments/{experiment_id}/kill", response_model=ExperimentResponse)
def kill_experiment_endpoint(
    experiment_id: int,
    body: ExperimentKillRequest,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    try:
        exp = kill_experiment(db, experiment_id, body.winner_variant)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _experiment_to_response(exp)


@router.post(
    "/experiments/{experiment_id}/assign/{user_id}",
    response_model=ExperimentAssignmentResponse,
)
def assign_user_endpoint(
    experiment_id: int,
    user_id: int,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    try:
        assignment = assign_user_to_experiment(db, experiment_id, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ExperimentAssignmentResponse(
        experiment_id=assignment.experiment_id,
        user_id=assignment.user_id,
        variant=assignment.variant,
        assigned_at=assignment.assigned_at,
    )


@router.get(
    "/experiments/{experiment_id}/assignment/{user_id}",
    response_model=ExperimentAssignmentResponse | None,
)
def get_assignment_endpoint(
    experiment_id: int,
    user_id: int,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    a = get_user_assignment(db, experiment_id, user_id)
    if not a:
        return None
    return ExperimentAssignmentResponse(
        experiment_id=a.experiment_id,
        user_id=a.user_id,
        variant=a.variant,
        assigned_at=a.assigned_at,
    )


@router.post(
    "/experiments/{experiment_id}/metrics",
    response_model=ExperimentMetricSnapshotResponse,
    status_code=201,
)
def record_metric_endpoint(
    experiment_id: int,
    body: ExperimentMetricSnapshotCreate,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    snap = record_metric_snapshot(
        db,
        experiment_id=experiment_id,
        variant=body.variant,
        metric_name=body.metric_name,
        metric_value=body.metric_value,
        sample_size=body.sample_size,
    )
    return ExperimentMetricSnapshotResponse(
        id=snap.id,
        experiment_id=snap.experiment_id,
        variant=snap.variant,
        metric_name=snap.metric_name,
        metric_value=snap.metric_value,
        sample_size=snap.sample_size,
        recorded_at=snap.recorded_at,
    )


@router.get("/experiments/{experiment_id}/guardrails")
def check_guardrails_endpoint(
    experiment_id: int,
    tenant_ctx: TenantContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    return check_guardrails(db, experiment_id)


# ╔═══════════════════════════════════════════════════════════════╗
# ║  AB-005: Onboarding Funnel                                   ║
# ╚═══════════════════════════════════════════════════════════════╝


@router.get("/analytics/onboarding-funnel", response_model=list[OnboardingFunnelResponse])
def onboarding_funnel_endpoint(
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_analytics_db),
    core_db: Session = Depends(get_db),
):
    data = get_onboarding_funnel(db, tenant_ctx.tenant_id, core_db=core_db)
    return [OnboardingFunnelResponse(**d) for d in data]


@router.post("/analytics/onboarding-event", status_code=201)
def record_onboarding_endpoint(
    body: OnboardingEventCreate,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_analytics_db),
):
    record_onboarding_event(db, body.user_id, tenant_ctx.tenant_id, body.step)
    return {"ok": True}


# ╔═══════════════════════════════════════════════════════════════╗
# ║  AB-006: Activation Milestones                                ║
# ╚═══════════════════════════════════════════════════════════════╝


@router.get("/analytics/activation/{user_id}", response_model=ActivationMilestoneResponse)
def user_milestones_endpoint(
    user_id: int,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_analytics_db),
):
    milestones = get_user_milestones(db, user_id)
    return ActivationMilestoneResponse(
        user_id=user_id,
        milestones=[
            {"milestone": m.milestone, "achieved_at": m.achieved_at.isoformat()} for m in milestones
        ],
    )


@router.post("/analytics/activation/{user_id}/milestone", status_code=201)
def record_milestone_endpoint(
    user_id: int,
    milestone: str = Query(..., max_length=50),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_analytics_db),
):
    record_milestone(db, user_id, tenant_ctx.tenant_id, milestone)
    return {"ok": True}


@router.get("/analytics/activation-summary", response_model=list[UserActivationSummary])
def activation_summary_endpoint(
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_analytics_db),
):
    data = get_activation_summary(db, tenant_ctx.tenant_id)
    return [UserActivationSummary(**d) for d in data]


# ╔═══════════════════════════════════════════════════════════════╗
# ║  AB-007: Retention Cohorts                                    ║
# ╚═══════════════════════════════════════════════════════════════╝


@router.get("/analytics/retention-cohorts", response_model=RetentionCohortResponse)
def retention_cohorts_endpoint(
    weeks: int = Query(default=8, ge=1, le=52),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    data = get_retention_cohorts(db, tenant_ctx.tenant_id, weeks)
    return RetentionCohortResponse(cohorts=[RetentionCohortRow(**d) for d in data])


# ╔═══════════════════════════════════════════════════════════════╗
# ║  AB-008: Churn Prediction                                     ║
# ╚═══════════════════════════════════════════════════════════════╝


@router.get("/analytics/churn-risk", response_model=ChurnPredictionResponse)
def churn_risk_endpoint(
    inactive_days: int = Query(default=30, ge=7),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    data = get_churn_risk_users(db, tenant_ctx.tenant_id, inactive_days)
    return ChurnPredictionResponse(
        at_risk_users=[ChurnRiskUser(**u) for u in data["at_risk_users"]],
        total_active=data["total_active"],
        total_at_risk=data["total_at_risk"],
    )


# ╔═══════════════════════════════════════════════════════════════╗
# ║  AB-009: Webhooks                                             ║
# ╚═══════════════════════════════════════════════════════════════╝


@router.get("/webhooks", response_model=list[WebhookResponse])
def list_webhooks_endpoint(
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    hooks = list_webhooks(db, tenant_ctx.tenant_id)
    return [
        WebhookResponse(
            id=h.id,
            tenant_id=h.tenant_id,
            url=h.url,
            event_types=_parse_json_field(h.event_types) or [],
            is_active=h.is_active,
            created_by=h.created_by,
            created_at=h.created_at,
            updated_at=h.updated_at,
        )
        for h in hooks
    ]


@router.post("/webhooks", response_model=WebhookResponse, status_code=201)
def create_webhook_endpoint(
    body: WebhookCreate,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    wh, _secret = create_webhook(
        db,
        tenant_id=tenant_ctx.tenant_id,
        url=body.url,
        event_types=body.event_types,
        created_by=tenant_ctx.user_id,
        is_active=body.is_active,
    )
    return WebhookResponse(
        id=wh.id,
        tenant_id=wh.tenant_id,
        url=wh.url,
        event_types=_parse_json_field(wh.event_types) or [],
        is_active=wh.is_active,
        created_by=wh.created_by,
        created_at=wh.created_at,
        updated_at=wh.updated_at,
    )


@router.put("/webhooks/{webhook_id}", response_model=WebhookResponse)
def update_webhook_endpoint(
    webhook_id: int,
    body: WebhookUpdate,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    wh = update_webhook(
        db,
        webhook_id,
        tenant_ctx.tenant_id,
        url=body.url,
        event_types=body.event_types,
        is_active=body.is_active,
    )
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return WebhookResponse(
        id=wh.id,
        tenant_id=wh.tenant_id,
        url=wh.url,
        event_types=_parse_json_field(wh.event_types) or [],
        is_active=wh.is_active,
        created_by=wh.created_by,
        created_at=wh.created_at,
        updated_at=wh.updated_at,
    )


@router.delete("/webhooks/{webhook_id}", status_code=204)
def delete_webhook_endpoint(
    webhook_id: int,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    if not delete_webhook(db, webhook_id, tenant_ctx.tenant_id):
        raise HTTPException(status_code=404, detail="Webhook not found")


@router.get("/webhooks/{webhook_id}/deliveries", response_model=WebhookDeliveryLogResponse)
def webhook_deliveries_endpoint(
    webhook_id: int,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    data = get_webhook_delivery_log(db, webhook_id, tenant_ctx.tenant_id)
    return WebhookDeliveryLogResponse(
        deliveries=[
            WebhookDeliveryResponse(
                id=d.id,
                webhook_id=d.webhook_id,
                event_type=d.event_type,
                response_status=d.response_status,
                success=d.success,
                attempts=d.attempts,
                delivered_at=d.delivered_at,
            )
            for d in data["deliveries"]
        ],
        total_delivered=data["total_delivered"],
        success_rate=data["success_rate"],
    )


@router.post("/webhooks/test-deliver", status_code=200)
def test_deliver_endpoint(
    event_type: str = Query(..., max_length=120),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    count = deliver_webhook_event(db, tenant_ctx.tenant_id, event_type, {"test": True})
    return {"delivered_to": count}


# ╔═══════════════════════════════════════════════════════════════╗
# ║  AB-010: API Keys                                             ║
# ╚═══════════════════════════════════════════════════════════════╝


@router.get("/api-keys", response_model=list[ApiKeyResponse])
def list_api_keys_endpoint(
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    keys = list_api_keys(db, tenant_ctx.tenant_id)
    return [
        ApiKeyResponse(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            scopes=_parse_json_field(k.scopes),
            is_active=k.is_active,
            last_used_at=k.last_used_at,
            expires_at=k.expires_at,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.post("/api-keys", response_model=ApiKeyCreatedResponse, status_code=201)
def create_api_key_endpoint(
    body: ApiKeyCreate,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    key, raw = create_api_key(
        db,
        tenant_id=tenant_ctx.tenant_id,
        user_id=tenant_ctx.user_id,
        name=body.name,
        scopes=body.scopes,
        expires_in_days=body.expires_in_days,
    )
    return ApiKeyCreatedResponse(
        id=key.id,
        name=key.name,
        key_prefix=key.key_prefix,
        scopes=_parse_json_field(key.scopes),
        is_active=key.is_active,
        last_used_at=key.last_used_at,
        expires_at=key.expires_at,
        created_at=key.created_at,
        full_key=raw,
    )


@router.delete("/api-keys/{key_id}", status_code=204)
def revoke_api_key_endpoint(
    key_id: int,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    if not revoke_api_key(db, key_id, tenant_ctx.tenant_id):
        raise HTTPException(status_code=404, detail="API key not found")


@router.post("/api-keys/verify")
def verify_api_key_endpoint(
    raw_key: str = Query(..., min_length=10),
    db: Session = Depends(get_db),
):
    key = authenticate_api_key(db, raw_key)
    if not key:
        raise HTTPException(status_code=401, detail="Invalid or expired API key")
    return {"valid": True, "key_id": key.id, "tenant_id": key.tenant_id}


# ╔═══════════════════════════════════════════════════════════════╗
# ║  AB-011: Integration Health                                   ║
# ╚═══════════════════════════════════════════════════════════════╝


@router.get("/integrations/health", response_model=IntegrationHealthResponse)
def integration_health_endpoint(
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    return get_integration_health(db, tenant_ctx.tenant_id)


# ╔═══════════════════════════════════════════════════════════════╗
# ║  AB-012: API Developer Portal (served as JSON spec)           ║
# ╚═══════════════════════════════════════════════════════════════╝


@router.get("/developer/api-docs")
def api_developer_portal():
    """Return a summary of the public API for the developer portal page."""
    return {
        "title": "Intel Documentation Platform API",
        "version": "1.0.0",
        "description": "Programmatic access to the Intel Documentation Platform. Use API keys for authentication.",
        "authentication": {
            "type": "API Key",
            "header": "X-API-Key",
            "instructions": "Generate an API key from the admin panel. Include it in the X-API-Key header.",
        },
        "endpoints": [
            {"method": "GET", "path": "/api/v1/documents", "description": "List documents"},
            {
                "method": "GET",
                "path": "/api/v1/documents/{id}",
                "description": "Get document detail",
            },
            {
                "method": "POST",
                "path": "/api/v1/documents/upload",
                "description": "Upload document",
            },
            {"method": "GET", "path": "/api/v1/search", "description": "Search documents"},
            {"method": "GET", "path": "/api/v1/companies", "description": "List companies"},
            {
                "method": "GET",
                "path": "/api/v1/analytics/overview",
                "description": "Analytics overview",
            },
            {
                "method": "GET",
                "path": "/api/v1/webhooks",
                "description": "List registered webhooks",
            },
            {"method": "POST", "path": "/api/v1/webhooks", "description": "Register a webhook"},
        ],
        "rate_limits": {"default": "100 requests/minute", "admin": "500 requests/minute"},
        "openapi_spec": "/openapi.json",
    }


# ╔═══════════════════════════════════════════════════════════════╗
# ║  AB-013: Internal Playbook Search                             ║
# ╚═══════════════════════════════════════════════════════════════╝


@router.get("/admin/playbooks")
def list_playbooks(
    q: str = Query(default="", max_length=200),
    tenant_ctx: TenantContext = Depends(require_system_admin),
):
    """List available internal playbooks/runbooks."""
    import os

    docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "docs")
    playbooks: list[dict[str, str]] = []

    search_dirs = [
        ("docs", docs_dir),
        ("docs/chaos", os.path.join(docs_dir, "chaos")),
        ("docs/adr", os.path.join(docs_dir, "adr")),
        ("docs/compliance", os.path.join(docs_dir, "compliance")),
        ("docs/migrations", os.path.join(docs_dir, "migrations")),
    ]

    for label, dirpath in search_dirs:
        if not os.path.isdir(dirpath):
            continue
        for fname in sorted(os.listdir(dirpath)):
            if not fname.endswith(".md"):
                continue
            title = fname.replace("-", " ").replace("_", " ").replace(".md", "").title()
            path = f"{label}/{fname}"
            if q and q.lower() not in title.lower() and q.lower() not in path.lower():
                continue
            playbooks.append({"title": title, "path": path})

    return playbooks


# ╔═══════════════════════════════════════════════════════════════╗
# ║  AB-015 / AB-016: Trust Center & Security Questionnaire       ║
# ╚═══════════════════════════════════════════════════════════════╝


@router.get("/public/trust-center")
def trust_center():
    """Public trust center page data."""
    return {
        "title": "Intel Documentation Platform — Trust Center",
        "security_practices": [
            "All data encrypted at rest (AES-256) and in transit (TLS 1.2+)",
            "Role-based access control with 6-tier permission model",
            "Audit logging with HMAC integrity signing",
            "Automated vulnerability scanning in CI/CD pipeline",
            "Session management with revocation support",
            "Container images run as non-root users",
        ],
        "data_handling": [
            "Multi-tenant architecture with strict data isolation",
            "GDPR Article 20 data export available on request",
            "Right to erasure (Article 17) supported",
            "Data retention policies configurable per tenant",
        ],
        "compliance": [
            "SOC 2 evidence collection automated",
            "WCAG 2.1 AA accessibility standards",
            "GDPR/CCPA policy mapping documented",
        ],
        "contact": "security@example.com",
    }


@router.get("/public/security-questionnaire")
def security_questionnaire():
    """Public security questionnaire FAQ."""
    return {
        "title": "Security Questionnaire — FAQ",
        "questions": [
            {
                "q": "How is data encrypted?",
                "a": "All data is encrypted at rest using AES-256 and in transit using TLS 1.2+.",
            },
            {
                "q": "What access controls are in place?",
                "a": "RBAC with 6 roles: system_admin, admin, manager, editor, viewer, customer. All API endpoints enforce role checks.",
            },
            {
                "q": "How are passwords stored?",
                "a": "Passwords are hashed using bcrypt with automatic salt generation. Plaintext passwords are never stored.",
            },
            {
                "q": "What is your incident response process?",
                "a": "We follow a documented incident runbook with RTO of 4 hours and RPO of 1 hour. All incidents are logged in the audit trail.",
            },
            {
                "q": "Do you support SSO/SAML?",
                "a": "The platform uses JWT-based authentication. SSO integration is on the roadmap.",
            },
            {
                "q": "How do you handle data deletion requests?",
                "a": "GDPR Article 17 right-to-erasure is supported. Users can request data deletion, which is processed after admin approval.",
            },
            {
                "q": "Are your containers secured?",
                "a": "All containers run as non-root users. Container images are scanned for vulnerabilities in CI.",
            },
            {
                "q": "Do you perform penetration testing?",
                "a": "We run automated security scanning including dependency audits (pip-audit, npm audit) and have documented chaos/DR testing procedures.",
            },
        ],
    }
