"""Schemas for Wave AB — Experimentation and Growth Systems."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ── AB-001: Feature Flag Targeting ────────────────────────────────


class FeatureFlagTargetingUpdate(BaseModel):
    feature_key: str = Field(..., max_length=100)
    enabled: bool
    rollout_percentage: int = Field(default=100, ge=0, le=100)
    target_tenant_ids: list[int] | None = None


class FeatureFlagTargetingResponse(BaseModel):
    id: int
    tenant_id: int
    feature_key: str
    enabled: bool
    rollout_percentage: int | None = 100
    target_tenant_ids: list[int] | None = None
    updated_by: int | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── AB-002 / AB-003 / AB-004: Experiments ─────────────────────────


class ExperimentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    feature_flag_key: str | None = Field(default=None, max_length=100)
    variants: list[str] = Field(default=["control", "treatment"])
    traffic_percentage: int = Field(default=100, ge=1, le=100)
    primary_metric: str | None = Field(default=None, max_length=100)
    guardrail_metrics: list[str] | None = None
    guardrail_threshold: int = Field(default=10, ge=1, le=100)


class ExperimentUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    traffic_percentage: int | None = Field(default=None, ge=1, le=100)
    primary_metric: str | None = Field(default=None, max_length=100)
    guardrail_metrics: list[str] | None = None
    guardrail_threshold: int | None = Field(default=None, ge=1, le=100)


class ExperimentResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    feature_flag_key: str | None = None
    status: str
    variants: list[str]
    traffic_percentage: int
    primary_metric: str | None = None
    guardrail_metrics: list[str] | None = None
    guardrail_threshold: int
    winner_variant: str | None = None
    tenant_id: int | None = None
    created_by: int
    started_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExperimentAssignmentResponse(BaseModel):
    experiment_id: int
    user_id: int
    variant: str
    assigned_at: datetime

    class Config:
        from_attributes = True


class ExperimentMetricSnapshotCreate(BaseModel):
    variant: str = Field(..., max_length=100)
    metric_name: str = Field(..., max_length=100)
    metric_value: str = Field(..., max_length=50)
    sample_size: int = Field(default=0, ge=0)


class ExperimentMetricSnapshotResponse(BaseModel):
    id: int
    experiment_id: int
    variant: str
    metric_name: str
    metric_value: str
    sample_size: int
    recorded_at: datetime

    class Config:
        from_attributes = True


class ExperimentKillRequest(BaseModel):
    winner_variant: str | None = None  # If None, revert all to control


# ── AB-005: Onboarding Funnel ─────────────────────────────────────


class OnboardingEventCreate(BaseModel):
    user_id: int
    step: str = Field(..., max_length=50)


class OnboardingFunnelResponse(BaseModel):
    step: str
    count: int
    percentage: float


# ── AB-006: Activation Milestones ─────────────────────────────────


class ActivationMilestoneResponse(BaseModel):
    user_id: int
    milestones: list[dict[str, Any]]  # [{milestone, achieved_at}]


class UserActivationSummary(BaseModel):
    user_id: int
    username: str
    milestones_completed: int
    milestones_total: int
    milestones: list[str]


# ── AB-007: Retention Cohorts ─────────────────────────────────────


class RetentionCohortRow(BaseModel):
    cohort_week: str  # ISO week string e.g. "2026-W12"
    cohort_size: int
    retention_by_week: dict[int, float]  # week_offset: retention_rate


class RetentionCohortResponse(BaseModel):
    cohorts: list[RetentionCohortRow]


# ── AB-008: Churn Prediction ──────────────────────────────────────


class ChurnRiskUser(BaseModel):
    user_id: int
    username: str
    email: str
    last_login: datetime | None = None
    days_inactive: int
    risk_level: str  # "low", "medium", "high"


class ChurnPredictionResponse(BaseModel):
    at_risk_users: list[ChurnRiskUser]
    total_active: int
    total_at_risk: int


# ── AB-009: Webhooks ──────────────────────────────────────────────


class WebhookCreate(BaseModel):
    url: str = Field(..., max_length=2048)
    event_types: list[str]
    is_active: bool = True


class WebhookUpdate(BaseModel):
    url: str | None = Field(default=None, max_length=2048)
    event_types: list[str] | None = None
    is_active: bool | None = None


class WebhookResponse(BaseModel):
    id: int
    tenant_id: int
    url: str
    event_types: list[str]
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookDeliveryResponse(BaseModel):
    id: int
    webhook_id: int
    event_type: str
    response_status: int | None = None
    success: bool
    attempts: int
    delivered_at: datetime

    class Config:
        from_attributes = True


class WebhookDeliveryLogResponse(BaseModel):
    deliveries: list[WebhookDeliveryResponse]
    total_delivered: int
    success_rate: float


# ── AB-010: API Keys ──────────────────────────────────────────────


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    scopes: list[str] | None = None
    expires_in_days: int | None = Field(default=None, ge=1, le=365)


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    scopes: list[str] | None = None
    is_active: bool
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Returned only on creation — contains the full key (never shown again)."""

    full_key: str


# ── AB-011: Integration Health ────────────────────────────────────


class IntegrationHealthResponse(BaseModel):
    webhooks: dict[str, Any]  # {total, active, success_rate_24h, recent_failures}
    api_keys: dict[str, Any]  # {total, active, last_used}


# ── AB-014: Tech Debt ────────────────────────────────────────────


class TechDebtResponse(BaseModel):
    todo_count: int
    fixme_count: int
    total: int
    threshold: int
    passed: bool
    details: list[dict[str, Any]]  # [{file, line, text}]
