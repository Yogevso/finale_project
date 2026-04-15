"""Public API for notifications bounded context."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Notification


@dataclass
class NotificationsContextAPI:
    """Stable API for notification reads/writes."""

    db: Session

    def list_user_notifications(self, user_id: int) -> list[Notification]:
        return (
            self.db.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .all()
        )
