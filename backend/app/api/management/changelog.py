"""Changelog API — management CRUD for release notes (auth required).

AF-006/007: Public read access moved to ``app.api.public.changelog``.
This router is management-only; all endpoints require manager auth.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.permissions import require_manager
from app.models import ChangelogEntry, User

router = APIRouter(prefix="/changelog", tags=["Changelog"])


class ChangelogCreate(BaseModel):
    title: str
    content: str
    version_tag: Optional[str] = None
    category: Optional[str] = None
    published: bool = False


class ChangelogUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    version_tag: Optional[str] = None
    category: Optional[str] = None
    published: Optional[bool] = None


@router.get("", dependencies=[Depends(require_manager)])
async def list_changelog(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    published_only: bool = False,
    db: Session = Depends(get_db),
):
    """List changelog entries (management — includes unpublished drafts)."""
    query = db.query(ChangelogEntry)
    if published_only:
        query = query.filter(ChangelogEntry.published.is_(True))
    total = query.count()
    items = (
        query.order_by(ChangelogEntry.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "items": [
            {
                "id": e.id,
                "title": e.title,
                "content": e.content,
                "version_tag": e.version_tag,
                "category": e.category,
                "published": e.published,
                "created_at": e.created_at.isoformat(),
                "updated_at": e.updated_at.isoformat(),
            }
            for e in items
        ],
    }


@router.post("", dependencies=[Depends(require_manager)])
async def create_changelog(
    body: ChangelogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    entry = ChangelogEntry(
        title=body.title,
        content=body.content,
        version_tag=body.version_tag,
        category=body.category,
        published=body.published,
        created_by=current_user.id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"id": entry.id, "title": entry.title}


@router.put("/{entry_id}", dependencies=[Depends(require_manager)])
async def update_changelog(
    entry_id: int,
    body: ChangelogUpdate,
    db: Session = Depends(get_db),
):
    entry = db.query(ChangelogEntry).filter(ChangelogEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Changelog entry not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    entry.updated_at = datetime.utcnow()
    db.commit()
    return {"id": entry.id, "title": entry.title}


@router.delete("/{entry_id}", dependencies=[Depends(require_manager)])
async def delete_changelog(
    entry_id: int,
    db: Session = Depends(get_db),
):
    entry = db.query(ChangelogEntry).filter(ChangelogEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Changelog entry not found")
    db.delete(entry)
    db.commit()
    return {"deleted": True}
