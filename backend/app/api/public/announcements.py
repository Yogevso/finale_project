"""Public announcements endpoint — no authentication required."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Announcement

router = APIRouter(tags=["Public Announcements"])


@router.get("/announcements")
async def get_active_announcements(db: Session = Depends(get_db)):
    """Return active, non-expired announcements for public display."""
    now = datetime.utcnow()
    items = (
        db.query(Announcement)
        .filter(
            Announcement.active.is_(True),
            (Announcement.expires_at.is_(None)) | (Announcement.expires_at > now),
        )
        .order_by(Announcement.created_at.desc())
        .all()
    )
    return [
        {
            "id": a.id,
            "message": a.message,
            "type": a.type,
            "created_at": a.created_at.isoformat(),
        }
        for a in items
    ]
