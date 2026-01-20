"""Search API with FTS5 and saved searches"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Document, SavedSearch, User
from app.security import get_current_user

router = APIRouter(prefix="/search", tags=["Search"])


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
    current_user: User = Depends(get_current_user),
):
    """Full-text search using SQLite FTS5"""
    offset = (page - 1) * page_size

    # Try FTS5 search first
    try:
        fts_query = text("""
            SELECT d.*, bm25(documents_fts) as score
            FROM documents d
            JOIN documents_fts ON d.id = documents_fts.rowid
            WHERE documents_fts MATCH :query
            ORDER BY score
            LIMIT :limit OFFSET :offset
        """)
        result = db.execute(fts_query, {"query": q, "limit": page_size, "offset": offset})
        docs = result.fetchall()

        # Count total
        count_query = text("""
            SELECT COUNT(*) FROM documents d
            JOIN documents_fts ON d.id = documents_fts.rowid
            WHERE documents_fts MATCH :query
        """)
        total = db.execute(count_query, {"query": q}).scalar() or 0

    except Exception:
        # Fallback to LIKE search if FTS5 fails
        query = db.query(Document).filter(
            (Document.title.ilike(f"%{q}%")) |
            (Document.description.ilike(f"%{q}%"))
        )

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
            id=d.id if hasattr(d, 'id') else d[0],
            title=d.title if hasattr(d, 'title') else d[1],
            document_number=d.document_number if hasattr(d, 'document_number') else d[2],
            description=d.description if hasattr(d, 'description') else d[3],
            category=d.category if hasattr(d, 'category') else d[5],
            status=d.status.value if hasattr(d, 'status') else d[4],
            created_at=d.created_at if hasattr(d, 'created_at') else d[7],
            updated_at=d.updated_at if hasattr(d, 'updated_at') else d[8],
            relevance_score=getattr(d, 'score', 0.0) if hasattr(d, 'score') else 0.0,
        )
        for d in docs
    ]

    # Get autocomplete suggestions
    suggestions = get_autocomplete_suggestions(db, q)

    return SearchResponse(items=items, total=total, query=q, suggestions=suggestions)


@router.get("/autocomplete")
def autocomplete(
    q: str = Query(..., min_length=2, description="Partial search query"),
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get autocomplete suggestions for search"""
    suggestions = get_autocomplete_suggestions(db, q, limit)
    return {"suggestions": suggestions}


def get_autocomplete_suggestions(db: Session, q: str, limit: int = 5) -> List[str]:
    """Get document title suggestions matching query prefix"""
    docs = db.query(Document.title).filter(
        Document.title.ilike(f"%{q}%")
    ).limit(limit).all()

    return [d.title for d in docs]


@router.get("/facets")
def get_search_facets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get facet counts for filtering"""
    # Category counts
    categories = db.query(
        Document.category,
        text("COUNT(*)")
    ).group_by(Document.category).all()

    # Status counts
    statuses = db.query(
        Document.status,
        text("COUNT(*)")
    ).group_by(Document.status).all()

    return {
        "categories": [{"name": c[0] or "Uncategorized", "count": c[1]} for c in categories],
        "statuses": [{"name": s[0].value if s[0] else "unknown", "count": s[1]} for s in statuses],
    }


# Saved Searches
@router.get("/saved", response_model=List[SavedSearchResponse])
def list_saved_searches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List user's saved searches"""
    searches = db.query(SavedSearch).filter(
        SavedSearch.user_id == current_user.id
    ).order_by(SavedSearch.created_at.desc()).all()

    return searches


@router.post("/saved", response_model=SavedSearchResponse)
def create_saved_search(
    data: SavedSearchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
):
    """Delete a saved search"""
    saved = db.query(SavedSearch).filter(
        SavedSearch.id == search_id,
        SavedSearch.user_id == current_user.id
    ).first()

    if not saved:
        raise HTTPException(status_code=404, detail="Saved search not found")

    db.delete(saved)
    db.commit()
    return {"message": "Saved search deleted"}
