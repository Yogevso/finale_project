"""Overview/recent-activity analytics module."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import func, or_

from app.models import (
    ActionType,
    AudienceEventType,
    AuditLog,
    Document,
    DocumentStatus,
    DocumentVisibility,
    ReviewRequest,
    ReviewStatus,
    Tenant,
    User,
)
from app.schemas.analytics import AssignmentChurnItem, CategoryCount, RecentActivity


class AnalyticsOverviewMixin:
    """Overview and activity feed analytics."""

    def _tenant_scoped_audit_query(self, *, start_dt: datetime, end_dt: datetime):
        query = self.analytics_db.query(AuditLog).filter(
            AuditLog.created_at.between(start_dt, end_dt)
        )
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            tenant_doc_ids = [
                row[0]
                for row in self.db.query(Document.id)
                .filter(Document.tenant_id == self.tenant_ctx.tenant_id)
                .all()
            ]
            query = query.filter(
                or_(AuditLog.document_id.in_(tenant_doc_ids), AuditLog.document_id.is_(None))
            )
        return query

    @staticmethod
    def _safe_json_loads(raw_value: str | None) -> dict[str, Any]:
        if not raw_value:
            return {}
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def get_overview(self, date_from: date, date_to: date) -> Dict:
        start_dt = datetime.combine(date_from, datetime.min.time())
        end_dt = datetime.combine(date_to, datetime.max.time())
        today_start = datetime.combine(date.today(), datetime.min.time())
        week_ago = today_start - timedelta(days=7)
        ninety_days_ago = today_start - timedelta(days=90)
        thirty_days_ago = today_start - timedelta(days=30)

        doc_query = self.db.query(Document)
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            doc_query = doc_query.filter(Document.tenant_id == self.tenant_ctx.tenant_id)
        total_documents = doc_query.count()

        user_query = self.db.query(User)
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            user_query = user_query.filter(User.tenant_id == self.tenant_ctx.tenant_id)
        total_users = user_query.count()

        audit_query = self._tenant_scoped_audit_query(start_dt=start_dt, end_dt=end_dt)

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

        audience_query = self.db.query(Document.visibility, func.count(Document.id)).group_by(
            Document.visibility
        )
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            audience_query = audience_query.filter(Document.tenant_id == self.tenant_ctx.tenant_id)
        by_audience_type = {
            DocumentVisibility.INTERNAL.value: 0,
            DocumentVisibility.COMPANY.value: 0,
            DocumentVisibility.PUBLIC.value: 0,
        }
        for visibility, count in audience_query.all():
            key = visibility.value if visibility else "internal"
            by_audience_type[key] = int(count)

        review_query = self.db.query(ReviewRequest).filter(
            ReviewRequest.status == ReviewStatus.PENDING
        )
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            review_query = review_query.join(Document).filter(
                Document.tenant_id == self.tenant_ctx.tenant_id
            )
        pending_reviews = review_query.count()

        views_today_query = self.analytics_db.query(AuditLog).filter(
            AuditLog.action == ActionType.VIEW, AuditLog.created_at >= today_start
        )
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            _tenant_doc_ids = [
                row[0]
                for row in self.db.query(Document.id)
                .filter(Document.tenant_id == self.tenant_ctx.tenant_id)
                .all()
            ]
            views_today_query = views_today_query.filter(
                or_(
                    AuditLog.document_id.in_(_tenant_doc_ids),
                    AuditLog.document_id.is_(None),
                )
            )
        views_today = views_today_query.count()

        new_docs_query = self.db.query(Document).filter(Document.created_at >= week_ago)
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            new_docs_query = new_docs_query.filter(Document.tenant_id == self.tenant_ctx.tenant_id)
        new_docs_this_week = new_docs_query.count()

        exposure_risk_count = 0
        visibility_logs = self._tenant_scoped_audit_query(
            start_dt=thirty_days_ago,
            end_dt=end_dt,
        ).filter(AuditLog.audience_event_type == AudienceEventType.VISIBILITY_CHANGED)
        for row in visibility_logs.all():
            details = self._safe_json_loads(row.details)
            from_visibility = str(details.get("from_visibility") or "").lower()
            to_visibility = str(details.get("to_visibility") or "").lower()
            if (
                from_visibility == DocumentVisibility.INTERNAL.value
                and to_visibility == DocumentVisibility.PUBLIC.value
            ):
                exposure_risk_count += 1

        churn_query = self._tenant_scoped_audit_query(
            start_dt=ninety_days_ago,
            end_dt=end_dt,
        ).filter(AuditLog.assignment_diff.isnot(None))
        churn_counter: dict[int, int] = {}
        for row in churn_query.all():
            if row.document_id is None:
                continue
            churn_counter[row.document_id] = churn_counter.get(row.document_id, 0) + 1
        assignment_churn_90d = [
            AssignmentChurnItem(document_id=document_id, churn_count=count).model_dump()
            for document_id, count in sorted(
                churn_counter.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ]

        return {
            "period_start": date_from,
            "period_end": date_to,
            "total_documents": total_documents,
            "total_users": total_users,
            "total_views": total_views,
            "total_downloads": total_downloads,
            "documents_by_status": documents_by_status,
            "documents_by_category": [c.model_dump() for c in documents_by_category],
            "by_audience_type": by_audience_type,
            "pending_reviews": pending_reviews,
            "views_today": views_today,
            "new_docs_this_week": new_docs_this_week,
            "exposure_risk_transitions_30d": exposure_risk_count,
            "assignment_churn_90d": assignment_churn_90d,
        }

    def get_recent_activity(self, limit: int = 10) -> List[RecentActivity]:
        query = self.analytics_db.query(AuditLog)

        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            tenant_doc_ids = [
                row[0]
                for row in self.db.query(Document.id)
                .filter(Document.tenant_id == self.tenant_ctx.tenant_id)
                .all()
            ]
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

    def get_company_audience_analytics(self, company_id: int) -> dict[str, Any]:
        company = self.db.query(Tenant).filter(Tenant.id == company_id).first()
        if not company:
            return {
                "company_id": company_id,
                "company_name": "Unknown",
                "document_count": 0,
                "active_document_count": 0,
                "company_visible_document_count": 0,
                "view_count_30d": 0,
                "download_count_30d": 0,
                "assignment_churn_90d": 0,
            }

        assigned_docs_query = self.db.query(Document).filter(
            Document.assigned_companies.any(id=company_id)
        )
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            assigned_docs_query = assigned_docs_query.filter(
                Document.tenant_id == self.tenant_ctx.tenant_id
            )

        assigned_documents = assigned_docs_query.all()
        assigned_doc_ids = [doc.id for doc in assigned_documents]

        active_document_count = sum(
            1 for doc in assigned_documents if doc.status == DocumentStatus.ACTIVE
        )
        company_visible_document_count = sum(
            1 for doc in assigned_documents if doc.visibility == DocumentVisibility.COMPANY
        )

        now = datetime.utcnow()
        thirty_days_ago = now - timedelta(days=30)
        ninety_days_ago = now - timedelta(days=90)

        if assigned_doc_ids:
            view_count_30d = (
                self.analytics_db.query(AuditLog)
                .filter(
                    AuditLog.action == ActionType.VIEW,
                    AuditLog.created_at.between(thirty_days_ago, now),
                    AuditLog.document_id.in_(assigned_doc_ids),
                )
                .count()
            )
            download_count_30d = (
                self.analytics_db.query(AuditLog)
                .filter(
                    AuditLog.action == ActionType.DOWNLOAD,
                    AuditLog.created_at.between(thirty_days_ago, now),
                    AuditLog.document_id.in_(assigned_doc_ids),
                )
                .count()
            )
        else:
            view_count_30d = 0
            download_count_30d = 0

        churn_logs = self.analytics_db.query(AuditLog).filter(
            AuditLog.assignment_diff.isnot(None),
            AuditLog.created_at.between(ninety_days_ago, now),
        )
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            tenant_doc_ids = [
                row[0]
                for row in self.db.query(Document.id)
                .filter(Document.tenant_id == self.tenant_ctx.tenant_id)
                .all()
            ]
            churn_logs = churn_logs.filter(AuditLog.document_id.in_(tenant_doc_ids))
        churn_logs = churn_logs.all()
        assignment_churn_90d = 0
        for log in churn_logs:
            payload = self._safe_json_loads(log.assignment_diff)
            touched_ids = set(payload.get("old_company_ids", [])) | set(
                payload.get("new_company_ids", [])
            )
            if company_id in touched_ids:
                assignment_churn_90d += 1

        return {
            "company_id": company_id,
            "company_name": company.name,
            "document_count": len(assigned_documents),
            "active_document_count": active_document_count,
            "company_visible_document_count": company_visible_document_count,
            "view_count_30d": view_count_30d,
            "download_count_30d": download_count_30d,
            "assignment_churn_90d": assignment_churn_90d,
        }

    def export_audit_logs(
        self, *, date_from: date | None, date_to: date | None
    ) -> list[dict[str, Any]]:
        if date_from is None:
            date_from = date.today() - timedelta(days=30)
        if date_to is None:
            date_to = date.today()

        start_dt = datetime.combine(date_from, datetime.min.time())
        end_dt = datetime.combine(date_to, datetime.max.time())
        query = self._tenant_scoped_audit_query(start_dt=start_dt, end_dt=end_dt)
        logs = query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).all()

        user_by_id = {
            user.id: user
            for user in self.db.query(User).filter(
                User.id.in_([log.user_id for log in logs if log.user_id is not None])
            )
        }
        document_by_id = {
            document.id: document
            for document in self.db.query(Document).filter(
                Document.id.in_([log.document_id for log in logs if log.document_id is not None])
            )
        }

        rows: list[dict[str, Any]] = []
        for log in logs:
            user = user_by_id.get(log.user_id) if log.user_id is not None else None
            document = document_by_id.get(log.document_id) if log.document_id is not None else None
            rows.append(
                {
                    "id": log.id,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                    "user_id": log.user_id,
                    "user_email": user.email if user else None,
                    "document_id": log.document_id,
                    "document_title": document.title if document else None,
                    "action": log.action.value if log.action else None,
                    "audience_event_type": (
                        log.audience_event_type.value if log.audience_event_type else None
                    ),
                    "details": log.details,
                    "assignment_diff": log.assignment_diff,
                    "ip_address": log.ip_address,
                    "signature_key_id": log.signature_key_id,
                    "signature": log.signature,
                }
            )
        return rows
