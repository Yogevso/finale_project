"""Announcement banner API — admin manages, all users read active banners."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.permissions import require_manager
from app.models import Announcement, User

router = APIRouter(prefix="/announcements", tags=["Announcements"])


class AnnouncementCreate(BaseModel):
    message: str
    type: str = "info"
    expires_at: Optional[str] = None


class AnnouncementUpdate(BaseModel):
    message: Optional[str] = None
    type: Optional[str] = None
    active: Optional[bool] = None
    expires_at: Optional[str] = None


@router.get("")
async def list_announcements(
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    """List announcements. By default returns only active, non-expired ones."""
    query = db.query(Announcement)
    if active_only:
        now = datetime.utcnow()
        query = query.filter(
            Announcement.active.is_(True),
        ).filter(
            (Announcement.expires_at.is_(None)) | (Announcement.expires_at > now)
        )
    items = query.order_by(Announcement.created_at.desc()).all()
    return [
        {
            "id": a.id,
            "message": a.message,
            "type": a.type,
            "active": a.active,
            "created_at": a.created_at.isoformat(),
            "expires_at": a.expires_at.isoformat() if a.expires_at else None,
        }
        for a in items
    ]


@router.post("", dependencies=[Depends(require_manager)])
async def create_announcement(
    body: AnnouncementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    expires = datetime.fromisoformat(body.expires_at) if body.expires_at else None
    ann = Announcement(
        message=body.message,
        type=body.type,
        created_by=current_user.id,
        expires_at=expires,
    )
    db.add(ann)
    db.commit()
    db.refresh(ann)
    return {"id": ann.id, "message": ann.message}


@router.put("/{ann_id}", dependencies=[Depends(require_manager)])
async def update_announcement(
    ann_id: int,
    body: AnnouncementUpdate,
    db: Session = Depends(get_db),
):
    ann = db.query(Announcement).filter(Announcement.id == ann_id).first()
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")
    data = body.model_dump(exclude_unset=True)
    if "expires_at" in data:
        data["expires_at"] = datetime.fromisoformat(data["expires_at"]) if data["expires_at"] else None
    for field, value in data.items():
        setattr(ann, field, value)
    db.commit()
    return {"id": ann.id, "message": ann.message}


@router.delete("/{ann_id}", dependencies=[Depends(require_manager)])
async def delete_announcement(
    ann_id: int,
    db: Session = Depends(get_db),
):
    ann = db.query(Announcement).filter(Announcement.id == ann_id).first()
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")
    db.delete(ann)
    db.commit()
    return {"deleted": True}
