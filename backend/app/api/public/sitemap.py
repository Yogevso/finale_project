"""XML Sitemap endpoint for public documents."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Document, DocumentStatus, DocumentVisibility

router = APIRouter(tags=["Sitemap"])

_SITEMAP_HEADER = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
_SITEMAP_FOOTER = "</urlset>\n"


@router.get("/sitemap.xml")
async def sitemap(db: Session = Depends(get_db)):
    """Generate an XML sitemap listing all published public documents."""
    docs = (
        db.query(Document.id, Document.updated_at)
        .filter(
            Document.status == DocumentStatus.ACTIVE,
            Document.visibility == DocumentVisibility.PUBLIC,
        )
        .order_by(Document.updated_at.desc())
        .all()
    )

    parts = [_SITEMAP_HEADER]
    for doc_id, updated_at in docs:
        lastmod = updated_at.strftime("%Y-%m-%d") if updated_at else ""
        parts.append("  <url>\n")
        parts.append(f"    <loc>/doc/{doc_id}</loc>\n")
        if lastmod:
            parts.append(f"    <lastmod>{lastmod}</lastmod>\n")
        parts.append("    <changefreq>weekly</changefreq>\n")
        parts.append("    <priority>0.8</priority>\n")
        parts.append("  </url>\n")
    parts.append(_SITEMAP_FOOTER)

    return Response(
        content="".join(parts),
        media_type="application/xml",
        headers={"Cache-Control": "public, max-age=3600"},
    )
