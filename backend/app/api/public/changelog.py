"""AF-006: Public changelog endpoint — moved out of management router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ChangelogEntry

router = APIRouter(prefix="/public", tags=["Public"])


@router.get("/changelog")
async def list_public_changelog(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List published changelog entries. No authentication required."""
    query = db.query(ChangelogEntry).filter(ChangelogEntry.published.is_(True))
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
