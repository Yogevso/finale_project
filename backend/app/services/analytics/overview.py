"""Overview/recent-activity analytics module."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, List

from sqlalchemy import func, or_

from app.models import ActionType, AuditLog, Document, ReviewRequest, ReviewStatus, User
from app.schemas.analytics import CategoryCount, RecentActivity


class AnalyticsOverviewMixin:
    """Overview and activity feed analytics."""

    def get_overview(self, date_from: date, date_to: date) -> Dict:
        start_dt = datetime.combine(date_from, datetime.min.time())
        end_dt = datetime.combine(date_to, datetime.max.time())
        today_start = datetime.combine(date.today(), datetime.min.time())
        week_ago = today_start - timedelta(days=7)

        doc_query = self.db.query(Document)
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            doc_query = doc_query.filter(Document.tenant_id == self.tenant_ctx.tenant_id)
        total_documents = doc_query.count()

        user_query = self.db.query(User)
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            user_query = user_query.filter(User.tenant_id == self.tenant_ctx.tenant_id)
        total_users = user_query.count()

        audit_query = self.db.query(AuditLog).filter(AuditLog.created_at.between(start_dt, end_dt))
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            tenant_doc_ids = (
                self.db.query(Document.id)
                .filter(Document.tenant_id == self.tenant_ctx.tenant_id)
                .subquery()
            )
            audit_query = audit_query.filter(
                or_(AuditLog.document_id.in_(tenant_doc_ids), AuditLog.document_id.is_(None))
            )

        total_views = audit_query.filter(AuditLog.action == ActionType.VIEW).count()
        total_downloads = audit_query.filter(AuditLog.action == ActionType.DOWNLOAD).count()

        status_query = self.db.query(Document.status, func.count(Document.id)).group_by(
            Document.status
        )
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            status_query = status_query.filter(Document.tenant_id == self.tenant_ctx.tenant_id)
        documents_by_status = {
            status.value if status else "unknown": count for status, count in status_query.all()
        }

        cat_query = (
            self.db.query(Document.category, func.count(Document.id))
            .filter(Document.category.isnot(None))
            .group_by(Document.category)
        )
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            cat_query = cat_query.filter(Document.tenant_id == self.tenant_ctx.tenant_id)
        documents_by_category = [
            CategoryCount(category=cat or "Uncategorized", count=count)
            for cat, count in cat_query.all()
        ]

        review_query = self.db.query(ReviewRequest).filter(
            ReviewRequest.status == ReviewStatus.PENDING
        )
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            review_query = review_query.join(Document).filter(
                Document.tenant_id == self.tenant_ctx.tenant_id
            )
        pending_reviews = review_query.count()

        views_today_query = self.db.query(AuditLog).filter(
            AuditLog.action == ActionType.VIEW, AuditLog.created_at >= today_start
        )
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            views_today_query = views_today_query.filter(
                or_(
                    AuditLog.document_id.in_(
                        self.db.query(Document.id).filter(
                            Document.tenant_id == self.tenant_ctx.tenant_id
                        )
                    ),
                    AuditLog.document_id.is_(None),
                )
            )
        views_today = views_today_query.count()

        new_docs_query = self.db.query(Document).filter(Document.created_at >= week_ago)
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            new_docs_query = new_docs_query.filter(Document.tenant_id == self.tenant_ctx.tenant_id)
        new_docs_this_week = new_docs_query.count()

        return {
            "period_start": date_from,
            "period_end": date_to,
            "total_documents": total_documents,
            "total_users": total_users,
            "total_views": total_views,
            "total_downloads": total_downloads,
            "documents_by_status": documents_by_status,
            "documents_by_category": [c.model_dump() for c in documents_by_category],
            "pending_reviews": pending_reviews,
            "views_today": views_today,
            "new_docs_this_week": new_docs_this_week,
        }

    def get_recent_activity(self, limit: int = 10) -> List[RecentActivity]:
        query = self.db.query(AuditLog).join(User, AuditLog.user_id == User.id)

        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            tenant_doc_ids = (
                self.db.query(Document.id)
                .filter(Document.tenant_id == self.tenant_ctx.tenant_id)
                .subquery()
            )
            query = query.filter(
                or_(AuditLog.document_id.in_(tenant_doc_ids), AuditLog.document_id.is_(None))
            )

        logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()

        activities = []
        for log in logs:
            user = self.db.query(User).filter(User.id == log.user_id).first()
            doc = None
            if log.document_id:
                doc = self.db.query(Document).filter(Document.id == log.document_id).first()

            activities.append(
                RecentActivity(
                    id=log.id,
                    action=log.action.value if log.action else "unknown",
                    document_id=log.document_id,
                    document_title=doc.title if doc else None,
                    user_id=log.user_id,
                    user_name=user.full_name if user else "Unknown",
                    created_at=log.created_at.isoformat() if log.created_at else "",
                    details=log.details,
                )
            )

        return activities
