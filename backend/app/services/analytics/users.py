"""User analytics module."""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, Optional

from sqlalchemy import func

from app.models import AuditLog, User
from app.schemas.analytics import TimeGranularity, TimeSeriesPoint, UserActivityItem


class AnalyticsUsersMixin:
    """User and activity analytics for admin reporting."""

    def get_user_analytics(
        self,
        date_from: date,
        date_to: date,
        granularity: Optional[TimeGranularity] = None,
    ) -> Dict:
        if not granularity:
            granularity = self._auto_granularity(date_from, date_to)

        start_dt = datetime.combine(date_from, datetime.min.time())
        end_dt = datetime.combine(date_to, datetime.max.time())

        user_query = self.db.query(User)
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            user_query = user_query.filter(User.tenant_id == self.tenant_ctx.tenant_id)

        total_users = user_query.count()
        active_users = user_query.filter(User.is_active.is_(True)).count()
        inactive_users = total_users - active_users

        role_query = self.db.query(User.role, func.count(User.id)).group_by(User.role)
        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            role_query = role_query.filter(User.tenant_id == self.tenant_ctx.tenant_id)
        users_by_role = {
            role.value if role else "unknown": count for role, count in role_query.all()
        }

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
