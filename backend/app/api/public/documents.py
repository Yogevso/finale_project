"""
Public Documents API - No Authentication Required

This module provides public access to published documents with PUBLIC visibility.
No authentication is required for these endpoints.
"""

import math
from datetime import datetime
from typing import Optional
from xml.sax.saxutils import escape as xml_escape

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db import get_db
from app.domain.specifications.audience_policies import (
    ExternalEmbedPolicySpec,
    LinkSharingPolicySpec,
)
from app.models import Attachment, Document, DocumentStatus, DocumentVisibility, Platform, Topic, Version
from app.schemas.public import (
    PublicAttachmentInfo,
    PublicCategoriesResponse,
    PublicCategoryCount,
    PublicDocumentListResponse,
    PublicDocumentSummary,
    PublicDocumentWithAttachments,
    PublicPlatformCategoryGroup,
    PublicPlatformDocument,
    PublicPlatformGroup,
    PublicPlatformHistoryResponse,
    PublicPlatformYearGroup,
    PublicSearchResponse,
    PublicSearchResult,
)
from app.utils.topic_normalization import build_topic_lookup, normalize_topic_to_slug

router = APIRouter(prefix="/public", tags=["Public"])

# Short cache for public listings, longer for individual documents.
_PUBLIC_LIST_MAX_AGE = 60  # 1 minute
_PUBLIC_DETAIL_MAX_AGE = 300  # 5 minutes


def _set_public_cache_headers(response: Response, *, max_age: int, etag: str | None = None) -> None:
    """Set Cache-Control and optional ETag on public responses."""
    response.headers["Cache-Control"] = f"public, max-age={max_age}, stale-while-revalidate={max_age * 2}"
    if etag:
        response.headers["ETag"] = f'"{etag}"'


def get_public_documents_query(db: Session):
    """
    Base query for public documents.
    Only returns documents that are:
    - visibility = PUBLIC
    - not deleted
    """
    return db.query(Document).filter(
        Document.visibility == DocumentVisibility.PUBLIC,
        Document.deleted_at.is_(None),
    )


def _resolve_topic_aliases(db: Session, raw_topic: Optional[str]) -> set[str]:
    normalized_without_lookup = normalize_topic_to_slug(raw_topic)
    if not normalized_without_lookup:
        return set()

    topics = db.query(Topic).all()
    topic_lookup = build_topic_lookup(topics)
    canonical = normalize_topic_to_slug(raw_topic, topic_lookup) or normalized_without_lookup

    aliases = {canonical}
    aliases.update(alias for alias, mapped in topic_lookup.items() if mapped == canonical)
    return aliases


def _apply_topic_filter(query, db: Session, raw_topic: Optional[str]):
    aliases = _resolve_topic_aliases(db, raw_topic)
    if not aliases:
        return query.filter(Document.id == -1)
    normalized_topic = func.lower(func.trim(Document.topic))
    return query.filter(normalized_topic.in_(aliases))


@router.get("/documents", response_model=PublicDocumentListResponse)
def list_public_documents(
    response: Response,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    search: Optional[str] = Query(None, max_length=500, description="Search in title/description"),
    sort_by: Optional[str] = Query("created_at", pattern="^(title|created_at|updated_at)$", description="Sort field: title, created_at, updated_at"),
    sort_order: Optional[str] = Query("desc", pattern="^(asc|desc)$", description="Sort order (asc/desc)"),
    db: Session = Depends(get_db),
):
    """
    List all public published documents.

    No authentication required.

    - Supports pagination
    - Optional category filter
    - Optional search in title/description
    - Sortable by created_at, title, updated_at
    """
    query = get_public_documents_query(db)

    # Apply filters
    if category:
        query = query.filter(Document.category == category)
    if topic:
        query = _apply_topic_filter(query, db, topic)
    if platform:
        query = query.join(Platform, Document.platform_id == Platform.id).filter(Platform.name == platform)

    # Apply search filter
    if search:
        # M-36: Escape SQL wildcards to prevent injection
        _escaped = search.replace("%", r"\%").replace("_", r"\_")
        search_term = f"%{_escaped}%"
        platform_subq = db.query(Document.id).join(Platform, Document.platform_id == Platform.id).filter(Platform.name.ilike(search_term, escape="\\")).subquery()
        query = query.filter(
            or_(
                Document.title.ilike(search_term, escape="\\"),
                Document.description.ilike(search_term, escape="\\"),
                Document.tags.ilike(search_term, escape="\\"),
                Document.topic.ilike(search_term, escape="\\"),
                Document.id.in_(db.query(platform_subq)),
            )
        )

    latest_published = (
        db.query(
            Version.document_id.label("document_id"),
            func.max(Version.published_at).label("published_at"),
            func.max(Version.version_number).label("version_number"),
        )
        .filter(Version.is_published.is_(True))
        .group_by(Version.document_id)
        .subquery()
    )

    query = query.outerjoin(
        latest_published, Document.id == latest_published.c.document_id
    ).add_columns(latest_published.c.published_at, latest_published.c.version_number)

    # Get total count
    total = query.count()

    # Apply sorting
    if sort_by == "title":
        order_col = Document.title
    elif sort_by == "updated_at":
        order_col = Document.updated_at
    else:
        order_col = Document.created_at

    if sort_order == "asc":
        query = query.order_by(order_col.asc())
    else:
        query = query.order_by(order_col.desc())

    # Apply pagination
    skip = (page - 1) * page_size
    documents = query.offset(skip).limit(page_size).all()

    # Calculate total pages
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    items = []
    for doc, published_at, version_number in documents:
        items.append(
            PublicDocumentSummary(
                id=doc.id,
                document_number=doc.document_number,
                title=doc.title,
                description=doc.description,
                category=doc.category,
                topic=doc.topic,
                platform=doc.platform_name,
                release_branch=doc.release_branch,
                tags=doc.tags,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
                published_at=published_at,
                version_number=version_number,
            )
        )

    result = PublicDocumentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )

    _set_public_cache_headers(response, max_age=_PUBLIC_LIST_MAX_AGE)
    return result


@router.get("/documents/{document_id}", response_model=PublicDocumentWithAttachments)
def get_public_document(document_id: int, response: Response, db: Session = Depends(get_db)):
    """
    Get a single public document with its content.

    No authentication required.

    Returns the latest published version content.
    """
    # Get document
    document = get_public_documents_query(db).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or not publicly accessible",
        )

    # Get latest published version, fall back to latest version
    latest_version = (
        db.query(Version)
        .filter(
            Version.document_id == document_id,
            Version.is_published == True,  # noqa: E712
        )
        .order_by(Version.version_number.desc())
        .first()
    )

    if not latest_version:
        latest_version = (
            db.query(Version)
            .filter(Version.document_id == document_id)
            .order_by(Version.version_number.desc())
            .first()
        )

    if not latest_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document has no versions",
        )

    # AF-002: Only include attachments uploaded before the published version's
    # publish timestamp so new uploads don't leak to public readers.
    cutoff = latest_version.published_at or latest_version.created_at
    attachments = (
        db.query(Attachment)
        .filter(
            Attachment.document_id == document_id,
            Attachment.uploaded_at <= cutoff,
        )
        .order_by(Attachment.uploaded_at.desc())
        .all()
    )

    # Build response
    sharing_policy = LinkSharingPolicySpec.for_document(document).to_dict()
    embed_policy = ExternalEmbedPolicySpec.for_document(document).to_dict()

    doc_payload = PublicDocumentWithAttachments(
        id=document.id,
        document_number=document.document_number,
        title=document.title,
        description=document.description,
        category=document.category,
        topic=document.topic,
        platform=document.platform_name,
        release_branch=document.release_branch,
        tags=document.tags,
        created_at=document.created_at,
        updated_at=document.updated_at,
        content=latest_version.content if latest_version else None,
        version_number=latest_version.version_number if latest_version else None,
        published_at=latest_version.published_at if latest_version else None,
        has_attachments=len(attachments) > 0,
        attachment_count=len(attachments),
        attachments=[
            PublicAttachmentInfo(
                id=att.id,
                filename=att.filename,
                file_size=att.file_size,
                content_type=att.mime_type,
                created_at=att.uploaded_at,
            )
            for att in attachments
        ],
        sharing_policy=sharing_policy,
        embed_policy=embed_policy,
    )

    # Set X-Frame-Options based on embed policy
    embed_spec = ExternalEmbedPolicySpec.for_document(document)
    response.headers["X-Frame-Options"] = embed_spec.x_frame_options_header

    # ETag based on document version + update time
    etag = f"doc-{document_id}-v{latest_version.version_number if latest_version else 0}"
    _set_public_cache_headers(response, max_age=_PUBLIC_DETAIL_MAX_AGE, etag=etag)
    return doc_payload


@router.get("/platforms/history", response_model=PublicPlatformHistoryResponse)
def get_platform_history(db: Session = Depends(get_db)):
    """
    Group public documents by platform -> category -> year (from published_at).

    Falls back to updated_at/created_at when published_at is not available.
    """
    latest_published = (
        db.query(
            Version.document_id.label("document_id"),
            func.max(Version.published_at).label("published_at"),
            func.max(Version.version_number).label("version_number"),
        )
        .filter(Version.is_published.is_(True))
        .group_by(Version.document_id)
        .subquery()
    )

    rows = (
        get_public_documents_query(db)
        .outerjoin(latest_published, Document.id == latest_published.c.document_id)
        .add_columns(latest_published.c.published_at, latest_published.c.version_number)
        .all()
    )

    platform_map: dict[str, dict[str, dict[Optional[int], list[PublicPlatformDocument]]]] = {}

    for doc, published_at, version_number in rows:
        platform = doc.platform_name or "Unspecified"
        category = doc.category or "General"
        effective_date = published_at or doc.updated_at or doc.created_at
        year = effective_date.year if effective_date else None

        platform_map.setdefault(platform, {})
        platform_map[platform].setdefault(category, {})
        platform_map[platform][category].setdefault(year, [])

        platform_map[platform][category][year].append(
            PublicPlatformDocument(
                id=doc.id,
                document_number=doc.document_number,
                title=doc.title,
                category=doc.category,
                platform=doc.platform_name,
                release_branch=doc.release_branch,
                version_label=doc.version_label,
                version_number=version_number,
                published_at=published_at,
                updated_at=doc.updated_at,
            )
        )

    platforms: list[PublicPlatformGroup] = []
    for platform_name in sorted(platform_map.keys(), key=lambda v: v.lower()):
        categories: list[PublicPlatformCategoryGroup] = []
        for category_name in sorted(platform_map[platform_name].keys(), key=lambda v: v.lower()):
            year_groups: list[PublicPlatformYearGroup] = []
            year_map = platform_map[platform_name][category_name]
            for year in sorted(
                year_map.keys(),
                key=lambda v: (v is None, v),
                reverse=True,
            ):
                docs = sorted(
                    year_map[year],
                    key=lambda d: d.published_at or d.updated_at or datetime.min,
                    reverse=True,
                )
                year_groups.append(PublicPlatformYearGroup(year=year, documents=docs))

            categories.append(
                PublicPlatformCategoryGroup(category=category_name, years=year_groups)
            )

        platforms.append(PublicPlatformGroup(platform=platform_name, categories=categories))

    return PublicPlatformHistoryResponse(items=platforms)


@router.get("/categories", response_model=PublicCategoriesResponse)
def list_public_categories(db: Session = Depends(get_db)):
    """
    List all categories that have public published documents.

    No authentication required.

    Returns category names with document counts.
    """
    # Query categories with counts
    category_counts = (
        get_public_documents_query(db)
        .with_entities(Document.category, func.count(Document.id).label("count"))
        .filter(
            Document.category != None,  # noqa: E711
            Document.category != "",
        )
        .group_by(Document.category)
        .order_by(func.count(Document.id).desc())
        .all()
    )

    items = [PublicCategoryCount(category=cat, count=count) for cat, count in category_counts]

    return PublicCategoriesResponse(items=items, total=len(items))


@router.get("/search", response_model=PublicSearchResponse)
def search_public_documents(
    q: str = Query(..., min_length=2, max_length=500, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    db: Session = Depends(get_db),
):
    """
    Search across public document metadata.

    No authentication required.

    Searches in:
    - Title
    - Description
    - Tags
    - Document number
    - Topic
    - Platform

    Note: This endpoint searches metadata fields only, not document body content.
    """
    # M-36: Escape SQL wildcards to prevent injection
    _escaped_q = q.replace("%", r"\%").replace("_", r"\_")
    search_term = f"%{_escaped_q}%"

    # Start with public documents query
    query = get_public_documents_query(db)

    # Apply category filter if provided
    if category:
        query = query.filter(Document.category == category)
    if topic:
        query = _apply_topic_filter(query, db, topic)
    if platform:
        query = query.join(Platform, Document.platform_id == Platform.id).filter(Platform.name == platform)

    # Search in document fields
    platform_subq = db.query(Document.id).join(Platform, Document.platform_id == Platform.id).filter(Platform.name.ilike(search_term, escape="\\")).subquery()
    query = query.filter(
        or_(
            Document.title.ilike(search_term, escape="\\"),
            Document.description.ilike(search_term, escape="\\"),
            Document.tags.ilike(search_term, escape="\\"),
            Document.document_number.ilike(search_term, escape="\\"),
            Document.topic.ilike(search_term, escape="\\"),
            Document.id.in_(db.query(platform_subq)),
        )
    )

    # Get total count
    total = query.count()

    # Apply pagination
    skip = (page - 1) * page_size
    documents = query.order_by(Document.updated_at.desc()).offset(skip).limit(page_size).all()

    # Build search results with snippets
    results = []
    for doc in documents:
        # Create a snippet from description or title
        snippet = None
        if doc.description:
            # Find matching part in description
            desc_lower = doc.description.lower()
            q_lower = q.lower()
            pos = desc_lower.find(q_lower)
            if pos >= 0:
                start = max(0, pos - 50)
                end = min(len(doc.description), pos + len(q) + 50)
                snippet = (
                    ("..." if start > 0 else "")
                    + doc.description[start:end]
                    + ("..." if end < len(doc.description) else "")
                )
            else:
                snippet = (
                    doc.description[:100] + "..." if len(doc.description) > 100 else doc.description
                )

        results.append(
            PublicSearchResult(
                id=doc.id,
                document_number=doc.document_number,
                title=doc.title,
                description=doc.description,
                category=doc.category,
                topic=doc.topic,
                platform=doc.platform_name,
                snippet=snippet,
                score=1.0,  # Simple relevance score
            )
        )

    return PublicSearchResponse(query=q, items=results, total=total, page=page, page_size=page_size)


@router.get("/documents/{document_id}/attachments/{attachment_id}")
def get_public_attachment(document_id: int, attachment_id: int, db: Session = Depends(get_db)):
    """
    Get attachment info for a public document.

    No authentication required.

    Note: Actual file download may require separate endpoint with rate limiting.
    """
    # Verify document is public
    document = get_public_documents_query(db).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or not publicly accessible",
        )

    # C6: Only serve attachments that existed at publish time
    from app.services.published_attachment_resolver import is_attachment_in_published_snapshot

    if not is_attachment_in_published_snapshot(db, document_id, attachment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    # Get attachment
    attachment = (
        db.query(Attachment)
        .filter(Attachment.id == attachment_id, Attachment.document_id == document_id)
        .first()
    )

    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    return PublicAttachmentInfo(
        id=attachment.id,
        filename=attachment.filename,
        file_size=attachment.file_size,
        content_type=attachment.mime_type,
        created_at=attachment.uploaded_at,
    )


@router.get("/stats")
def get_public_stats(db: Session = Depends(get_db)):
    """
    Get public statistics.

    No authentication required.

    Returns counts of public documents, categories, etc.
    """
    # Count public documents
    doc_count = get_public_documents_query(db).count()

    # Count categories
    category_count = (
        get_public_documents_query(db)
        .with_entities(func.count(func.distinct(Document.category)))
        .filter(
            Document.category != None,  # noqa: E711
            Document.category != "",
        )
        .scalar()
    )

    return {"total_documents": doc_count, "total_categories": category_count or 0}


# ---------------------------------------------------------------------------
# Sitemap – public documents only
# ---------------------------------------------------------------------------

_SITEMAP_XML_HEADER = '<?xml version="1.0" encoding="UTF-8"?>\n'
_SITEMAP_URLSET_OPEN = (
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
)
_SITEMAP_URLSET_CLOSE = "</urlset>\n"


@router.get(
    "/sitemap.xml",
    response_class=Response,
    summary="Sitemap of all public documents",
    description="Returns an XML sitemap containing only PUBLIC + ACTIVE documents. Useful for SEO crawlers.",
)
def get_public_sitemap(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    base_url: Optional[str] = Query(
        None,
        description="Override base URL for sitemap <loc> entries. Defaults to request origin.",
    ),
):
    """Generate an XML sitemap that only includes PUBLIC and ACTIVE documents."""
    origin = base_url or str(request.base_url).rstrip("/")
    escaped_origin = xml_escape(origin)

    docs = (
        get_public_documents_query(db)
        .with_entities(Document.id, Document.updated_at)
        .order_by(Document.updated_at.desc())
        .all()
    )

    lines: list[str] = [_SITEMAP_XML_HEADER, _SITEMAP_URLSET_OPEN]
    for doc_id, updated_at in docs:
        lastmod = updated_at.strftime("%Y-%m-%d") if updated_at else ""
        lines.append("  <url>\n")
        lines.append(f"    <loc>{escaped_origin}/doc/{doc_id}</loc>\n")
        if lastmod:
            lines.append(f"    <lastmod>{lastmod}</lastmod>\n")
        lines.append("    <changefreq>weekly</changefreq>\n")
        lines.append("    <priority>0.7</priority>\n")
        lines.append("  </url>\n")
    lines.append(_SITEMAP_URLSET_CLOSE)

    _set_public_cache_headers(response, max_age=_PUBLIC_LIST_MAX_AGE)
    xml_response = Response(content="".join(lines), media_type="application/xml")
    xml_response.headers["Cache-Control"] = response.headers.get("Cache-Control", "")
    return xml_response


# ---------------------------------------------------------------------------
# RSS Feed – public documents only
# ---------------------------------------------------------------------------


@router.get(
    "/feed.xml",
    response_class=Response,
    summary="RSS 2.0 feed of recent public documents",
    description="Returns an RSS 2.0 XML feed containing the most recent PUBLIC + ACTIVE documents.",
)
def get_public_rss_feed(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of items in the feed"),
    base_url: Optional[str] = Query(
        None,
        description="Override base URL for feed <link> entries. Defaults to request origin.",
    ),
):
    """Generate an RSS 2.0 feed filtered to PUBLIC + ACTIVE documents only."""
    origin = base_url or str(request.base_url).rstrip("/")

    docs = (
        get_public_documents_query(db)
        .with_entities(Document.id, Document.title, Document.description, Document.updated_at, Document.category)
        .order_by(Document.updated_at.desc())
        .limit(limit)
        .all()
    )

    def _escape(text: str | None) -> str:
        if not text:
            return ""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    lines: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>\n',
        '<rss version="2.0">\n',
        "  <channel>\n",
        "    <title>Public Documents</title>\n",
        f"    <link>{_escape(origin)}/docs</link>\n",
        "    <description>Recently updated public documents</description>\n",
    ]

    for doc_id, title, description, updated_at, category in docs:
        pub_date = updated_at.strftime("%a, %d %b %Y %H:%M:%S GMT") if updated_at else ""
        lines.append("    <item>\n")
        lines.append(f"      <title>{_escape(title)}</title>\n")
        lines.append(f"      <link>{_escape(origin)}/doc/{doc_id}</link>\n")
        if description:
            lines.append(f"      <description>{_escape(description)}</description>\n")
        if category:
            lines.append(f"      <category>{_escape(category)}</category>\n")
        if pub_date:
            lines.append(f"      <pubDate>{pub_date}</pubDate>\n")
        lines.append(f"      <guid>{_escape(origin)}/doc/{doc_id}</guid>\n")
        lines.append("    </item>\n")

    lines.append("  </channel>\n")
    lines.append("</rss>\n")

    _set_public_cache_headers(response, max_age=_PUBLIC_LIST_MAX_AGE)
    rss_response = Response(content="".join(lines), media_type="application/rss+xml")
    rss_response.headers["Cache-Control"] = response.headers.get("Cache-Control", "")
    return rss_response
