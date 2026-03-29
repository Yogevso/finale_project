"""Public platform overview/detail endpoints for viewer portal."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Document, DocumentStatus, DocumentVisibility, Platform, Version
from app.schemas.public import (
    PublicPlatformDocumentRow,
    PublicPlatformDocumentsResponse,
    PublicPlatformLatestRelease,
    PublicPlatformOverviewItem,
    PublicPlatformOverviewResponse,
)

router = APIRouter(prefix="/platforms", tags=["Public"])


def _latest_published_subquery(db: Session):
    return (
        db.query(
            Version.document_id.label("document_id"),
            func.max(Version.published_at).label("published_at"),
            func.max(Version.version_number).label("version_number"),
        )
        .filter(Version.is_published.is_(True))
        .group_by(Version.document_id)
        .subquery()
    )


def _public_platform_documents_query(db: Session):
    latest_published = _latest_published_subquery(db)
    query = (
        db.query(Document, latest_published.c.published_at, latest_published.c.version_number)
        .join(latest_published, Document.id == latest_published.c.document_id)
        .filter(
            Document.visibility == DocumentVisibility.PUBLIC,
            Document.status == DocumentStatus.ACTIVE,
            Document.deleted_at.is_(None),
            Document.platform_id.is_not(None),
        )
    )
    return query, latest_published


@router.get("", response_model=PublicPlatformOverviewResponse)
def list_platform_overview(db: Session = Depends(get_db)):
    """Return platform overview rows (latest release + doc counts) without full doc payloads."""
    latest_published = _latest_published_subquery(db)
    rows = (
        db.query(
            Document,
            Platform.name.label("platform_name"),
            latest_published.c.published_at,
            latest_published.c.version_number,
        )
        .join(Platform, Document.platform_id == Platform.id)
        .join(latest_published, Document.id == latest_published.c.document_id)
        .filter(
            Document.visibility == DocumentVisibility.PUBLIC,
            Document.status == DocumentStatus.ACTIVE,
            Document.deleted_at.is_(None),
            Document.platform_id.is_not(None),
        )
        .all()
    )

    platform_map: dict[int, dict] = {}
    for doc, platform_name, published_at, version_number in rows:
        if doc.platform_id is None:
            continue

        entry = platform_map.setdefault(
            doc.platform_id,
            {
                "id": doc.platform_id,
                "platform": platform_name,
                "doc_count": 0,
                "latest_release": None,
                "latest_release_ts": None,
            },
        )
        entry["doc_count"] += 1

        candidate_date: Optional[datetime] = published_at or doc.updated_at or doc.created_at
        latest_ts = entry["latest_release_ts"]
        candidate_ts = candidate_date.timestamp() if candidate_date else 0
        should_replace = latest_ts is None or candidate_ts > latest_ts
        if should_replace:
            entry["latest_release_ts"] = candidate_ts
            entry["latest_release"] = PublicPlatformLatestRelease(
                id=doc.id,
                document_number=doc.document_number,
                title=doc.title,
                release_branch=doc.release_branch,
                version_label=doc.version_label,
                version_number=version_number,
                published_at=published_at,
                updated_at=doc.updated_at,
            )

    items = [
        PublicPlatformOverviewItem(
            id=entry["id"],
            platform=entry["platform"],
            doc_count=entry["doc_count"],
            latest_release=entry["latest_release"],
        )
        for entry in platform_map.values()
    ]
    items.sort(key=lambda item: item.platform.lower())
    return PublicPlatformOverviewResponse(items=items)


@router.get("/{platform_id}/documents", response_model=PublicPlatformDocumentsResponse)
def get_platform_documents(
    platform_id: int,
    search: Optional[str] = Query(None, description="Search documents in this platform"),
    sort_by: str = Query(
        "latest",
        pattern="^(latest|name|category|version|status)$",
        description="Sort field",
    ),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db),
):
    """Return all public documents for a single platform ID."""
    platform = db.query(Platform).filter(Platform.id == platform_id).first()
    if not platform:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Platform not found")

    query, latest_published = _public_platform_documents_query(db)
    query = query.filter(Document.platform_id == platform_id)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Document.title.ilike(search_term),
                Document.document_number.ilike(search_term),
                Document.category.ilike(search_term),
            )
        )

    total = query.count()

    sort_map = {
        "latest": func.coalesce(
            latest_published.c.published_at,
            Document.updated_at,
            Document.created_at,
        ),
        "name": Document.title,
        "category": Document.category,
        "version": latest_published.c.version_number,
        "status": Document.status,
    }
    order_column = sort_map.get(sort_by, sort_map["latest"])
    query = query.order_by(order_column.asc() if sort_order == "asc" else order_column.desc())

    rows = query.all()
    items = [
        PublicPlatformDocumentRow(
            id=doc.id,
            title=doc.title,
            document_number=doc.document_number,
            category=doc.category,
            version_label=doc.version_label,
            version_number=version_number,
            published_at=published_at,
            updated_at=doc.updated_at,
            status=doc.status.value if hasattr(doc.status, "value") else str(doc.status),
        )
        for doc, published_at, version_number in rows
    ]

    return PublicPlatformDocumentsResponse(
        platform_id=platform.id,
        platform=platform.name,
        total=total,
        items=items,
    )
