"""Reusable query/access specifications for filters and role gates."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import and_, false, or_
from sqlalchemy.orm import Query

from app.models import Document, DocumentStatus, DocumentVisibility, User, UserRole


def _coerce_role(role: UserRole | str) -> UserRole:
    if isinstance(role, UserRole):
        return role
    return UserRole(role)


@dataclass(frozen=True)
class TenantScopeSpec:
    """Tenant-scoping filter for user-bound document queries."""

    tenant_id: int | None
    is_system_admin: bool

    @classmethod
    def for_user(cls, user: User) -> TenantScopeSpec:
        role = _coerce_role(user.role)
        return cls(
            tenant_id=user.tenant_id,
            is_system_admin=role == UserRole.SYSTEM_ADMIN,
        )

    def apply(
        self,
        query: Query,
        model: type[Document],
        *,
        tenant_column: str = "tenant_id",
    ) -> Query:
        if self.is_system_admin:
            return query
        if not hasattr(model, tenant_column):
            return query
        column = getattr(model, tenant_column)
        if self.tenant_id is None:
            return query.filter(column.is_(None))
        return query.filter(column == self.tenant_id)

    def sql_clause(
        self,
        *,
        column_expr: str,
        param_name: str = "tenant_id",
    ) -> tuple[str | None, dict[str, object]]:
        if self.is_system_admin:
            return None, {}
        if self.tenant_id is None:
            return f"{column_expr} IS NULL", {}
        return f"{column_expr} = :{param_name}", {param_name: self.tenant_id}


@dataclass(frozen=True)
class DateRangeSpec:
    """Date-range filter that can be applied to ORM and SQL text queries."""

    date_from: datetime | None = None
    date_to: datetime | None = None

    def apply(self, query: Query, column: Any) -> Query:
        if self.date_from is not None:
            query = query.filter(column >= self.date_from)
        if self.date_to is not None:
            query = query.filter(column <= self.date_to)
        return query

    def sql_clauses(
        self,
        *,
        column_expr: str,
        from_param: str = "date_from",
        to_param: str = "date_to",
    ) -> tuple[list[str], dict[str, object]]:
        clauses: list[str] = []
        params: dict[str, object] = {}
        if self.date_from is not None:
            clauses.append(f"{column_expr} >= :{from_param}")
            params[from_param] = self.date_from
        if self.date_to is not None:
            clauses.append(f"{column_expr} <= :{to_param}")
            params[to_param] = self.date_to
        return clauses, params


@dataclass(frozen=True)
class RoleAccessSpec:
    """Role-membership gate for endpoint/service-level checks."""

    allowed_roles: frozenset[UserRole] = field(default_factory=frozenset)
    require_active: bool = True

    @classmethod
    def customer_only(cls) -> RoleAccessSpec:
        return cls(allowed_roles=frozenset({UserRole.CUSTOMER}))

    def is_satisfied_by(self, user: User | None) -> bool:
        if user is None:
            return False
        if self.require_active and not user.is_active:
            return False
        return _coerce_role(user.role) in self.allowed_roles


@dataclass(frozen=True)
class VisibilitySpec:
    """Composable document visibility rules for query and runtime checks."""

    allowed_visibilities: frozenset[DocumentVisibility]
    company_tenant_id: int | None = None
    required_statuses: frozenset[DocumentStatus] | None = None

    @classmethod
    def customer_portal(cls, customer_tenant_id: int | None) -> VisibilitySpec:
        return cls(
            allowed_visibilities=frozenset(
                {
                    DocumentVisibility.PUBLIC,
                    DocumentVisibility.COMPANY,
                }
            ),
            company_tenant_id=customer_tenant_id,
            required_statuses=frozenset({DocumentStatus.ACTIVE}),
        )

    @classmethod
    def management(cls) -> VisibilitySpec:
        """All visibility levels, active documents only – for internal staff search."""
        return cls(
            allowed_visibilities=frozenset(
                {
                    DocumentVisibility.PUBLIC,
                    DocumentVisibility.INTERNAL,
                    DocumentVisibility.COMPANY,
                }
            ),
            required_statuses=frozenset({DocumentStatus.ACTIVE}),
        )

    @classmethod
    def public_only(cls) -> VisibilitySpec:
        """Public + active – for anonymous/public search and sitemap."""
        return cls(
            allowed_visibilities=frozenset({DocumentVisibility.PUBLIC}),
            required_statuses=frozenset({DocumentStatus.ACTIVE}),
        )

    def is_satisfied_by(self, document: Document) -> bool:
        if self.required_statuses and document.status not in self.required_statuses:
            return False

        if document.visibility == DocumentVisibility.PUBLIC:
            return DocumentVisibility.PUBLIC in self.allowed_visibilities

        if document.visibility == DocumentVisibility.INTERNAL:
            return DocumentVisibility.INTERNAL in self.allowed_visibilities

        if document.visibility == DocumentVisibility.COMPANY:
            if DocumentVisibility.COMPANY not in self.allowed_visibilities:
                return False
            if self.company_tenant_id is None:
                return False
            return any(company.id == self.company_tenant_id for company in document.assigned_companies)

        return False

    def apply(self, query: Query, model: type[Document] = Document) -> Query:
        if self.required_statuses:
            query = query.filter(model.status.in_(tuple(self.required_statuses)))

        conditions = []
        if DocumentVisibility.PUBLIC in self.allowed_visibilities:
            conditions.append(model.visibility == DocumentVisibility.PUBLIC)

        if DocumentVisibility.INTERNAL in self.allowed_visibilities:
            conditions.append(model.visibility == DocumentVisibility.INTERNAL)

        if (
            DocumentVisibility.COMPANY in self.allowed_visibilities
            and self.company_tenant_id is not None
        ):
            conditions.append(
                and_(
                    model.visibility == DocumentVisibility.COMPANY,
                    model.assigned_companies.any(id=self.company_tenant_id),
                )
            )

        if not conditions:
            return query.filter(false())
        if len(conditions) == 1:
            return query.filter(conditions[0])
        return query.filter(or_(*conditions))

    def sql_clauses(
        self,
        *,
        visibility_col: str = "d.visibility",
        status_col: str = "d.status",
        company_subquery_col: str = "d.id",
    ) -> tuple[list[str], dict[str, object]]:
        """Return raw-SQL WHERE fragments + bind params for FTS5 / text queries.

        The returned clauses should be ANDed into the caller's WHERE.
        """
        clauses: list[str] = []
        params: dict[str, object] = {}

        # Status filter
        if self.required_statuses:
            status_values = [s.value for s in self.required_statuses]
            if len(status_values) == 1:
                clauses.append(f"{status_col} = :vis_status")
                params["vis_status"] = status_values[0]
            else:
                placeholders = ", ".join(
                    f":vis_status_{i}" for i in range(len(status_values))
                )
                clauses.append(f"{status_col} IN ({placeholders})")
                for i, v in enumerate(status_values):
                    params[f"vis_status_{i}"] = v

        # Visibility filter
        vis_parts: list[str] = []
        if DocumentVisibility.PUBLIC in self.allowed_visibilities:
            vis_parts.append(f"{visibility_col} = :vis_public")
            params["vis_public"] = DocumentVisibility.PUBLIC.value

        if DocumentVisibility.INTERNAL in self.allowed_visibilities:
            vis_parts.append(f"{visibility_col} = :vis_internal")
            params["vis_internal"] = DocumentVisibility.INTERNAL.value

        if (
            DocumentVisibility.COMPANY in self.allowed_visibilities
            and self.company_tenant_id is not None
        ):
            vis_parts.append(
                f"({visibility_col} = :vis_company AND {company_subquery_col} IN "
                f"(SELECT document_id FROM document_company_assignments "
                f"WHERE company_id = :vis_company_tid))"
            )
            params["vis_company"] = DocumentVisibility.COMPANY.value
            params["vis_company_tid"] = self.company_tenant_id

        if vis_parts:
            clauses.append("(" + " OR ".join(vis_parts) + ")")
        elif not vis_parts and self.allowed_visibilities:
            # All visibilities allowed but none matched the branch conditions
            pass
        else:
            # Empty allowed_visibilities → match nothing
            clauses.append("1 = 0")

        return clauses, params
