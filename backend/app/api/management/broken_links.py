"""Broken Link Reports API — admin endpoints for viewing link scan results."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.permissions import require_manager
from app.models import BrokenLinkReport, Document, User
from app.services.broken_link_service import scan_broken_links

router = APIRouter(
    prefix="/broken-links",
    tags=["Broken Links"],
    dependencies=[Depends(require_manager)],
)


@router.get("")
async def list_broken_links(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """Return all broken link reports with document info."""
    rows = (
        db.query(BrokenLinkReport, Document.title, Document.document_number)
        .join(Document, BrokenLinkReport.document_id == Document.id)
        .order_by(BrokenLinkReport.scanned_at.desc())
        .all()
    )
    return {
        "total": len(rows),
        "items": [
            {
                "id": report.id,
                "document_id": report.document_id,
                "document_title": title,
                "document_number": doc_number,
                "broken_url": report.broken_url,
                "link_text": report.link_text,
                "reason": report.reason,
                "scanned_at": report.scanned_at.isoformat() if report.scanned_at else None,
            }
            for report, title, doc_number in rows
        ],
    }


@router.get("/summary")
async def broken_links_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """Return summary counts grouped by reason."""
    rows = (
        db.query(BrokenLinkReport.reason, func.count(BrokenLinkReport.id))
        .group_by(BrokenLinkReport.reason)
        .all()
    )
    total = sum(count for _, count in rows)
    by_reason = {reason: count for reason, count in rows}

    affected_docs = (
        db.query(func.count(func.distinct(BrokenLinkReport.document_id))).scalar() or 0
    )

    return {
        "total_broken_links": total,
        "affected_documents": affected_docs,
        "by_reason": by_reason,
    }


@router.post("/scan")
async def trigger_scan(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """Manually trigger a broken link scan."""
    broken_count = scan_broken_links(db)
    return {"broken_links_found": broken_count}
