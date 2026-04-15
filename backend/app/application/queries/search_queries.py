"""Application query handlers for management search read models."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import and_, or_, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.config import settings
from app.domain.specifications import DateRangeSpec, TenantScopeSpec, VisibilitySpec
from app.feature_flags import BackendFeatureFlag, is_backend_feature_enabled
from app.infrastructure.degradation import DegradationPolicy, record_degradation
from app.models import Document, SavedSearch, SystemSetting, User, UserRole
from app.observability.search_runtime import (
    record_search_degraded_fallback,
    record_search_execution,
)
from app.projections import ProjectionCache, execute_cached_projection, get_projection_cache
from app.repositories import DocumentRepository
from app.search_backend import SearchBackendMode, database_dialect_name, resolve_search_backend_mode

# Default BM25 weights for FTS5 columns: title, description, category, tags
DEFAULT_RELEVANCE_WEIGHTS = {"title": 3.0, "description": 1.0, "category": 1.0, "tags": 2.0}
FTS_RESERVED_OPERATOR_TOKENS = {"AND", "OR", "NOT", "NEAR"}
FTS_TERM_PATTERN = re.compile(r"[\w]+", re.UNICODE)

logger = logging.getLogger(__name__)

POSTGRES_SEARCH_VECTOR = (
    "setweight(to_tsvector('simple', COALESCE(d.title, '')), 'A') || "
    "setweight(to_tsvector('simple', COALESCE(d.description, '')), 'B') || "
    "setweight(to_tsvector('simple', COALESCE(d.category, '')), 'C') || "
    "setweight(to_tsvector('simple', COALESCE(d.tags, '')), 'B')"
)


def escape_sql_wildcards(value: str) -> str:
    """Escape SQL LIKE wildcards to prevent injection."""
    return value.replace("%", r"\%").replace("_", r"\_")


def _extract_search_terms(raw_query: str, *, max_terms: int = 8) -> list[str]:
    terms: list[str] = []
    for token in FTS_TERM_PATTERN.findall(raw_query or ""):
        if token.upper() in FTS_RESERVED_OPERATOR_TOKENS:
            continue
        normalized = token.strip()
        if not normalized:
            continue
        terms.append(normalized[:64])
        if len(terms) >= max_terms:
            break
    return terms


def build_safe_fts_query(raw_query: str) -> str | None:
    """Convert free-form user input into a quoted FTS5 AND query."""
    terms = _extract_search_terms(raw_query)
    if not terms:
        return None
    escaped_terms = ['"' + term.replace('"', '""') + '"' for term in terms]
    return " AND ".join(escaped_terms)


def build_safe_plain_search_query(raw_query: str) -> str | None:
    """Convert free-form user input into a backend-safe plain-text search query."""
    terms = _extract_search_terms(raw_query)
    if not terms:
        return None
    return " ".join(terms)


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

    def __init__(
        self,
        db: Session,
        *,
        projection_cache: ProjectionCache | None = None,
    ):
        self.db = db
        self.projection_cache = projection_cache or get_projection_cache()

    @staticmethod
    def _visibility_cache_scope(user: User) -> str:
        role = user.role.value if hasattr(user.role, "value") else str(user.role)
        is_system_admin = role == "system_admin"
        tenant_scope = "system" if is_system_admin else f"tenant:{user.tenant_id}"
        return f"{tenant_scope}:role:{role}"

    @staticmethod
    def _visibility_spec_for_user(user: User) -> VisibilitySpec | None:
        """Return a ``VisibilitySpec`` appropriate for the searching user.

        * **system_admin** – no visibility restriction (returns ``None``).
        * **customer** – portal-style (PUBLIC + assigned COMPANY, active only).
        * **all other internal roles** – management (PUBLIC + INTERNAL + COMPANY, active only).
        """
        role = user.role.value if hasattr(user.role, "value") else str(user.role)
        if (
            role == UserRole.SYSTEM_ADMIN.value
            if hasattr(UserRole.SYSTEM_ADMIN, "value")
            else role == "system_admin"
        ):
            return None  # system admin sees everything
        if role == (UserRole.CUSTOMER.value if hasattr(UserRole.CUSTOMER, "value") else "customer"):
            return VisibilitySpec.customer_portal(user.tenant_id)
        return VisibilitySpec.management()

    def _get_relevance_weights(self) -> dict[str, float]:
        """Load configurable search relevance weights from system_settings."""
        try:
            setting = (
                self.db.query(SystemSetting)
                .filter(SystemSetting.key == "search_relevance_weights")
                .first()
            )
            if setting and setting.value:
                weights = json.loads(setting.value)
                return {
                    "title": float(weights.get("title", DEFAULT_RELEVANCE_WEIGHTS["title"])),
                    "description": float(
                        weights.get("description", DEFAULT_RELEVANCE_WEIGHTS["description"])
                    ),
                    "category": float(
                        weights.get("category", DEFAULT_RELEVANCE_WEIGHTS["category"])
                    ),
                    "tags": float(weights.get("tags", DEFAULT_RELEVANCE_WEIGHTS["tags"])),
                }
        except (json.JSONDecodeError, ValueError, TypeError, KeyError):
            pass
        return DEFAULT_RELEVANCE_WEIGHTS.copy()

    def _bm25_expression(self) -> str:
        """Build bm25() call with weighted columns: title, description, category, tags."""
        w = self._get_relevance_weights()
        return (
            "bm25(documents_fts, "
            f"{w['title']}, {w['description']}, {w['category']}, {w['tags']}, "
            "0.0, 0.0, 0.0)"
        )

    def _execute_cached(
        self,
        *,
        projection_name: str,
        key_parts: tuple[object, ...],
        loader,
        ttl_seconds: int = 45,
        validator=None,
    ):
        if not is_backend_feature_enabled(BackendFeatureFlag.PROJECTION_CACHE):
            return loader()
        return execute_cached_projection(
            cache=self.projection_cache,
            namespace=f"search.{projection_name}",
            key_parts=key_parts,
            scopes={"search"},
            loader=loader,
            ttl_seconds=ttl_seconds,
            validator=validator,
        )

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

    def _execute_sqlite_fts_search(
        self,
        *,
        query: SearchDocumentsQuery,
        tenant_scope_spec: TenantScopeSpec,
        date_range_spec: DateRangeSpec,
        visibility_spec: VisibilitySpec | None,
        offset: int,
        safe_search_query: str,
    ) -> tuple[list[object], int]:
        filters = ["documents_fts MATCH :search_query"]
        params: dict[str, object] = {
            "search_query": safe_search_query,
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
        if (
            query.current_user.role != UserRole.SYSTEM_ADMIN
            and query.current_user.tenant_id is not None
        ):
            filters.append("documents_fts.tenant_id = :fts_tenant_id")
            params["fts_tenant_id"] = str(query.current_user.tenant_id)

        if visibility_spec is not None:
            vis_clauses, vis_params = visibility_spec.sql_clauses(
                visibility_col="d.visibility",
                status_col="d.status",
                company_subquery_col="d.id",
            )
            filters.extend(vis_clauses)
            params.update(vis_params)

        where_clause = " AND ".join(filters)
        bm25_expr = self._bm25_expression()
        docs_query = text(
            f"""
            SELECT d.*, {bm25_expr} as score
            FROM documents d
            JOIN documents_fts ON d.id = documents_fts.rowid
            WHERE {where_clause}
            ORDER BY score
            LIMIT :limit OFFSET :offset
            """
        )
        docs = self.db.execute(docs_query, params).fetchall()

        count_query = text(
            f"""
            SELECT COUNT(*) FROM documents d
            JOIN documents_fts ON d.id = documents_fts.rowid
            WHERE {where_clause}
            """
        )
        count_params = {k: v for k, v in params.items() if k not in {"limit", "offset"}}
        total = self.db.execute(count_query, count_params).scalar() or 0
        return docs, int(total)

    def _execute_postgres_tsv_search(
        self,
        *,
        query: SearchDocumentsQuery,
        tenant_scope_spec: TenantScopeSpec,
        date_range_spec: DateRangeSpec,
        visibility_spec: VisibilitySpec | None,
        offset: int,
        plain_search_query: str,
    ) -> tuple[list[object], int]:
        tsquery_expr = "websearch_to_tsquery('simple', :search_query)"
        filters = [f"{POSTGRES_SEARCH_VECTOR} @@ {tsquery_expr}"]
        params: dict[str, object] = {
            "search_query": plain_search_query,
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
        if visibility_spec is not None:
            vis_clauses, vis_params = visibility_spec.sql_clauses(
                visibility_col="d.visibility",
                status_col="d.status",
                company_subquery_col="d.id",
            )
            filters.extend(vis_clauses)
            params.update(vis_params)

        where_clause = " AND ".join(filters)
        rank_expr = f"ts_rank_cd({POSTGRES_SEARCH_VECTOR}, {tsquery_expr})"
        docs_query = text(
            f"""
            SELECT d.*, {rank_expr} as score
            FROM documents d
            WHERE {where_clause}
            ORDER BY score DESC, d.updated_at DESC
            LIMIT :limit OFFSET :offset
            """
        )
        docs = self.db.execute(docs_query, params).fetchall()

        count_query = text(
            f"""
            SELECT COUNT(*) FROM documents d
            WHERE {where_clause}
            """
        )
        count_params = {k: v for k, v in params.items() if k not in {"limit", "offset"}}
        total = self.db.execute(count_query, count_params).scalar() or 0
        return docs, int(total)

    def _execute_like_search(
        self,
        *,
        query: SearchDocumentsQuery,
        document_repository: DocumentRepository,
        tenant_scope_spec: TenantScopeSpec,
        date_range_spec: DateRangeSpec,
        visibility_spec: VisibilitySpec | None,
        offset: int,
        search_terms: list[str],
    ) -> tuple[list[object], int]:
        fallback_query = document_repository.query()
        if search_terms:
            per_term_clauses = []
            for term in search_terms:
                escaped_term = escape_sql_wildcards(term)
                per_term_clauses.append(
                    or_(
                        Document.title.ilike(f"%{escaped_term}%", escape="\\"),
                        Document.description.ilike(f"%{escaped_term}%", escape="\\"),
                        Document.document_number.ilike(f"%{escaped_term}%", escape="\\"),
                        Document.tags.ilike(f"%{escaped_term}%", escape="\\"),
                    )
                )
            fallback_query = fallback_query.filter(and_(*per_term_clauses))
        else:
            escaped_q = escape_sql_wildcards(query.q)
            fallback_query = fallback_query.filter(
                or_(
                    Document.title.ilike(f"%{escaped_q}%", escape="\\"),
                    Document.description.ilike(f"%{escaped_q}%", escape="\\"),
                )
            )
        fallback_query = tenant_scope_spec.apply(fallback_query, Document)
        if visibility_spec is not None:
            fallback_query = visibility_spec.apply(fallback_query, Document)
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
        return docs, int(total)

    def execute_search_documents(self, query: SearchDocumentsQuery) -> SearchDocumentsQueryResult:
        def load_projection() -> SearchDocumentsQueryResult:
            document_repository = DocumentRepository(self.db)
            tenant_scope_spec = TenantScopeSpec.for_user(query.current_user)
            date_range_spec = DateRangeSpec(date_from=query.date_from, date_to=query.date_to)
            visibility_spec = self._visibility_spec_for_user(query.current_user)
            offset = (query.page - 1) * query.page_size
            safe_search_query = build_safe_fts_query(query.q)
            plain_search_query = build_safe_plain_search_query(query.q)
            search_terms = _extract_search_terms(query.q)
            dialect_name = database_dialect_name(self.db)
            configured_mode = settings.SEARCH_BACKEND_MODE
            effective_mode = resolve_search_backend_mode(
                configured_mode,
                dialect_name=dialect_name,
            )

            if not search_terms:
                docs, total = self._execute_like_search(
                    query=query,
                    document_repository=document_repository,
                    tenant_scope_spec=tenant_scope_spec,
                    date_range_spec=date_range_spec,
                    visibility_spec=visibility_spec,
                    offset=offset,
                    search_terms=search_terms,
                )
                record_search_execution(effective_mode=SearchBackendMode.PORTABLE_LIKE.value)
            else:
                try:
                    if effective_mode == SearchBackendMode.SQLITE_FTS5:
                        docs, total = self._execute_sqlite_fts_search(
                            query=query,
                            tenant_scope_spec=tenant_scope_spec,
                            date_range_spec=date_range_spec,
                            visibility_spec=visibility_spec,
                            offset=offset,
                            safe_search_query=safe_search_query or plain_search_query or query.q,
                        )
                    elif effective_mode == SearchBackendMode.POSTGRES_TSV:
                        docs, total = self._execute_postgres_tsv_search(
                            query=query,
                            tenant_scope_spec=tenant_scope_spec,
                            date_range_spec=date_range_spec,
                            visibility_spec=visibility_spec,
                            offset=offset,
                            plain_search_query=plain_search_query or query.q,
                        )
                    else:
                        docs, total = self._execute_like_search(
                            query=query,
                            document_repository=document_repository,
                            tenant_scope_spec=tenant_scope_spec,
                            date_range_spec=date_range_spec,
                            visibility_spec=visibility_spec,
                            offset=offset,
                            search_terms=search_terms,
                        )
                    record_search_execution(effective_mode=effective_mode.value)
                except (OperationalError, ProgrammingError) as exc:
                    logger.warning(
                        "Search backend %s failed on %s; falling back to LIKE search",
                        effective_mode.value,
                        dialect_name,
                        exc_info=True,
                    )
                    record_degradation(
                        DegradationPolicy.COMPENSATING,
                        "search.documents",
                        exc,
                    )
                    record_search_degraded_fallback(
                        requested_mode=effective_mode.value,
                        fallback_mode=SearchBackendMode.PORTABLE_LIKE.value,
                        error=exc,
                    )
                    docs, total = self._execute_like_search(
                        query=query,
                        document_repository=document_repository,
                        tenant_scope_spec=tenant_scope_spec,
                        date_range_spec=date_range_spec,
                        visibility_spec=visibility_spec,
                        offset=offset,
                        search_terms=search_terms,
                    )
                    record_search_execution(effective_mode=SearchBackendMode.PORTABLE_LIKE.value)

            suggestions = self.execute_autocomplete(
                SearchAutocompleteQuery(q=query.q, limit=5, current_user=query.current_user)
            )
            return SearchDocumentsQueryResult(
                items=[self._build_read_model(row) for row in docs],
                total=int(total),
                query=query.q,
                suggestions=suggestions,
            )

        visibility_scope = self._visibility_cache_scope(query.current_user)
        return self._execute_cached(
            projection_name="documents",
            key_parts=(
                visibility_scope,
                query.q,
                query.category,
                query.date_from,
                query.date_to,
                query.page,
                query.page_size,
            ),
            loader=load_projection,
            ttl_seconds=30,
            validator=lambda payload: isinstance(payload, SearchDocumentsQueryResult),
        )

    def execute_autocomplete(self, query: SearchAutocompleteQuery) -> list[str]:
        return self._execute_cached(
            projection_name="autocomplete",
            key_parts=(
                self._visibility_cache_scope(query.current_user),
                query.q,
                query.limit,
            ),
            loader=lambda: self._load_autocomplete(query),
            ttl_seconds=30,
            validator=lambda payload: isinstance(payload, list)
            and all(isinstance(item, str) for item in payload),
        )

    def _load_autocomplete(self, query: SearchAutocompleteQuery) -> list[str]:
        # M-38: Escape wildcards in autocomplete query
        escaped_q = escape_sql_wildcards(query.q)
        document_repository = DocumentRepository(self.db)
        title_query = (
            document_repository.query()
            .with_entities(Document.title)
            .filter(Document.title.ilike(f"%{escaped_q}%", escape="\\"))
        )
        title_query = TenantScopeSpec.for_user(query.current_user).apply(title_query, Document)
        visibility_spec = self._visibility_spec_for_user(query.current_user)
        if visibility_spec is not None:
            title_query = visibility_spec.apply(title_query, Document)
        docs = title_query.limit(query.limit).all()
        return [doc.title for doc in docs]

    def execute_facets(self, query: SearchFacetsQuery) -> dict:
        return self._execute_cached(
            projection_name="facets",
            key_parts=(self._visibility_cache_scope(query.current_user),),
            loader=lambda: self._load_facets(query),
            ttl_seconds=30,
            validator=lambda payload: isinstance(payload, dict)
            and "categories" in payload
            and "statuses" in payload,
        )

    def _load_facets(self, query: SearchFacetsQuery) -> dict:
        tenant_scope_spec = TenantScopeSpec.for_user(query.current_user)
        visibility_spec = self._visibility_spec_for_user(query.current_user)

        category_query = self.db.query(Document.category, text("COUNT(*)"))
        category_query = tenant_scope_spec.apply(category_query, Document)
        if visibility_spec is not None:
            category_query = visibility_spec.apply(category_query, Document)
        categories = category_query.group_by(Document.category).all()

        status_query = self.db.query(Document.status, text("COUNT(*)"))
        status_query = tenant_scope_spec.apply(status_query, Document)
        if visibility_spec is not None:
            status_query = visibility_spec.apply(status_query, Document)
        statuses = status_query.group_by(Document.status).all()

        return {
            "categories": [{"name": c[0] or "Uncategorized", "count": c[1]} for c in categories],
            "statuses": [
                {"name": s[0].value if s[0] else "unknown", "count": s[1]} for s in statuses
            ],
        }

    def execute_list_saved_searches(self, query: ListSavedSearchesQuery) -> list[SavedSearch]:
        return (
            self.db.query(SavedSearch)
            .filter(SavedSearch.user_id == query.user_id)
            .order_by(SavedSearch.created_at.desc())
            .all()
        )
