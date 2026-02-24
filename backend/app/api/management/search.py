"""Search API with FTS5 and saved searches"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Document, SavedSearch, User, UserRole
from app.security import get_current_active_user

router = APIRouter(prefix="/search", tags=["Search"])


def _is_system_admin(user: User) -> bool:
    return user.role == UserRole.SYSTEM_ADMIN


def _apply_document_tenant_scope(query, current_user: User):
    """Apply tenant scoping to document ORM queries for non-system admins."""
    if _is_system_admin(current_user):
        return query
    if current_user.tenant_id is None:
        return query.filter(Document.tenant_id.is_(None))
    return query.filter(Document.tenant_id == current_user.tenant_id)


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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Full-text search using SQLite FTS5"""
    offset = (page - 1) * page_size

    # Try FTS5 search first
    try:
        filters = ["documents_fts MATCH :query"]
        params: dict[str, object] = {"query": q, "limit": page_size, "offset": offset}

        if category:
            filters.append("d.category = :category")
            params["category"] = category
        if date_from:
            filters.append("d.created_at >= :date_from")
            params["date_from"] = date_from
        if date_to:
            filters.append("d.created_at <= :date_to")
            params["date_to"] = date_to

        if not _is_system_admin(current_user):
            if current_user.tenant_id is None:
                filters.append("d.tenant_id IS NULL")
            else:
                filters.append("d.tenant_id = :tenant_id")
                params["tenant_id"] = current_user.tenant_id

        where_clause = " AND ".join(filters)
        fts_query = text(
            f"""
            SELECT d.*, bm25(documents_fts) as score
            FROM documents d
            JOIN documents_fts ON d.id = documents_fts.rowid
            WHERE {where_clause}
            ORDER BY score
            LIMIT :limit OFFSET :offset
            """
        )
        result = db.execute(fts_query, params)
        docs = result.fetchall()

        # Count total
        count_query = text(
            f"""
            SELECT COUNT(*) FROM documents d
            JOIN documents_fts ON d.id = documents_fts.rowid
            WHERE {where_clause}
            """
        )
        count_params = {k: v for k, v in params.items() if k not in {"limit", "offset"}}
        total = db.execute(count_query, count_params).scalar() or 0

    except Exception:
        # Fallback to LIKE search if FTS5 fails
        query = db.query(Document).filter(
            (Document.title.ilike(f"%{q}%")) | (Document.description.ilike(f"%{q}%"))
        )
        query = _apply_document_tenant_scope(query, current_user)

        if category:
            query = query.filter(Document.category == category)
        if date_from:
            query = query.filter(Document.created_at >= date_from)
        if date_to:
            query = query.filter(Document.created_at <= date_to)

        total = query.count()
        docs = query.order_by(Document.updated_at.desc()).offset(offset).limit(page_size).all()

    items = [
        SearchResult(
            id=d.id if hasattr(d, "id") else d[0],
            title=d.title if hasattr(d, "title") else d[1],
            document_number=d.document_number if hasattr(d, "document_number") else d[2],
            description=d.description if hasattr(d, "description") else d[3],
            category=d.category if hasattr(d, "category") else d[5],
            status=d.status.value if hasattr(d, "status") else d[4],
            created_at=d.created_at if hasattr(d, "created_at") else d[7],
            updated_at=d.updated_at if hasattr(d, "updated_at") else d[8],
            relevance_score=getattr(d, "score", 0.0) if hasattr(d, "score") else 0.0,
        )
        for d in docs
    ]

    # Get autocomplete suggestions
    suggestions = get_autocomplete_suggestions(db, q, current_user=current_user)

    return SearchResponse(items=items, total=total, query=q, suggestions=suggestions)


@router.get("/autocomplete")
def autocomplete(
    q: str = Query(..., min_length=2, description="Partial search query"),
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get autocomplete suggestions for search"""
    suggestions = get_autocomplete_suggestions(db, q, limit, current_user=current_user)
    return {"suggestions": suggestions}


def get_autocomplete_suggestions(
    db: Session,
    q: str,
    limit: int = 5,
    *,
    current_user: Optional[User] = None,
) -> List[str]:
    """Get document title suggestions matching query prefix"""
    query = db.query(Document.title).filter(Document.title.ilike(f"%{q}%"))
    if current_user is not None:
        query = _apply_document_tenant_scope(query, current_user)
    docs = query.limit(limit).all()

    return [d.title for d in docs]


@router.get("/facets")
def get_search_facets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get facet counts for filtering"""
    # Category counts
    category_query = db.query(Document.category, text("COUNT(*)"))
    category_query = _apply_document_tenant_scope(category_query, current_user)
    categories = category_query.group_by(Document.category).all()

    # Status counts
    status_query = db.query(Document.status, text("COUNT(*)"))
    status_query = _apply_document_tenant_scope(status_query, current_user)
    statuses = status_query.group_by(Document.status).all()

    return {
        "categories": [{"name": c[0] or "Uncategorized", "count": c[1]} for c in categories],
        "statuses": [{"name": s[0].value if s[0] else "unknown", "count": s[1]} for s in statuses],
    }


# Saved Searches
@router.get("/saved", response_model=List[SavedSearchResponse])
def list_saved_searches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List user's saved searches"""
    searches = (
        db.query(SavedSearch)
        .filter(SavedSearch.user_id == current_user.id)
        .order_by(SavedSearch.created_at.desc())
        .all()
    )

    return searches


@router.post("/saved", response_model=SavedSearchResponse)
def create_saved_search(
    data: SavedSearchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
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
    current_user: User = Depends(get_current_active_user),
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
