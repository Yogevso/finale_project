"""Analytics Service - Business logic for analytics aggregations"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.dependencies.tenant import TenantContext
from app.models import (
    ActionType,
    AuditLog,
    Comment,
    Document,
    Feedback,
    FeedbackStatus,
    ReadingProgress,
    ReviewRequest,
    ReviewStatus,
    Tenant,
    User,
    Version,
)
from app.schemas.analytics import (
    CategoryCount,
    DocumentStats,
    RecentActivity,
    TenantMetrics,
    TimeGranularity,
    TimeSeriesPoint,
    UserActivityItem,
)
from app.services.base_service import SessionService


class AnalyticsService(SessionService):
    """Service for computing analytics metrics with tenant isolation"""

    def __init__(self, db: Session, tenant_ctx: Optional[TenantContext] = None):
        super().__init__(db)
        self.tenant_ctx = tenant_ctx

    def _get_tenant_filter(self, model):
        """Get tenant filter for a model if applicable"""
        if not self.tenant_ctx or self.tenant_ctx.is_system_admin:
            return True  # No filter for system admin
        if hasattr(model, "tenant_id"):
            return model.tenant_id == self.tenant_ctx.tenant_id
        return True

    def _get_date_trunc(self, granularity: TimeGranularity, column):
        """Get date truncation function based on granularity (SQLite compatible)"""
        if granularity == TimeGranularity.DAILY:
            return func.date(column)
        elif granularity == TimeGranularity.WEEKLY:
            return func.strftime("%Y-W%W", column)
        elif granularity == TimeGranularity.MONTHLY:
            return func.strftime("%Y-%m", column)
        return func.date(column)

    def _auto_granularity(self, date_from: date, date_to: date) -> TimeGranularity:
        """Auto-detect granularity based on date range"""
        days = (date_to - date_from).days
        if days <= 30:
            return TimeGranularity.DAILY
        elif days <= 180:
            return TimeGranularity.WEEKLY
        else:
            return TimeGranularity.MONTHLY

    # ========================================================================
    # Overview Analytics
    # ========================================================================

    def get_overview(self, date_from: date, date_to: date) -> Dict:
        """Get overview analytics"""
        # Convert dates to datetime for queries
        start_dt = datetime.combine(date_from, datetime.min.time())
        end_dt = datetime.combine(date_to, datetime.max.time())
        today_start = datetime.combine(date.today(), datetime.min.time())
        week_ago = today_start - timedelta(days=7)

        # Total documents
        doc_query = self.db.query(Document)
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            doc_query = doc_query.filter(Document.tenant_id == self.tenant_ctx.tenant_id)
        total_documents = doc_query.count()

        # Total users
        user_query = self.db.query(User)
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            user_query = user_query.filter(User.tenant_id == self.tenant_ctx.tenant_id)
        total_users = user_query.count()

        # Views and downloads in period
        audit_query = self.db.query(AuditLog).filter(AuditLog.created_at.between(start_dt, end_dt))
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            # Filter by documents in tenant
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

        # Documents by status
        status_query = self.db.query(Document.status, func.count(Document.id)).group_by(
            Document.status
        )
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            status_query = status_query.filter(Document.tenant_id == self.tenant_ctx.tenant_id)
        documents_by_status = {
            status.value if status else "unknown": count for status, count in status_query.all()
        }

        # Documents by category
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

        # Pending reviews
        review_query = self.db.query(ReviewRequest).filter(
            ReviewRequest.status == ReviewStatus.PENDING
        )
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            # Filter by documents in tenant
            review_query = review_query.join(Document).filter(
                Document.tenant_id == self.tenant_ctx.tenant_id
            )
        pending_reviews = review_query.count()

        # Views today
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

        # New docs this week
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
        """Get recent activity feed"""
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

    # ========================================================================
    # Engagement Analytics
    # ========================================================================

    def get_engagement(
        self,
        date_from: date,
        date_to: date,
        granularity: Optional[TimeGranularity] = None,
    ) -> Dict:
        """Get engagement analytics"""
        if not granularity:
            granularity = self._auto_granularity(date_from, date_to)

        start_dt = datetime.combine(date_from, datetime.min.time())
        end_dt = datetime.combine(date_to, datetime.max.time())

        # Get tenant document IDs for filtering
        tenant_doc_subquery = None
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            tenant_doc_subquery = (
                self.db.query(Document.id)
                .filter(Document.tenant_id == self.tenant_ctx.tenant_id)
                .subquery()
            )

        def apply_tenant_filter(query):
            if tenant_doc_subquery is not None:
                return query.filter(
                    or_(
                        AuditLog.document_id.in_(tenant_doc_subquery),
                        AuditLog.document_id.is_(None),
                    )
                )
            return query

        # Views over time
        date_trunc = self._get_date_trunc(granularity, AuditLog.created_at)
        views_query = (
            self.db.query(date_trunc.label("date"), func.count(AuditLog.id).label("value"))
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

        # Downloads over time
        downloads_query = (
            self.db.query(date_trunc.label("date"), func.count(AuditLog.id).label("value"))
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

        # Unique visitors
        visitors_query = self.db.query(func.count(func.distinct(AuditLog.user_id))).filter(
            AuditLog.action == ActionType.VIEW, AuditLog.created_at.between(start_dt, end_dt)
        )
        visitors_query = apply_tenant_filter(visitors_query)
        unique_visitors = visitors_query.scalar() or 0

        # Reading progress metrics
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

        # Completion rate (100% progress)
        total_progress = progress_query.count()
        completed = progress_query.filter(ReadingProgress.progress_percent >= 100).count()
        completion_rate = (completed / total_progress * 100) if total_progress > 0 else 0.0

        # Total time spent (estimate based on last_read_at and created_at)
        # Since there's no time_spent_seconds column, we'll return 0
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
        """Get top documents by views and downloads"""
        start_dt = datetime.combine(date_from, datetime.min.time())
        end_dt = datetime.combine(date_to, datetime.max.time())

        tenant_doc_subquery = None
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            tenant_doc_subquery = (
                self.db.query(Document.id)
                .filter(Document.tenant_id == self.tenant_ctx.tenant_id)
                .subquery()
            )

        def get_top_by_action(action: ActionType) -> List[DocumentStats]:
            query = self.db.query(
                AuditLog.document_id, func.count(AuditLog.id).label("count")
            ).filter(
                AuditLog.action == action,
                AuditLog.created_at.between(start_dt, end_dt),
                AuditLog.document_id.isnot(None),
            )

            if tenant_doc_subquery is not None:
                query = query.filter(AuditLog.document_id.in_(tenant_doc_subquery))

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

    # ========================================================================
    # User Analytics
    # ========================================================================

    def get_user_analytics(
        self,
        date_from: date,
        date_to: date,
        granularity: Optional[TimeGranularity] = None,
    ) -> Dict:
        """Get user analytics (admin only)"""
        if not granularity:
            granularity = self._auto_granularity(date_from, date_to)

        start_dt = datetime.combine(date_from, datetime.min.time())
        end_dt = datetime.combine(date_to, datetime.max.time())

        # Base user query
        user_query = self.db.query(User)
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            user_query = user_query.filter(User.tenant_id == self.tenant_ctx.tenant_id)

        total_users = user_query.count()
        active_users = user_query.filter(User.is_active.is_(True)).count()
        inactive_users = total_users - active_users

        # Users by role
        role_query = self.db.query(User.role, func.count(User.id)).group_by(User.role)
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            role_query = role_query.filter(User.tenant_id == self.tenant_ctx.tenant_id)
        users_by_role = {
            role.value if role else "unknown": count for role, count in role_query.all()
        }

        # New users over time
        date_trunc = self._get_date_trunc(granularity, User.created_at)
        new_users_query = (
            self.db.query(date_trunc.label("date"), func.count(User.id).label("value"))
            .filter(User.created_at.between(start_dt, end_dt))
            .group_by(date_trunc)
            .order_by(date_trunc)
        )
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            new_users_query = new_users_query.filter(User.tenant_id == self.tenant_ctx.tenant_id)
        new_users_over_time = [
            TimeSeriesPoint(date=str(row.date), value=row.value) for row in new_users_query.all()
        ]

        # Most active users
        activity_query = (
            self.db.query(
                User.id.label("user_id"),
                User.username.label("username"),
                User.full_name.label("full_name"),
                User.role.label("role"),
                func.count(AuditLog.id).label("count"),
                func.max(AuditLog.created_at).label("last_active"),
            )
            .join(User, User.id == AuditLog.user_id)
            .filter(AuditLog.created_at.between(start_dt, end_dt))
        )
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            activity_query = activity_query.filter(User.tenant_id == self.tenant_ctx.tenant_id)
        activity_query = (
            activity_query.group_by(User.id, User.username, User.full_name, User.role)
            .order_by(
                func.count(AuditLog.id).desc(),
                func.max(AuditLog.created_at).desc(),
                User.id.asc(),
            )
            .limit(10)
        )

        most_active = [
            UserActivityItem(
                user_id=row.user_id,
                username=row.username,
                full_name=row.full_name,
                role=row.role.value if row.role else "unknown",
                action_count=row.count,
                last_active=row.last_active.isoformat() if row.last_active else None,
            )
            for row in activity_query.all()
        ]

        return {
            "period_start": date_from,
            "period_end": date_to,
            "granularity": granularity,
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": inactive_users,
            "users_by_role": users_by_role,
            "new_users_over_time": [u.model_dump() for u in new_users_over_time],
            "most_active_users": [u.model_dump() for u in most_active],
        }

    # ========================================================================
    # Content Production Analytics
    # ========================================================================

    def get_content_analytics(
        self,
        date_from: date,
        date_to: date,
        granularity: Optional[TimeGranularity] = None,
    ) -> Dict:
        """Get content production analytics"""
        if not granularity:
            granularity = self._auto_granularity(date_from, date_to)

        start_dt = datetime.combine(date_from, datetime.min.time())
        end_dt = datetime.combine(date_to, datetime.max.time())

        # Documents created over time
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

        # Versions published over time (publish date, not version creation date)
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

        # Comments over time
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

        # Review metrics
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

        # Reviews by status
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

        # Average review turnaround (for completed reviews)
        completed_reviews = review_query.filter(ReviewRequest.reviewed_at.isnot(None)).all()
        turnaround_hours = None
        if completed_reviews:
            total_hours = sum(
                (r.reviewed_at - r.created_at).total_seconds() / 3600
                for r in completed_reviews
                if r.reviewed_at and r.created_at
            )
            turnaround_hours = total_hours / len(completed_reviews)

        # Totals
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

    # ========================================================================
    # Feedback Analytics
    # ========================================================================

    def get_feedback_analytics(
        self,
        date_from: date,
        date_to: date,
        granularity: Optional[TimeGranularity] = None,
    ) -> Dict:
        """Get feedback analytics"""
        if not granularity:
            granularity = self._auto_granularity(date_from, date_to)

        start_dt = datetime.combine(date_from, datetime.min.time())
        end_dt = datetime.combine(date_to, datetime.max.time())

        # Base query
        base_query = self.db.query(Feedback).filter(Feedback.created_at.between(start_dt, end_dt))
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            base_query = base_query.join(Document).filter(
                Document.tenant_id == self.tenant_ctx.tenant_id
            )

        total_feedback = base_query.count()
        pending = base_query.filter(Feedback.status == FeedbackStatus.PENDING).count()
        responded = base_query.filter(Feedback.status == FeedbackStatus.RESPONDED).count()

        # Feedback by type
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

        # Feedback by status
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

        # Feedback over time
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

        # Average response time
        responded_feedback = base_query.filter(Feedback.responded_at.isnot(None)).all()
        avg_response_hours = None
        if responded_feedback:
            total_hours = sum(
                (f.responded_at - f.created_at).total_seconds() / 3600
                for f in responded_feedback
                if f.responded_at and f.created_at
            )
            avg_response_hours = total_hours / len(responded_feedback)

        # Helpfulness rate
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
            "feedback_over_time": [f.model_dump() for f in feedback_over_time],
            "avg_response_time_hours": round(avg_response_hours, 2) if avg_response_hours else None,
            "helpfulness_rate": round(helpfulness_rate, 2),
        }

    # ========================================================================
    # Tenant Analytics (System Admin Only)
    # ========================================================================

    def get_tenant_analytics(self, date_from: date, date_to: date) -> Dict:
        """Get cross-tenant analytics (system admin only)"""
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        tenants = self.db.query(Tenant).all()
        total_tenants = len(tenants)
        active_tenants = sum(1 for t in tenants if t.is_active)

        tenant_metrics = []
        for tenant in tenants:
            # Document count
            doc_count = self.db.query(Document).filter(Document.tenant_id == tenant.id).count()

            # User count
            user_count = self.db.query(User).filter(User.tenant_id == tenant.id).count()

            # Active users (had activity in last 30 days)
            active_user_ids = (
                self.db.query(func.distinct(AuditLog.user_id))
                .join(User)
                .filter(User.tenant_id == tenant.id, AuditLog.created_at >= thirty_days_ago)
                .all()
            )
            active_users_30d = len(active_user_ids)

            # Views in last 30 days
            tenant_doc_ids = (
                self.db.query(Document.id).filter(Document.tenant_id == tenant.id).subquery()
            )
            views_30d = (
                self.db.query(AuditLog)
                .filter(
                    AuditLog.action == ActionType.VIEW,
                    AuditLog.created_at >= thirty_days_ago,
                    AuditLog.document_id.in_(tenant_doc_ids),
                )
                .count()
            )

            # Health score (simple formula: activity + content)
            health_score = min(
                100,
                (
                    (active_users_30d / max(user_count, 1) * 40)  # 40% weight: active user ratio
                    + (min(views_30d, 100) / 100 * 30)  # 30% weight: views (capped at 100)
                    + (min(doc_count, 50) / 50 * 30)  # 30% weight: documents (capped at 50)
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
            "tenants": [t.model_dump() for t in tenant_metrics],
        }
