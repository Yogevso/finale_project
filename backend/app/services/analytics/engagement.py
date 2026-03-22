"""Engagement analytics module."""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional

from sqlalchemy import func, or_

from app.models import ActionType, AuditLog, Document, ReadingProgress
from app.schemas.analytics import DocumentStats, TimeGranularity, TimeSeriesPoint


class AnalyticsEngagementMixin:
    """Document engagement analytics and top-doc reports."""

    def get_engagement(
        self,
        date_from: date,
        date_to: date,
        granularity: Optional[TimeGranularity] = None,
    ) -> Dict:
        if not granularity:
            granularity = self._auto_granularity(date_from, date_to)

        start_dt = datetime.combine(date_from, datetime.min.time())
        end_dt = datetime.combine(date_to, datetime.max.time())

        tenant_doc_ids = None
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            tenant_doc_ids = [
                row[0]
                for row in self.db.query(Document.id)
                .filter(Document.tenant_id == self.tenant_ctx.tenant_id)
                .all()
            ]

        def apply_tenant_filter(query):
            if tenant_doc_ids is not None:
                return query.filter(
                    or_(
                        AuditLog.document_id.in_(tenant_doc_ids),
                        AuditLog.document_id.is_(None),
                    )
                )
            return query

        date_trunc = self._get_date_trunc(granularity, AuditLog.created_at)
        views_query = (
            self.analytics_db.query(date_trunc.label("date"), func.count(AuditLog.id).label("value"))
            .filter(
                AuditLog.action == ActionType.VIEW, AuditLog.created_at.between(start_dt, end_dt)
            )
            .group_by(date_trunc)
            .order_by(date_trunc)
        )
        views_query = apply_tenant_filter(views_query)
        views_over_time = [
            TimeSeriesPoint(date=str(row.date), value=row.value) for row in views_query.all()
        ]

        downloads_query = (
            self.analytics_db.query(date_trunc.label("date"), func.count(AuditLog.id).label("value"))
            .filter(
                AuditLog.action == ActionType.DOWNLOAD,
                AuditLog.created_at.between(start_dt, end_dt),
            )
            .group_by(date_trunc)
            .order_by(date_trunc)
        )
        downloads_query = apply_tenant_filter(downloads_query)
        downloads_over_time = [
            TimeSeriesPoint(date=str(row.date), value=row.value) for row in downloads_query.all()
        ]

        visitors_query = self.analytics_db.query(func.count(func.distinct(AuditLog.user_id))).filter(
            AuditLog.action == ActionType.VIEW, AuditLog.created_at.between(start_dt, end_dt)
        )
        visitors_query = apply_tenant_filter(visitors_query)
        unique_visitors = visitors_query.scalar() or 0

        progress_query = self.db.query(ReadingProgress)
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            progress_query = progress_query.join(Document).filter(
                Document.tenant_id == self.tenant_ctx.tenant_id
            )

        avg_progress = self.db.query(func.avg(ReadingProgress.progress_percent))
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            avg_progress = avg_progress.join(Document).filter(
                Document.tenant_id == self.tenant_ctx.tenant_id
            )
        avg_reading_progress = avg_progress.scalar() or 0.0

        total_progress = progress_query.count()
        completed = progress_query.filter(ReadingProgress.progress_percent >= 100).count()
        completion_rate = (completed / total_progress * 100) if total_progress > 0 else 0.0

        total_time_spent_minutes = 0

        return {
            "period_start": date_from,
            "period_end": date_to,
            "granularity": granularity,
            "views_over_time": [v.model_dump() for v in views_over_time],
            "downloads_over_time": [d.model_dump() for d in downloads_over_time],
            "unique_visitors": unique_visitors,
            "avg_reading_progress": round(avg_reading_progress, 2),
            "completion_rate": round(completion_rate, 2),
            "total_time_spent_minutes": total_time_spent_minutes,
        }

    def get_top_documents(
        self,
        date_from: date,
        date_to: date,
        limit: int = 10,
    ) -> Dict:
        start_dt = datetime.combine(date_from, datetime.min.time())
        end_dt = datetime.combine(date_to, datetime.max.time())

        tenant_doc_ids = None
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            tenant_doc_ids = [
                row[0]
                for row in self.db.query(Document.id)
                .filter(Document.tenant_id == self.tenant_ctx.tenant_id)
                .all()
            ]

        def get_top_by_action(action: ActionType) -> List[DocumentStats]:
            query = self.analytics_db.query(
                AuditLog.document_id, func.count(AuditLog.id).label("count")
            ).filter(
                AuditLog.action == action,
                AuditLog.created_at.between(start_dt, end_dt),
                AuditLog.document_id.isnot(None),
            )

            if tenant_doc_ids is not None:
                query = query.filter(AuditLog.document_id.in_(tenant_doc_ids))

            query = (
                query.group_by(AuditLog.document_id)
                .order_by(func.count(AuditLog.id).desc())
                .limit(limit)
            )

            results = []
            for row in query.all():
                doc = self.db.query(Document).filter(Document.id == row.document_id).first()
                if doc:
                    results.append(
                        DocumentStats(
                            document_id=doc.id,
                            document_number=doc.document_number,
                            title=doc.title,
                            view_count=row.count if action == ActionType.VIEW else 0,
                            download_count=row.count if action == ActionType.DOWNLOAD else 0,
                        )
                    )
            return results

        return {
            "by_views": [d.model_dump() for d in get_top_by_action(ActionType.VIEW)],
            "by_downloads": [d.model_dump() for d in get_top_by_action(ActionType.DOWNLOAD)],
        }
