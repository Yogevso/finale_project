"""Application query handlers for management search read models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.specifications import DateRangeSpec, TenantScopeSpec
from app.models import Document, SavedSearch, User
from app.repositories import DocumentRepository


@dataclass(frozen=True, slots=True)
class SearchDocumentReadModel:
    """Read-model row for document search results."""

    id: int
    title: str
    document_number: str
    description: Optional[str]
    category: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    relevance_score: float = 0.0


@dataclass(frozen=True, slots=True)
class SearchDocumentsQuery:
    """Search documents query."""

    q: str
    category: Optional[str]
    date_from: Optional[datetime]
    date_to: Optional[datetime]
    page: int
    page_size: int
    current_user: User


@dataclass(frozen=True, slots=True)
class SearchDocumentsQueryResult:
    """Search result payload."""

    items: list[SearchDocumentReadModel]
    total: int
    query: str
    suggestions: list[str]


@dataclass(frozen=True, slots=True)
class SearchAutocompleteQuery:
    """Autocomplete query."""

    q: str
    limit: int
    current_user: User


@dataclass(frozen=True, slots=True)
class SearchFacetsQuery:
    """Search facets query."""

    current_user: User


@dataclass(frozen=True, slots=True)
class ListSavedSearchesQuery:
    """Saved-search list query."""

    user_id: int


class SearchQueryHandler:
    """Read-handler facade for search queries."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _extract_status(raw: object) -> str:
        if hasattr(raw, "value"):
            value = raw.value
            return str(value) if value is not None else "unknown"
        if raw is None:
            return "unknown"
        return str(raw)

    @staticmethod
    def _build_read_model(row: object) -> SearchDocumentReadModel:
        if hasattr(row, "id"):
            score = row.score if hasattr(row, "score") else 0.0
            return SearchDocumentReadModel(
                id=row.id,
                title=row.title,
                document_number=row.document_number,
                description=row.description,
                category=row.category,
                status=SearchQueryHandler._extract_status(row.status),
                created_at=row.created_at,
                updated_at=row.updated_at,
                relevance_score=float(score),
            )

        return SearchDocumentReadModel(
            id=row[0],
            title=row[1],
            document_number=row[2],
            description=row[3],
            category=row[5],
            status=SearchQueryHandler._extract_status(row[4]),
            created_at=row[7],
            updated_at=row[8],
            relevance_score=float(getattr(row, "score", 0.0)),
        )

    def execute_search_documents(self, query: SearchDocumentsQuery) -> SearchDocumentsQueryResult:
        document_repository = DocumentRepository(self.db)
        tenant_scope_spec = TenantScopeSpec.for_user(query.current_user)
        date_range_spec = DateRangeSpec(date_from=query.date_from, date_to=query.date_to)
        offset = (query.page - 1) * query.page_size

        try:
            filters = ["documents_fts MATCH :search_query"]
            params: dict[str, object] = {
                "search_query": query.q,
                "limit": query.page_size,
                "offset": offset,
            }

            if query.category:
                filters.append("d.category = :category")
                params["category"] = query.category
            date_clauses, date_params = date_range_spec.sql_clauses(column_expr="d.created_at")
            filters.extend(date_clauses)
            params.update(date_params)
            tenant_clause, tenant_params = tenant_scope_spec.sql_clause(column_expr="d.tenant_id")
            if tenant_clause:
                filters.append(tenant_clause)
                params.update(tenant_params)

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
            docs = self.db.execute(fts_query, params).fetchall()

            count_query = text(
                f"""
                SELECT COUNT(*) FROM documents d
                JOIN documents_fts ON d.id = documents_fts.rowid
                WHERE {where_clause}
                """
            )
            count_params = {k: v for k, v in params.items() if k not in {"limit", "offset"}}
            total = self.db.execute(count_query, count_params).scalar() or 0
        except Exception:
            fallback_query = document_repository.query().filter(
                (Document.title.ilike(f"%{query.q}%")) | (Document.description.ilike(f"%{query.q}%"))
            )
            fallback_query = tenant_scope_spec.apply(fallback_query, Document)
            if query.category:
                fallback_query = fallback_query.filter(Document.category == query.category)
            fallback_query = date_range_spec.apply(fallback_query, Document.created_at)

            total = fallback_query.count()
            docs = (
                fallback_query.order_by(Document.updated_at.desc())
                .offset(offset)
                .limit(query.page_size)
                .all()
            )

        suggestions = self.execute_autocomplete(
            SearchAutocompleteQuery(q=query.q, limit=5, current_user=query.current_user)
        )
        return SearchDocumentsQueryResult(
            items=[self._build_read_model(row) for row in docs],
            total=int(total),
            query=query.q,
            suggestions=suggestions,
        )

    def execute_autocomplete(self, query: SearchAutocompleteQuery) -> list[str]:
        document_repository = DocumentRepository(self.db)
        title_query = document_repository.query().with_entities(Document.title).filter(
            Document.title.ilike(f"%{query.q}%")
        )
        title_query = TenantScopeSpec.for_user(query.current_user).apply(title_query, Document)
        docs = title_query.limit(query.limit).all()
        return [doc.title for doc in docs]

    def execute_facets(self, query: SearchFacetsQuery) -> dict:
        tenant_scope_spec = TenantScopeSpec.for_user(query.current_user)

        category_query = self.db.query(Document.category, text("COUNT(*)"))
        category_query = tenant_scope_spec.apply(category_query, Document)
        categories = category_query.group_by(Document.category).all()

        status_query = self.db.query(Document.status, text("COUNT(*)"))
        status_query = tenant_scope_spec.apply(status_query, Document)
        statuses = status_query.group_by(Document.status).all()

        return {
            "categories": [{"name": c[0] or "Uncategorized", "count": c[1]} for c in categories],
            "statuses": [{"name": s[0].value if s[0] else "unknown", "count": s[1]} for s in statuses],
        }

    def execute_list_saved_searches(self, query: ListSavedSearchesQuery) -> list[SavedSearch]:
        return (
            self.db.query(SavedSearch)
            .filter(SavedSearch.user_id == query.user_id)
            .order_by(SavedSearch.created_at.desc())
            .all()
        )
