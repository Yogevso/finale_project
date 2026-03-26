"""Quota enforcement helpers for tenant resource limits (Z-012)."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.errors import RateLimitExceededError
from app.models import Document, TenantQuota, User


def check_user_quota(db: Session, tenant_id: int) -> None:
    """Raise 429 if tenant has reached its max-user quota."""
    quota = db.query(TenantQuota).filter(TenantQuota.tenant_id == tenant_id).first()
    if not quota or quota.max_users is None:
        return
    current = db.query(func.count(User.id)).filter(User.tenant_id == tenant_id).scalar() or 0
    if current >= quota.max_users:
        raise RateLimitExceededError(
            f"Tenant user quota reached ({quota.max_users}). Contact your administrator."
        )


def check_document_quota(db: Session, tenant_id: int) -> None:
    """Raise 429 if tenant has reached its max-document quota."""
    quota = db.query(TenantQuota).filter(TenantQuota.tenant_id == tenant_id).first()
    if not quota or quota.max_documents is None:
        return
    current = db.query(func.count(Document.id)).filter(Document.tenant_id == tenant_id).scalar() or 0
    if current >= quota.max_documents:
        raise RateLimitExceededError(
            f"Tenant document quota reached ({quota.max_documents}). Contact your administrator."
        )
