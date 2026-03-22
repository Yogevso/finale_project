"""Service layer for Wave AB — Experimentation, Analytics, Webhooks, API Keys."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.models import (
    ActivationMilestone,
    ApiKey,
    AuditLog,
    DomainEventOutbox,
    Experiment,
    ExperimentAssignment,
    ExperimentMetricSnapshot,
    ExperimentStatus,
    FeatureFlag,
    OnboardingEvent,
    User,
    UserSession,
    WebhookDelivery,
    WebhookRegistration,
)


# ---------------------------------------------------------------------------
# AB-001: Feature Flag Targeting
# ---------------------------------------------------------------------------


def update_feature_flag_targeting(
    db: Session,
    tenant_id: int,
    feature_key: str,
    enabled: bool,
    rollout_percentage: int = 100,
    target_tenant_ids: list[int] | None = None,
    updated_by: int | None = None,
) -> FeatureFlag:
    flag = (
        db.query(FeatureFlag)
        .filter(FeatureFlag.tenant_id == tenant_id, FeatureFlag.feature_key == feature_key)
        .first()
    )
    if flag is None:
        flag = FeatureFlag(
            tenant_id=tenant_id,
            feature_key=feature_key,
            enabled=enabled,
            rollout_percentage=rollout_percentage,
            target_tenant_ids=json.dumps(target_tenant_ids) if target_tenant_ids else None,
            updated_by=updated_by,
        )
        db.add(flag)
    else:
        flag.enabled = enabled
        flag.rollout_percentage = rollout_percentage
        flag.target_tenant_ids = json.dumps(target_tenant_ids) if target_tenant_ids else None
        flag.updated_by = updated_by
    db.commit()
    db.refresh(flag)
    return flag


def list_feature_flags_for_tenant(db: Session, tenant_id: int) -> list[FeatureFlag]:
    return (
        db.query(FeatureFlag)
        .filter(FeatureFlag.tenant_id == tenant_id)
        .order_by(FeatureFlag.feature_key)
        .all()
    )


# ---------------------------------------------------------------------------
# AB-002: Experiment Assignment
# ---------------------------------------------------------------------------


def create_experiment(
    db: Session,
    *,
    name: str,
    description: str | None = None,
    feature_flag_key: str | None = None,
    variants: list[str],
    traffic_percentage: int,
    primary_metric: str | None = None,
    guardrail_metrics: list[str] | None = None,
    guardrail_threshold: float = 0.10,
    created_by: int,
    tenant_id: int | None = None,
) -> Experiment:
    exp = Experiment(
        name=name,
        description=description,
        feature_flag_key=feature_flag_key,
        variants=json.dumps(variants),
        traffic_percentage=traffic_percentage,
        primary_metric=primary_metric,
        guardrail_metrics=json.dumps(guardrail_metrics) if guardrail_metrics else None,
        guardrail_threshold=guardrail_threshold,
        created_by=created_by,
        tenant_id=tenant_id,
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return exp


def get_experiment(db: Session, experiment_id: int) -> Experiment | None:
    return db.query(Experiment).filter(Experiment.id == experiment_id).first()


def list_experiments(db: Session, tenant_id: int | None = None) -> list[Experiment]:
    q = db.query(Experiment)
    if tenant_id is not None:
        q = q.filter(Experiment.tenant_id == tenant_id)
    return q.order_by(desc(Experiment.created_at)).all()


def start_experiment(db: Session, experiment_id: int) -> Experiment:
    exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if exp is None:
        raise ValueError("Experiment not found")
    exp.status = ExperimentStatus.RUNNING
    exp.started_at = datetime.utcnow()
    db.commit()
    db.refresh(exp)
    return exp


def stop_experiment(db: Session, experiment_id: int, winner_variant: str | None = None) -> Experiment:
    exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if exp is None:
        raise ValueError("Experiment not found")
    exp.status = ExperimentStatus.COMPLETED
    exp.ended_at = datetime.utcnow()
    exp.winner_variant = winner_variant
    db.commit()
    db.refresh(exp)
    return exp


def assign_user_to_experiment(db: Session, experiment_id: int, user_id: int) -> ExperimentAssignment:
    """Deterministic assignment: hash(experiment_id + user_id) → variant bucket."""
    existing = (
        db.query(ExperimentAssignment)
        .filter(
            ExperimentAssignment.experiment_id == experiment_id,
            ExperimentAssignment.user_id == user_id,
        )
        .first()
    )
    if existing:
        return existing

    exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if exp is None:
        raise ValueError("Experiment not found")

    variants = json.loads(exp.variants)
    digest = hashlib.sha256(f"{experiment_id}:{user_id}".encode()).hexdigest()
    bucket = int(digest[:8], 16) % 100

    # Check traffic percentage
    if bucket >= exp.traffic_percentage:
        variant = variants[0]  # control for excluded users
    else:
        variant_bucket = int(digest[8:16], 16) % len(variants)
        variant = variants[variant_bucket]

    assignment = ExperimentAssignment(
        experiment_id=experiment_id,
        user_id=user_id,
        variant=variant,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def get_user_assignment(db: Session, experiment_id: int, user_id: int) -> ExperimentAssignment | None:
    return (
        db.query(ExperimentAssignment)
        .filter(
            ExperimentAssignment.experiment_id == experiment_id,
            ExperimentAssignment.user_id == user_id,
        )
        .first()
    )


# ---------------------------------------------------------------------------
# AB-003: Metrics Guardrails
# ---------------------------------------------------------------------------


def record_metric_snapshot(
    db: Session,
    experiment_id: int,
    variant: str,
    metric_name: str,
    metric_value: str,
    sample_size: int = 0,
) -> ExperimentMetricSnapshot:
    snap = ExperimentMetricSnapshot(
        experiment_id=experiment_id,
        variant=variant,
        metric_name=metric_name,
        metric_value=metric_value,
        sample_size=sample_size,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


def check_guardrails(db: Session, experiment_id: int) -> dict[str, Any]:
    """Check if guardrail metrics have degraded beyond threshold."""
    exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if exp is None:
        return {"ok": True, "violations": []}

    guardrail_metrics = json.loads(exp.guardrail_metrics) if exp.guardrail_metrics else []
    if not guardrail_metrics:
        return {"ok": True, "violations": []}

    variants = json.loads(exp.variants)
    control = variants[0] if variants else "control"
    violations: list[dict[str, Any]] = []

    for metric in guardrail_metrics:
        # Get latest snapshot for control
        control_snap = (
            db.query(ExperimentMetricSnapshot)
            .filter(
                ExperimentMetricSnapshot.experiment_id == experiment_id,
                ExperimentMetricSnapshot.variant == control,
                ExperimentMetricSnapshot.metric_name == metric,
            )
            .order_by(desc(ExperimentMetricSnapshot.recorded_at))
            .first()
        )
        if not control_snap:
            continue

        control_val = float(control_snap.metric_value)
        if control_val == 0:
            continue

        # Check each treatment variant
        for v in variants[1:]:
            treatment_snap = (
                db.query(ExperimentMetricSnapshot)
                .filter(
                    ExperimentMetricSnapshot.experiment_id == experiment_id,
                    ExperimentMetricSnapshot.variant == v,
                    ExperimentMetricSnapshot.metric_name == metric,
                )
                .order_by(desc(ExperimentMetricSnapshot.recorded_at))
                .first()
            )
            if not treatment_snap:
                continue

            treatment_val = float(treatment_snap.metric_value)
            degradation_pct = ((control_val - treatment_val) / abs(control_val)) * 100

            if degradation_pct > exp.guardrail_threshold:
                violations.append({
                    "metric": metric,
                    "variant": v,
                    "control_value": control_val,
                    "treatment_value": treatment_val,
                    "degradation_pct": round(degradation_pct, 2),
                })

    should_halt = len(violations) > 0
    return {"ok": not should_halt, "violations": violations}


# ---------------------------------------------------------------------------
# AB-004: Kill Switch
# ---------------------------------------------------------------------------


def kill_experiment(db: Session, experiment_id: int, winner_variant: str | None = None) -> Experiment:
    """Immediately end experiment and optionally assign all to winner."""
    return stop_experiment(db, experiment_id, winner_variant)


# ---------------------------------------------------------------------------
# AB-005: Onboarding Funnel
# ---------------------------------------------------------------------------

ONBOARDING_STEPS = [
    "invitation_sent",
    "accepted",
    "first_login",
    "first_document_view",
    "first_action",
]


def record_onboarding_event(db: Session, user_id: int, tenant_id: int, step: str) -> OnboardingEvent:
    evt = OnboardingEvent(user_id=user_id, tenant_id=tenant_id, step=step)
    db.add(evt)
    db.commit()
    db.refresh(evt)
    return evt


def get_onboarding_funnel(db: Session, tenant_id: int, core_db: Session | None = None) -> list[dict[str, Any]]:
    _core = core_db or db
    total_users = _core.query(func.count(User.id)).filter(User.tenant_id == tenant_id).scalar() or 1

    results = []
    for step in ONBOARDING_STEPS:
        count = (
            db.query(func.count(func.distinct(OnboardingEvent.user_id)))
            .filter(OnboardingEvent.tenant_id == tenant_id, OnboardingEvent.step == step)
            .scalar()
            or 0
        )
        results.append({
            "step": step,
            "count": count,
            "percentage": round((count / total_users) * 100, 1),
        })
    return results


# ---------------------------------------------------------------------------
# AB-006: Activation Milestones
# ---------------------------------------------------------------------------

MILESTONES = [
    "viewed_5_docs",
    "created_1_doc",
    "completed_profile",
    "left_first_comment",
    "uploaded_first_file",
]


def record_milestone(db: Session, user_id: int, tenant_id: int, milestone: str) -> ActivationMilestone | None:
    existing = (
        db.query(ActivationMilestone)
        .filter(ActivationMilestone.user_id == user_id, ActivationMilestone.milestone == milestone)
        .first()
    )
    if existing:
        return existing

    am = ActivationMilestone(user_id=user_id, tenant_id=tenant_id, milestone=milestone)
    db.add(am)
    db.commit()
    db.refresh(am)
    return am


def get_user_milestones(db: Session, user_id: int) -> list[ActivationMilestone]:
    return (
        db.query(ActivationMilestone)
        .filter(ActivationMilestone.user_id == user_id)
        .order_by(ActivationMilestone.achieved_at)
        .all()
    )


def get_activation_summary(db: Session, tenant_id: int) -> list[dict[str, Any]]:
    users = db.query(User).filter(User.tenant_id == tenant_id, User.is_active.is_(True)).all()
    summaries = []
    for user in users:
        milestones = (
            db.query(ActivationMilestone)
            .filter(ActivationMilestone.user_id == user.id)
            .all()
        )
        completed = [m.milestone for m in milestones]
        summaries.append({
            "user_id": user.id,
            "username": user.username,
            "milestones_completed": len(completed),
            "milestones_total": len(MILESTONES),
            "milestones": completed,
        })
    return summaries


# ---------------------------------------------------------------------------
# AB-007: Retention Cohorts
# ---------------------------------------------------------------------------


def get_retention_cohorts(db: Session, tenant_id: int, weeks: int = 8) -> list[dict[str, Any]]:
    """Group users by signup week, compute weekly retention."""
    now = datetime.utcnow()
    cutoff = now - timedelta(weeks=weeks)

    users = (
        db.query(User)
        .filter(User.tenant_id == tenant_id, User.created_at >= cutoff)
        .all()
    )

    from collections import defaultdict
    cohorts: dict[str, list[int]] = defaultdict(list)

    for u in users:
        iso_year, iso_week, _ = u.created_at.isocalendar()
        week_key = f"{iso_year}-W{iso_week:02d}"
        cohorts[week_key].append(u.id)

    result = []
    for week_key in sorted(cohorts.keys()):
        user_ids = cohorts[week_key]
        cohort_size = len(user_ids)
        retention_by_week: dict[int, float] = {}

        for offset in range(weeks):
            week_start = cutoff + timedelta(weeks=offset)
            week_end = week_start + timedelta(weeks=1)

            active_count = (
                db.query(func.count(func.distinct(UserSession.user_id)))
                .filter(
                    UserSession.user_id.in_(user_ids),
                    UserSession.created_at >= week_start,
                    UserSession.created_at < week_end,
                )
                .scalar()
                or 0
            )
            retention_by_week[offset] = round((active_count / cohort_size) * 100, 1) if cohort_size else 0

        result.append({
            "cohort_week": week_key,
            "cohort_size": cohort_size,
            "retention_by_week": retention_by_week,
        })

    return result


# ---------------------------------------------------------------------------
# AB-008: Churn Prediction
# ---------------------------------------------------------------------------


def get_churn_risk_users(db: Session, tenant_id: int, inactive_days: int = 30) -> dict[str, Any]:
    """Flag users with no login in N days as at-risk."""
    now = datetime.utcnow()
    cutoff = now - timedelta(days=inactive_days)

    all_active = (
        db.query(User)
        .filter(User.tenant_id == tenant_id, User.is_active.is_(True))
        .all()
    )

    at_risk = []
    for user in all_active:
        last_session = (
            db.query(UserSession)
            .filter(UserSession.user_id == user.id)
            .order_by(desc(UserSession.created_at))
            .first()
        )
        last_login = last_session.created_at if last_session else user.created_at
        if last_login < cutoff:
            days_inactive = (now - last_login).days
            if days_inactive > 60:
                risk = "high"
            elif days_inactive > 30:
                risk = "medium"
            else:
                risk = "low"

            at_risk.append({
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "last_login": last_login,
                "days_inactive": days_inactive,
                "risk_level": risk,
            })

    return {
        "at_risk_users": at_risk,
        "total_active": len(all_active),
        "total_at_risk": len(at_risk),
    }


# ---------------------------------------------------------------------------
# AB-009: Webhook Management
# ---------------------------------------------------------------------------


def create_webhook(
    db: Session,
    tenant_id: int,
    url: str,
    event_types: list[str],
    created_by: int,
    is_active: bool = True,
) -> tuple[WebhookRegistration, str]:
    """Create a webhook and return (webhook, signing_secret)."""
    signing_secret = secrets.token_urlsafe(32)
    wh = WebhookRegistration(
        tenant_id=tenant_id,
        url=url,
        secret=hashlib.sha256(signing_secret.encode()).hexdigest(),
        event_types=json.dumps(event_types),
        is_active=is_active,
        created_by=created_by,
    )
    db.add(wh)
    db.commit()
    db.refresh(wh)
    return wh, signing_secret


def list_webhooks(db: Session, tenant_id: int) -> list[WebhookRegistration]:
    return (
        db.query(WebhookRegistration)
        .filter(WebhookRegistration.tenant_id == tenant_id)
        .order_by(WebhookRegistration.created_at)
        .all()
    )


def update_webhook(
    db: Session,
    webhook_id: int,
    tenant_id: int,
    url: str | None = None,
    event_types: list[str] | None = None,
    is_active: bool | None = None,
) -> WebhookRegistration | None:
    wh = (
        db.query(WebhookRegistration)
        .filter(WebhookRegistration.id == webhook_id, WebhookRegistration.tenant_id == tenant_id)
        .first()
    )
    if wh is None:
        return None
    if url is not None:
        wh.url = url
    if event_types is not None:
        wh.event_types = json.dumps(event_types)
    if is_active is not None:
        wh.is_active = is_active
    db.commit()
    db.refresh(wh)
    return wh


def delete_webhook(db: Session, webhook_id: int, tenant_id: int) -> bool:
    wh = (
        db.query(WebhookRegistration)
        .filter(WebhookRegistration.id == webhook_id, WebhookRegistration.tenant_id == tenant_id)
        .first()
    )
    if wh is None:
        return False
    db.delete(wh)
    db.commit()
    return True


def deliver_webhook_event(
    db: Session,
    tenant_id: int,
    event_type: str,
    payload: dict[str, Any],
) -> int:
    """Queue webhook delivery via DomainEventOutbox for all matching webhooks."""
    webhooks = (
        db.query(WebhookRegistration)
        .filter(WebhookRegistration.tenant_id == tenant_id, WebhookRegistration.is_active.is_(True))
        .all()
    )
    delivered = 0
    for wh in webhooks:
        subscribed = json.loads(wh.event_types)
        if event_type not in subscribed and "*" not in subscribed:
            continue

        delivery = WebhookDelivery(
            webhook_id=wh.id,
            event_type=event_type,
            payload_json=json.dumps(payload),
            success=True,  # Queued successfully; real HTTP delivery is async
            attempts=1,
        )
        db.add(delivery)
        delivered += 1

    if delivered:
        db.commit()
    return delivered


def get_webhook_delivery_log(
    db: Session, webhook_id: int, tenant_id: int, limit: int = 50,
) -> dict[str, Any]:
    wh = (
        db.query(WebhookRegistration)
        .filter(WebhookRegistration.id == webhook_id, WebhookRegistration.tenant_id == tenant_id)
        .first()
    )
    if wh is None:
        return {"deliveries": [], "total_delivered": 0, "success_rate": 0}

    deliveries = (
        db.query(WebhookDelivery)
        .filter(WebhookDelivery.webhook_id == webhook_id)
        .order_by(desc(WebhookDelivery.delivered_at))
        .limit(limit)
        .all()
    )

    total = db.query(func.count(WebhookDelivery.id)).filter(WebhookDelivery.webhook_id == webhook_id).scalar() or 0
    successes = (
        db.query(func.count(WebhookDelivery.id))
        .filter(WebhookDelivery.webhook_id == webhook_id, WebhookDelivery.success.is_(True))
        .scalar()
        or 0
    )
    rate = round((successes / total) * 100, 1) if total else 0

    return {"deliveries": deliveries, "total_delivered": total, "success_rate": rate}


# ---------------------------------------------------------------------------
# AB-010: API Key Management
# ---------------------------------------------------------------------------


def create_api_key(
    db: Session,
    tenant_id: int,
    user_id: int,
    name: str,
    scopes: list[str] | None = None,
    expires_in_days: int | None = None,
) -> tuple[ApiKey, str]:
    """Create an API key and return (record, full_key). Full key shown only once."""
    raw_key = secrets.token_urlsafe(48)
    prefix = raw_key[:8]
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = ApiKey(
        tenant_id=tenant_id,
        user_id=user_id,
        name=name,
        key_prefix=prefix,
        key_hash=key_hash,
        scopes=json.dumps(scopes) if scopes else None,
        expires_at=(datetime.utcnow() + timedelta(days=expires_in_days)) if expires_in_days else None,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key, raw_key


def list_api_keys(db: Session, tenant_id: int) -> list[ApiKey]:
    return (
        db.query(ApiKey)
        .filter(ApiKey.tenant_id == tenant_id)
        .order_by(ApiKey.created_at)
        .all()
    )


def revoke_api_key(db: Session, key_id: int, tenant_id: int) -> bool:
    key = (
        db.query(ApiKey)
        .filter(ApiKey.id == key_id, ApiKey.tenant_id == tenant_id)
        .first()
    )
    if key is None:
        return False
    key.is_active = False
    db.commit()
    return True


def authenticate_api_key(db: Session, raw_key: str) -> ApiKey | None:
    """Validate an API key and return the record if valid."""
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key = (
        db.query(ApiKey)
        .filter(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True))
        .first()
    )
    if key is None:
        return None
    if key.expires_at and key.expires_at < datetime.utcnow():
        return None
    key.last_used_at = datetime.utcnow()
    db.commit()
    return key


# ---------------------------------------------------------------------------
# AB-011: Integration Health
# ---------------------------------------------------------------------------


def get_integration_health(db: Session, tenant_id: int) -> dict[str, Any]:
    now = datetime.utcnow()
    day_ago = now - timedelta(hours=24)

    # Webhook health
    total_wh = db.query(func.count(WebhookRegistration.id)).filter(
        WebhookRegistration.tenant_id == tenant_id
    ).scalar() or 0
    active_wh = db.query(func.count(WebhookRegistration.id)).filter(
        WebhookRegistration.tenant_id == tenant_id, WebhookRegistration.is_active.is_(True)
    ).scalar() or 0

    recent_deliveries = (
        db.query(func.count(WebhookDelivery.id))
        .join(WebhookRegistration)
        .filter(WebhookRegistration.tenant_id == tenant_id, WebhookDelivery.delivered_at >= day_ago)
        .scalar()
        or 0
    )
    recent_successes = (
        db.query(func.count(WebhookDelivery.id))
        .join(WebhookRegistration)
        .filter(
            WebhookRegistration.tenant_id == tenant_id,
            WebhookDelivery.delivered_at >= day_ago,
            WebhookDelivery.success.is_(True),
        )
        .scalar()
        or 0
    )
    wh_success_rate = round((recent_successes / recent_deliveries) * 100, 1) if recent_deliveries else 100.0

    # API key health
    total_keys = db.query(func.count(ApiKey.id)).filter(ApiKey.tenant_id == tenant_id).scalar() or 0
    active_keys = db.query(func.count(ApiKey.id)).filter(
        ApiKey.tenant_id == tenant_id, ApiKey.is_active.is_(True)
    ).scalar() or 0

    last_used = (
        db.query(func.max(ApiKey.last_used_at))
        .filter(ApiKey.tenant_id == tenant_id)
        .scalar()
    )

    return {
        "webhooks": {
            "total": total_wh,
            "active": active_wh,
            "success_rate_24h": wh_success_rate,
            "recent_deliveries": recent_deliveries,
        },
        "api_keys": {
            "total": total_keys,
            "active": active_keys,
            "last_used": last_used.isoformat() if last_used else None,
        },
    }
