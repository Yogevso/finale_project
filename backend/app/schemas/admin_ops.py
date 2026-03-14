"""Schemas for Wave Z — Admin Operations and Tenant Management."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Z-001: Impersonation ──────────────────────────────────────────


class ImpersonateRequest(BaseModel):
    target_tenant_id: int


class ImpersonationSessionResponse(BaseModel):
    id: int
    admin_user_id: int
    target_tenant_id: int
    target_tenant_name: str | None = None
    session_token: str
    started_at: datetime
    ended_at: datetime | None = None
    is_active: bool

    class Config:
        from_attributes = True


# ── Z-002: Admin Action Queue ─────────────────────────────────────


class AdminActionCreate(BaseModel):
    action_type: str
    payload: dict[str, Any]
    reason: str | None = None
    target_tenant_id: int | None = None


class AdminActionReview(BaseModel):
    approved: bool
    comment: str | None = None


class AdminActionResponse(BaseModel):
    id: int
    action_type: str
    status: str
    payload: str  # JSON string
    reason: str | None = None
    requested_by: int
    requester_name: str | None = None
    reviewed_by: int | None = None
    reviewer_name: str | None = None
    review_comment: str | None = None
    target_tenant_id: int | None = None
    target_tenant_name: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None
    executed_at: datetime | None = None

    class Config:
        from_attributes = True


# ── Z-003: Bulk Operations ────────────────────────────────────────


class BulkTenantSettingsUpdate(BaseModel):
    tenant_ids: list[int]
    settings: dict[str, Any]


class BulkAnnouncementSend(BaseModel):
    tenant_ids: list[int] | None = None  # None = all tenants
    message: str = Field(..., max_length=500)
    type: str = Field(default="info", pattern=r"^(info|warning|success)$")


# ── Z-004: Tenant Configuration ───────────────────────────────────


class TenantConfigUpdate(BaseModel):
    settings: dict[str, Any]


class TenantConfigResponse(BaseModel):
    tenant_id: int
    tenant_name: str
    settings: dict[str, Any]

    class Config:
        from_attributes = True


# ── Z-005: Feature Flags ──────────────────────────────────────────


class FeatureFlagUpdate(BaseModel):
    feature_key: str = Field(..., max_length=100)
    enabled: bool


class FeatureFlagResponse(BaseModel):
    id: int
    tenant_id: int
    feature_key: str
    enabled: bool
    updated_by: int | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FeatureMatrixResponse(BaseModel):
    tenants: list[dict[str, Any]]  # [{tenant_id, tenant_name, features: {key: bool}}]


# ── Z-006: Status Page ────────────────────────────────────────────


class ServiceStatus(BaseModel):
    name: str
    status: str  # "healthy", "degraded", "down"
    latency_ms: float | None = None
    details: str | None = None


class SystemStatusResponse(BaseModel):
    overall: str  # "healthy", "degraded", "down"
    services: list[ServiceStatus]
    checked_at: datetime


# ── Z-007: SLA / Performance Reporting ────────────────────────────


class TenantPerformanceResponse(BaseModel):
    tenant_id: int
    tenant_name: str
    p50_ms: float
    p95_ms: float
    error_rate: float
    active_users: int
    period_start: datetime
    period_end: datetime


# ── Z-008: Provisioning ──────────────────────────────────────────


class TenantProvisionRequest(BaseModel):
    tenant_name: str = Field(..., min_length=2, max_length=255)
    tenant_slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    admin_username: str = Field(..., min_length=3, max_length=50)
    admin_email: str
    admin_password: str = Field(..., min_length=8)
    company_type: str = Field(default="customer", pattern=r"^(customer|partner|internal)$")
    contact_email: str | None = None


class TenantProvisionResponse(BaseModel):
    tenant_id: int
    tenant_name: str
    tenant_slug: str
    admin_user_id: int
    admin_username: str


# ── Z-009: Suspension ─────────────────────────────────────────────


class TenantSuspendRequest(BaseModel):
    reason: str | None = None


# ── Z-010: Domain Verification ────────────────────────────────────


class DomainVerificationCreate(BaseModel):
    domain: str = Field(..., max_length=255)


class DomainVerificationResponse(BaseModel):
    id: int
    tenant_id: int
    domain: str
    verification_token: str
    status: str
    verified_at: datetime | None = None
    created_at: datetime
    expires_at: datetime

    class Config:
        from_attributes = True


# ── Z-011: Custom Branding ────────────────────────────────────────


class TenantBrandingUpdate(BaseModel):
    logo_url: str | None = None
    primary_color: str | None = Field(None, max_length=7, pattern=r"^#[0-9a-fA-F]{6}$")
    accent_color: str | None = Field(None, max_length=7, pattern=r"^#[0-9a-fA-F]{6}$")
    portal_header_text: str | None = Field(None, max_length=255)


class TenantBrandingResponse(BaseModel):
    tenant_id: int
    logo_url: str | None = None
    primary_color: str | None = None
    accent_color: str | None = None
    portal_header_text: str | None = None


# ── Z-012: Quota ──────────────────────────────────────────────────


class TenantQuotaUpdate(BaseModel):
    max_users: int | None = None
    max_documents: int | None = None
    max_storage_mb: int | None = None


class TenantQuotaResponse(BaseModel):
    tenant_id: int
    max_users: int | None = None
    max_documents: int | None = None
    max_storage_mb: int | None = None
    current_users: int = 0
    current_documents: int = 0
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


# ── Z-015: Tenant Export/Import ───────────────────────────────────


class TenantExportResponse(BaseModel):
    tenant_id: int
    tenant_name: str
    export_data: dict[str, Any]
    exported_at: datetime


# ── Z-017: Rate Limiting ─────────────────────────────────────────


class RateLimitConfig(BaseModel):
    admin_requests_per_minute: int = 500
    regular_requests_per_minute: int = 100


# ── Z-018: Maintenance Window ─────────────────────────────────────


class MaintenanceWindowCreate(BaseModel):
    title: str = Field(..., max_length=255)
    description: str | None = None
    scheduled_start: datetime
    scheduled_end: datetime
    is_read_only: bool = True


class MaintenanceWindowResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    scheduled_start: datetime
    scheduled_end: datetime
    is_read_only: bool
    is_active: bool
    notification_sent: bool
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True
