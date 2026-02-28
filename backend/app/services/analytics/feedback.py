"""Feedback analytics module."""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, Optional

from sqlalchemy import func

from app.models import Document, Feedback, FeedbackStatus
from app.schemas.analytics import TimeGranularity, TimeSeriesPoint


class AnalyticsFeedbackMixin:
    """Customer feedback analytics."""

    def get_feedback_analytics(
        self,
        date_from: date,
        date_to: date,
        granularity: Optional[TimeGranularity] = None,
    ) -> Dict:
        if not granularity:
            granularity = self._auto_granularity(date_from, date_to)

        start_dt = datetime.combine(date_from, datetime.min.time())
        end_dt = datetime.combine(date_to, datetime.max.time())

        base_query = self.db.query(Feedback).filter(Feedback.created_at.between(start_dt, end_dt))
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            base_query = base_query.join(Document).filter(
                Document.tenant_id == self.tenant_ctx.tenant_id
            )

        total_feedback = base_query.count()
        pending = base_query.filter(Feedback.status == FeedbackStatus.PENDING).count()
        responded = base_query.filter(Feedback.status == FeedbackStatus.RESPONDED).count()

        type_query = (
            self.db.query(Feedback.feedback_type, func.count(Feedback.id))
            .filter(Feedback.created_at.between(start_dt, end_dt))
            .group_by(Feedback.feedback_type)
        )
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            type_query = type_query.join(Document).filter(
                Document.tenant_id == self.tenant_ctx.tenant_id
            )
        feedback_by_type = {
            ftype.value if ftype else "unknown": count for ftype, count in type_query.all()
        }

        status_query = (
            self.db.query(Feedback.status, func.count(Feedback.id))
            .filter(Feedback.created_at.between(start_dt, end_dt))
            .group_by(Feedback.status)
        )
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            status_query = status_query.join(Document).filter(
                Document.tenant_id == self.tenant_ctx.tenant_id
            )
        feedback_by_status = {
            status.value if status else "unknown": count for status, count in status_query.all()
        }

        date_trunc = self._get_date_trunc(granularity, Feedback.created_at)
        time_query = (
            self.db.query(date_trunc.label("date"), func.count(Feedback.id).label("value"))
            .filter(Feedback.created_at.between(start_dt, end_dt))
            .group_by(date_trunc)
            .order_by(date_trunc)
        )
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            time_query = time_query.join(Document).filter(
                Document.tenant_id == self.tenant_ctx.tenant_id
            )
        feedback_over_time = [
            TimeSeriesPoint(date=str(row.date), value=row.value) for row in time_query.all()
        ]

        responded_feedback = base_query.filter(Feedback.responded_at.isnot(None)).all()
        avg_response_hours = None
        if responded_feedback:
            total_hours = sum(
                (item.responded_at - item.created_at).total_seconds() / 3600
                for item in responded_feedback
                if item.responded_at and item.created_at
            )
            avg_response_hours = total_hours / len(responded_feedback)

        helpful_query = base_query.filter(Feedback.is_helpful.isnot(None))
        total_rated = helpful_query.count()
        helpful_count = helpful_query.filter(Feedback.is_helpful.is_(True)).count()
        helpfulness_rate = (helpful_count / total_rated * 100) if total_rated > 0 else 0.0

        return {
            "period_start": date_from,
            "period_end": date_to,
            "granularity": granularity,
            "total_feedback": total_feedback,
            "pending_feedback": pending,
            "responded_feedback": responded,
            "feedback_by_type": feedback_by_type,
            "feedback_by_status": feedback_by_status,
            "feedback_over_time": [item.model_dump() for item in feedback_over_time],
            "avg_response_time_hours": round(avg_response_hours, 2) if avg_response_hours else None,
            "helpfulness_rate": round(helpfulness_rate, 2),
        }
