"""Search API with FTS5 and saved searches"""

from dataclasses import asdict
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.application.queries.dependencies import get_search_query_handler
from app.application.queries.search_queries import (
    ListSavedSearchesQuery,
    SearchAutocompleteQuery,
    SearchDocumentsQuery,
    SearchFacetsQuery,
    SearchQueryHandler,
)
from app.db import get_db
from app.models import SavedSearch, User
from app.security import get_current_active_user

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
    current_user: User = Depends(get_current_active_user),
    search_query_handler: SearchQueryHandler = Depends(get_search_query_handler),
):
    """Full-text search using SQLite FTS5"""
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
    current_user: User = Depends(get_current_active_user),
    search_query_handler: SearchQueryHandler = Depends(get_search_query_handler),
):
    """Get autocomplete suggestions for search"""
    suggestions = search_query_handler.execute_autocomplete(
        SearchAutocompleteQuery(q=q, limit=limit, current_user=current_user)
    )
    return {"suggestions": suggestions}


@router.get("/facets")
def get_search_facets(
    current_user: User = Depends(get_current_active_user),
    search_query_handler: SearchQueryHandler = Depends(get_search_query_handler),
):
    """Get facet counts for filtering"""
    return search_query_handler.execute_facets(SearchFacetsQuery(current_user=current_user))


# Saved Searches
@router.get("/saved", response_model=List[SavedSearchResponse])
def list_saved_searches(
    current_user: User = Depends(get_current_active_user),
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
