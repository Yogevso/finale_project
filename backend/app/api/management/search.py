"""Search API with configurable backend search and saved searches."""

import hashlib
import logging
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.application.policies.access_policies import AnalyticsAccessPolicy
from app.application.queries.dependencies import get_search_query_handler
from app.application.queries.search_queries import (
    ListSavedSearchesQuery,
    SearchAutocompleteQuery,
    SearchDocumentsQuery,
    SearchFacetsQuery,
    SearchQueryHandler,
)
from app.db import get_analytics_db, get_db
from app.dependencies.permissions import require_any_role, require_internal_user
from app.models import Document, SavedSearch, SearchAnalytics, User, UserRole

_analytics_policy = AnalyticsAccessPolicy()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["Search"])


def _format_analytics_query_label(raw_query: str, *, current_user: User) -> str:
    if not _analytics_policy.is_tenant_scoped(current_user):
        digest = hashlib.sha256(raw_query.encode("utf-8")).hexdigest()[:12]
        return f"[redacted-query:{digest}]"
    return raw_query


# Schemas
class SearchResult(BaseModel):
    id: int
    title: str
    document_number: str
    description: Optional[str]
    category: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    relevance_score: float = 0.0

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    items: List[SearchResult]
    total: int
    query: str
    suggestions: List[str] = []


class SavedSearchCreate(BaseModel):
    name: str
    query: Optional[str] = None
    category: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class SavedSearchResponse(BaseModel):
    id: int
    name: str
    query: Optional[str]
    category: Optional[str]
    date_from: Optional[datetime]
    date_to: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=SearchResponse)
def search_documents(
    q: str = Query(..., min_length=1, description="Search query"),
    category: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_internal_user),
    search_query_handler: SearchQueryHandler = Depends(get_search_query_handler),
    analytics_db: Session = Depends(get_analytics_db),
):
    """Search documents using the configured runtime search backend."""
    result = search_query_handler.execute_search_documents(
        SearchDocumentsQuery(
            q=q,
            category=category,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
            current_user=current_user,
        )
    )

    # Log search analytics (fire-and-forget)
    try:
        analytics_db.add(
            SearchAnalytics(
                query=q[:500],
                user_id=current_user.id,
                tenant_id=current_user.tenant_id,
                results_count=result.total,
            )
        )
        analytics_db.commit()
    except Exception:  # policy: LOSSY — analytics logging must not block search responses
        logger.debug("Failed to log search analytics", exc_info=True)

    return SearchResponse(
        items=[SearchResult(**asdict(item)) for item in result.items],
        total=result.total,
        query=result.query,
        suggestions=result.suggestions,
    )


@router.get("/autocomplete")
def autocomplete(
    q: str = Query(..., min_length=2, description="Partial search query"),
    limit: int = Query(10, ge=1, le=20),
    current_user: User = Depends(require_internal_user),
    search_query_handler: SearchQueryHandler = Depends(get_search_query_handler),
):
    """Get autocomplete suggestions for search"""
    suggestions = search_query_handler.execute_autocomplete(
        SearchAutocompleteQuery(q=q, limit=limit, current_user=current_user)
    )
    return {"suggestions": suggestions}


@router.get("/facets")
def get_search_facets(
    current_user: User = Depends(require_internal_user),
    search_query_handler: SearchQueryHandler = Depends(get_search_query_handler),
):
    """Get facet counts for filtering"""
    return search_query_handler.execute_facets(SearchFacetsQuery(current_user=current_user))


# Saved Searches
@router.get("/saved", response_model=List[SavedSearchResponse])
def list_saved_searches(
    current_user: User = Depends(require_internal_user),
    search_query_handler: SearchQueryHandler = Depends(get_search_query_handler),
):
    """List user's saved searches"""
    return search_query_handler.execute_list_saved_searches(
        ListSavedSearchesQuery(user_id=current_user.id)
    )


@router.post("/saved", response_model=SavedSearchResponse)
def create_saved_search(
    data: SavedSearchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_internal_user),
):
    """Save a search for quick access"""
    saved = SavedSearch(
        user_id=current_user.id,
        name=data.name,
        query=data.query,
        category=data.category,
        date_from=data.date_from,
        date_to=data.date_to,
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)
    return saved


@router.delete("/saved/{search_id}")
def delete_saved_search(
    search_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_internal_user),
):
    """Delete a saved search"""
    saved = (
        db.query(SavedSearch)
        .filter(SavedSearch.id == search_id, SavedSearch.user_id == current_user.id)
        .first()
    )

    if not saved:
        raise HTTPException(status_code=404, detail="Saved search not found")

    db.delete(saved)
    db.commit()
    return {"message": "Saved search deleted"}


# ---- Search Analytics (Y2-005) ----


class SearchClickBody(BaseModel):
    query: str
    document_id: int


@router.post("/click")
def record_search_click(
    body: SearchClickBody,
    db: Session = Depends(get_analytics_db),
    core_db: Session = Depends(get_db),
    current_user: User = Depends(require_internal_user),
):
    """Record that a user clicked a search result."""
    # M-39: Verify the document belongs to the caller's tenant to prevent
    # cross-tenant analytics poisoning via arbitrary document_id.
    doc = (
        core_db.query(Document.id, Document.tenant_id)
        .filter(Document.id == body.document_id)
        .first()
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if (
        current_user.role != UserRole.SYSTEM_ADMIN
        and doc.tenant_id is not None
        and doc.tenant_id != current_user.tenant_id
    ):
        raise HTTPException(status_code=404, detail="Document not found")

    db.add(
        SearchAnalytics(
            query=body.query[:500],
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            results_count=0,
            clicked_document_id=body.document_id,
        )
    )
    db.commit()
    return {"ok": True}


@router.get("/analytics")
def get_search_analytics(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_analytics_db),
    current_user: User = Depends(
        require_any_role([UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER])
    ),
):
    """Get search analytics — top queries, zero-result queries, click-through."""
    since = datetime.utcnow() - timedelta(days=days)

    # Only count search events (results_count > 0 or results_count == 0 means a search event)
    # Click events have clicked_document_id set
    search_events = db.query(SearchAnalytics).filter(
        SearchAnalytics.created_at >= since,
        SearchAnalytics.clicked_document_id.is_(None),
    )

    # Tenant scoping for non-system-admins (M-29: delegated to AnalyticsAccessPolicy)
    if _analytics_policy.is_tenant_scoped(current_user):
        search_events = search_events.filter(SearchAnalytics.tenant_id == current_user.tenant_id)

    # Top queries
    top_queries = (
        search_events.with_entities(
            SearchAnalytics.query,
            func.count().label("count"),
            func.avg(SearchAnalytics.results_count).label("avg_results"),
        )
        .group_by(SearchAnalytics.query)
        .order_by(func.count().desc())
        .limit(20)
        .all()
    )

    # Zero-result queries
    zero_results = (
        search_events.filter(SearchAnalytics.results_count == 0)
        .with_entities(
            SearchAnalytics.query,
            func.count().label("count"),
        )
        .group_by(SearchAnalytics.query)
        .order_by(func.count().desc())
        .limit(20)
        .all()
    )

    # Click-through rate
    total_searches = search_events.count()
    click_query = db.query(SearchAnalytics).filter(
        SearchAnalytics.created_at >= since,
        SearchAnalytics.clicked_document_id.isnot(None),
    )
    if _analytics_policy.is_tenant_scoped(current_user):
        click_query = click_query.filter(SearchAnalytics.tenant_id == current_user.tenant_id)
    total_clicks = click_query.count()
    ctr = (total_clicks / total_searches * 100) if total_searches > 0 else 0

    return {
        "period_days": days,
        "total_searches": total_searches,
        "total_clicks": total_clicks,
        "click_through_rate": round(ctr, 1),
        "top_queries": [
            {
                "query": _format_analytics_query_label(q, current_user=current_user),
                "count": c,
                "avg_results": round(float(a or 0), 1),
            }
            for q, c, a in top_queries
        ],
        "zero_result_queries": [
            {
                "query": _format_analytics_query_label(q, current_user=current_user),
                "count": c,
            }
            for q, c in zero_results
        ],
    }
