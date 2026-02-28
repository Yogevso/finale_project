"""Content production analytics module."""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, Optional

from sqlalchemy import func

from app.models import Comment, Document, ReviewRequest, ReviewStatus, Version
from app.schemas.analytics import TimeGranularity, TimeSeriesPoint


class AnalyticsContentMixin:
    """Content creation, publication, and review analytics."""

    def get_content_analytics(
        self,
        date_from: date,
        date_to: date,
        granularity: Optional[TimeGranularity] = None,
    ) -> Dict:
        if not granularity:
            granularity = self._auto_granularity(date_from, date_to)

        start_dt = datetime.combine(date_from, datetime.min.time())
        end_dt = datetime.combine(date_to, datetime.max.time())

        doc_date_trunc = self._get_date_trunc(granularity, Document.created_at)
        docs_query = (
            self.db.query(doc_date_trunc.label("date"), func.count(Document.id).label("value"))
            .filter(Document.created_at.between(start_dt, end_dt))
            .group_by(doc_date_trunc)
            .order_by(doc_date_trunc)
        )
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            docs_query = docs_query.filter(Document.tenant_id == self.tenant_ctx.tenant_id)
        docs_over_time = [
            TimeSeriesPoint(date=str(row.date), value=row.value) for row in docs_query.all()
        ]

        ver_date_trunc = self._get_date_trunc(granularity, Version.published_at)
        versions_query = (
            self.db.query(ver_date_trunc.label("date"), func.count(Version.id).label("value"))
            .filter(
                Version.is_published.is_(True),
                Version.published_at.isnot(None),
                Version.published_at.between(start_dt, end_dt),
            )
            .group_by(ver_date_trunc)
            .order_by(ver_date_trunc)
        )
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            versions_query = versions_query.join(Document).filter(
                Document.tenant_id == self.tenant_ctx.tenant_id
            )
        versions_over_time = [
            TimeSeriesPoint(date=str(row.date), value=row.value) for row in versions_query.all()
        ]

        comment_date_trunc = self._get_date_trunc(granularity, Comment.created_at)
        comments_query = (
            self.db.query(comment_date_trunc.label("date"), func.count(Comment.id).label("value"))
            .filter(Comment.created_at.between(start_dt, end_dt))
            .group_by(comment_date_trunc)
            .order_by(comment_date_trunc)
        )
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            comments_query = comments_query.join(Document).filter(
                Document.tenant_id == self.tenant_ctx.tenant_id
            )
        comments_over_time = [
            TimeSeriesPoint(date=str(row.date), value=row.value) for row in comments_query.all()
        ]

        review_query = self.db.query(ReviewRequest).filter(
            ReviewRequest.created_at.between(start_dt, end_dt)
        )
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            review_query = review_query.join(Document).filter(
                Document.tenant_id == self.tenant_ctx.tenant_id
            )

        total_reviews = review_query.count()
        approved = review_query.filter(ReviewRequest.status == ReviewStatus.APPROVED).count()
        approval_rate = (approved / total_reviews * 100) if total_reviews > 0 else 0.0

        status_query = (
            self.db.query(ReviewRequest.status, func.count(ReviewRequest.id))
            .filter(ReviewRequest.created_at.between(start_dt, end_dt))
            .group_by(ReviewRequest.status)
        )
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            status_query = status_query.join(Document).filter(
                Document.tenant_id == self.tenant_ctx.tenant_id
            )
        reviews_by_status = {
            status.value if status else "unknown": count for status, count in status_query.all()
        }

        completed_reviews = review_query.filter(ReviewRequest.reviewed_at.isnot(None)).all()
        turnaround_hours = None
        if completed_reviews:
            total_hours = sum(
                (review.reviewed_at - review.created_at).total_seconds() / 3600
                for review in completed_reviews
                if review.reviewed_at and review.created_at
            )
            turnaround_hours = total_hours / len(completed_reviews)

        total_docs = self.db.query(Document).filter(Document.created_at.between(start_dt, end_dt))
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            total_docs = total_docs.filter(Document.tenant_id == self.tenant_ctx.tenant_id)

        total_versions = self.db.query(Version).filter(
            Version.is_published.is_(True),
            Version.published_at.isnot(None),
            Version.published_at.between(start_dt, end_dt),
        )
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            total_versions = total_versions.join(Document).filter(
                Document.tenant_id == self.tenant_ctx.tenant_id
            )

        total_comments = self.db.query(Comment).filter(Comment.created_at.between(start_dt, end_dt))
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            total_comments = total_comments.join(Document).filter(
                Document.tenant_id == self.tenant_ctx.tenant_id
            )

        return {
            "period_start": date_from,
            "period_end": date_to,
            "granularity": granularity,
            "documents_created_over_time": [d.model_dump() for d in docs_over_time],
            "versions_published_over_time": [v.model_dump() for v in versions_over_time],
            "comments_over_time": [c.model_dump() for c in comments_over_time],
            "avg_review_turnaround_hours": round(turnaround_hours, 2) if turnaround_hours else None,
            "approval_rate": round(approval_rate, 2),
            "reviews_by_status": reviews_by_status,
            "total_documents_created": total_docs.count(),
            "total_versions_published": total_versions.count(),
            "total_comments": total_comments.count(),
        }
