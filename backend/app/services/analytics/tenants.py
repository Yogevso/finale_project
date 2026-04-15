"""Cross-tenant analytics module."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict

from sqlalchemy import func

from app.models import ActionType, AuditLog, Document, Tenant, User
from app.schemas.analytics import TenantMetrics


class AnalyticsTenantsMixin:
    """System-wide tenant analytics."""

    def get_tenant_analytics(self, date_from: date, date_to: date) -> Dict:
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        tenants = self.db.query(Tenant).all()
        total_tenants = len(tenants)
        active_tenants = sum(1 for tenant in tenants if tenant.is_active)

        tenant_metrics = []
        for tenant in tenants:
            doc_count = self.db.query(Document).filter(Document.tenant_id == tenant.id).count()
            user_count = self.db.query(User).filter(User.tenant_id == tenant.id).count()

            # Get user IDs for this tenant from core DB, then query AuditLog from analytics DB
            tenant_user_ids = [
                row[0] for row in self.db.query(User.id).filter(User.tenant_id == tenant.id).all()
            ]
            active_user_ids = (
                (
                    self.analytics_db.query(func.distinct(AuditLog.user_id))
                    .filter(
                        AuditLog.user_id.in_(tenant_user_ids),
                        AuditLog.created_at >= thirty_days_ago,
                    )
                    .all()
                )
                if tenant_user_ids
                else []
            )
            active_users_30d = len(active_user_ids)

            tenant_doc_ids = [
                row[0]
                for row in self.db.query(Document.id).filter(Document.tenant_id == tenant.id).all()
            ]
            views_30d = (
                (
                    self.analytics_db.query(AuditLog)
                    .filter(
                        AuditLog.action == ActionType.VIEW,
                        AuditLog.created_at >= thirty_days_ago,
                        AuditLog.document_id.in_(tenant_doc_ids),
                    )
                    .count()
                )
                if tenant_doc_ids
                else 0
            )

            health_score = min(
                100,
                (
                    (active_users_30d / max(user_count, 1) * 40)
                    + (min(views_30d, 100) / 100 * 30)
                    + (min(doc_count, 50) / 50 * 30)
                ),
            )

            tenant_metrics.append(
                TenantMetrics(
                    tenant_id=tenant.id,
                    tenant_name=tenant.name,
                    tenant_slug=tenant.slug,
                    is_active=tenant.is_active,
                    total_documents=doc_count,
                    total_users=user_count,
                    active_users_30d=active_users_30d,
                    total_views_30d=views_30d,
                    health_score=round(health_score, 2),
                )
            )

        return {
            "period_start": date_from,
            "period_end": date_to,
            "total_tenants": total_tenants,
            "active_tenants": active_tenants,
            "tenants": [item.model_dump() for item in tenant_metrics],
        }
