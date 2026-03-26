"""Notifications API Routes"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_chat_db
from app.models import Notification, NotificationType, User
from app.security import get_current_active_user

router = APIRouter()


def _serialize_notification_type(raw_type: NotificationType | str) -> str:
    """Return canonical snake_case notification type values for API responses."""
    if isinstance(raw_type, NotificationType):
        return raw_type.value

    if isinstance(raw_type, str):
        try:
            return NotificationType(raw_type).value
        except ValueError:
            pass

        try:
            return NotificationType[raw_type].value
        except KeyError:
            pass

        return raw_type.lower()

    return str(raw_type)


# Schemas
class NotificationResponse(BaseModel):
    """Notification response schema"""

    id: int
    type: str
    title: str
    message: Optional[str] = None
    link: Optional[str] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """List of notifications with counts"""

    items: List[NotificationResponse]
    total: int
    unread_count: int


class NotificationMarkRead(BaseModel):
    """Mark notifications as read"""

    notification_ids: Optional[List[int]] = None  # None = mark all


# Routes
@router.get("/notifications", response_model=NotificationListResponse)
def get_notifications(
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_chat_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get notifications for current user"""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)

    if unread_only:
        query = query.filter(Notification.is_read.is_(False))

    total = query.count()
    unread_count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read.is_(False))
        .count()
    )

    items = query.order_by(Notification.created_at.desc()).limit(limit).all()

    return NotificationListResponse(
        items=[
            NotificationResponse(
                id=n.id,
                type=_serialize_notification_type(n.type),
                title=n.title,
                message=n.message,
                link=n.link,
                is_read=n.is_read,
                read_at=n.read_at,
                created_at=n.created_at,
            )
            for n in items
        ],
        total=total,
        unread_count=unread_count,
    )


@router.get("/notifications/count")
def get_notification_count(
    db: Session = Depends(get_chat_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get unread notification count for current user"""
    unread_count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read.is_(False))
        .count()
    )

    return {"unread_count": unread_count}


@router.post("/notifications/read")
def mark_notifications_read(
    data: NotificationMarkRead,
    db: Session = Depends(get_chat_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mark notifications as read"""
    query = db.query(Notification).filter(
        Notification.user_id == current_user.id, Notification.is_read.is_(False)
    )

    if data.notification_ids:
        query = query.filter(Notification.id.in_(data.notification_ids))

    now = datetime.utcnow()
    updated = query.update(
        {Notification.is_read: True, Notification.read_at: now}, synchronize_session=False
    )
    db.commit()

    return {"message": f"Marked {updated} notifications as read"}


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_chat_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mark a single notification as read"""
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        db.commit()

    return {"message": "Notification marked as read"}


@router.post("/notifications/{notification_id}/unread")
def mark_notification_unread(
    notification_id: int,
    db: Session = Depends(get_chat_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mark a single notification as unread"""
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    if notification.is_read:
        notification.is_read = False
        notification.read_at = None
        db.commit()

    return {"message": "Notification marked as unread"}


@router.delete("/notifications/{notification_id}")
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_chat_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a notification"""
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    db.delete(notification)
    db.commit()

    return {"message": "Notification deleted"}


@router.delete("/notifications")
def delete_all_notifications(
    read_only: bool = True,
    db: Session = Depends(get_chat_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete notifications (by default only read ones)"""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)

    if read_only:
        query = query.filter(Notification.is_read.is_(True))

    deleted = query.delete(synchronize_session=False)
    db.commit()

    return {"message": f"Deleted {deleted} notifications"}
