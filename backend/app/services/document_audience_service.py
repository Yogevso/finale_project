"""Audience and company-assignment helpers for documents."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from time import monotonic
from typing import Optional

from sqlalchemy.orm import Session

from app.dependencies.tenant import TenantContext
from app.domain.specifications import DocumentVisibilityCompanyAssignmentSpec
from app.errors import PermissionDeniedError, ValidationError
from app.errors.audience_errors import AudienceErrorCode
from app.models import DocumentVisibility, Tenant

COMPANY_LOOKUP_CACHE_TTL_SECONDS = 30
COMPANY_LOOKUP_CACHE_MAX_ENTRIES = 1024


@dataclass(slots=True, frozen=True)
class CompanyLookupSnapshot:
    """Minimal cached company lookup data used by assignment validation."""

    id: int
    name: str
    slug: str
    is_active: bool


@dataclass(slots=True)
class _CompanyLookupCacheEntry:
    snapshot: CompanyLookupSnapshot
    expires_at: float


@dataclass(slots=True, frozen=True)
class CompanyLookupCacheMetrics:
    """Operational metrics for the shared company lookup cache."""

    entry_count: int
    max_entries: int
    ttl_seconds: int
    hits: int
    misses: int
    expired: int
    writes: int
    evictions: int
    clears: int


@dataclass(slots=True)
class AudienceReconciliationResult:
    active_companies: list[Tenant]
    stale_companies: list[dict[str, object]]
    visibility: DocumentVisibility


class CompanyLookupCache:
    """Thread-safe in-memory cache for tenant-scoped company lookups."""

    def __init__(
        self,
        *,
        ttl_seconds: int,
        max_entries: int,
    ) -> None:
        self.ttl_seconds = max(1, int(ttl_seconds))
        self.max_entries = max(1, int(max_entries))
        self._entries: dict[tuple[int | None, int], _CompanyLookupCacheEntry] = {}
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        self._expired = 0
        self._writes = 0
        self._evictions = 0
        self._clears = 0

    def get(self, company_id: int, *, tenant_id: int | None = None) -> CompanyLookupSnapshot | None:
        if tenant_id is None:
            return None

        key = (tenant_id, company_id)
        now = monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.expires_at <= now:
                self._entries.pop(key, None)
                self._misses += 1
                self._expired += 1
                return None
            self._hits += 1
            return entry.snapshot

    def set(self, snapshot: CompanyLookupSnapshot, *, tenant_id: int | None = None) -> None:
        if tenant_id is None:
            return

        key = (tenant_id, snapshot.id)
        now = monotonic()
        with self._lock:
            self._entries[key] = _CompanyLookupCacheEntry(
                snapshot=snapshot,
                expires_at=now + self.ttl_seconds,
            )
            self._writes += 1
            self._evict_if_needed()

    def clear(self, *, reset_metrics: bool = False) -> None:
        with self._lock:
            self._entries.clear()
            self._clears += 1
            if reset_metrics:
                self._hits = 0
                self._misses = 0
                self._expired = 0
                self._writes = 0
                self._evictions = 0
                self._clears = 0

    def metrics(self) -> CompanyLookupCacheMetrics:
        with self._lock:
            return CompanyLookupCacheMetrics(
                entry_count=len(self._entries),
                max_entries=self.max_entries,
                ttl_seconds=self.ttl_seconds,
                hits=self._hits,
                misses=self._misses,
                expired=self._expired,
                writes=self._writes,
                evictions=self._evictions,
                clears=self._clears,
            )

    def _evict_if_needed(self) -> None:
        if len(self._entries) <= self.max_entries:
            return

        excess = len(self._entries) - self.max_entries
        for cache_key in list(self._entries)[:excess]:
            self._entries.pop(cache_key, None)
            self._evictions += 1


_company_cache = CompanyLookupCache(
    ttl_seconds=COMPANY_LOOKUP_CACHE_TTL_SECONDS,
    max_entries=COMPANY_LOOKUP_CACHE_MAX_ENTRIES,
)


def get_company_lookup_cache_metrics() -> CompanyLookupCacheMetrics:
    """Return a point-in-time metrics snapshot for the shared company cache."""

    return _company_cache.metrics()


def _cache_get(company_id: int, tenant_id: int | None = None) -> CompanyLookupSnapshot | None:
    return _company_cache.get(company_id, tenant_id=tenant_id)


def _cache_set(snapshot: CompanyLookupSnapshot, tenant_id: int | None = None) -> None:
    _company_cache.set(snapshot, tenant_id=tenant_id)


class DocumentAudienceService:
    """Resolve and validate company assignments for documents."""

    _company_visibility_assignment_spec = DocumentVisibilityCompanyAssignmentSpec()

    def __init__(self, db: Session, tenant_ctx: TenantContext | None = None):
        self.db = db
        self.tenant_ctx = tenant_ctx

    @staticmethod
    def normalize_company_ids(company_ids: Optional[list[int]]) -> list[int]:
        if not company_ids:
            return []

        normalized_ids = list(dict.fromkeys(company_ids))
        if any(company_id <= 0 for company_id in normalized_ids):
            raise ValidationError(
                "Company IDs must be positive integers",
                error_code=AudienceErrorCode.AUDIENCE_002.value,
            )
        return normalized_ids

    def validate_company_visibility_assignment(
        self,
        *,
        visibility: DocumentVisibility,
        company_ids: list[int],
    ) -> None:
        self._company_visibility_assignment_spec.assert_satisfied(
            visibility=visibility,
            company_ids=company_ids,
        )

    def _enforce_assignment_tenant_scope(self, company_ids: list[int]) -> None:
        if not company_ids:
            return
        if not self.tenant_ctx or self.tenant_ctx.is_system_admin:
            return

        tenant_id = self.tenant_ctx.tenant_id
        if tenant_id is None:
            return

        foreign_ids = [company_id for company_id in company_ids if company_id != tenant_id]
        if foreign_ids:
            raise PermissionDeniedError(
                "Cannot assign companies outside your tenant scope",
                error_code=AudienceErrorCode.AUDIENCE_010.value,
            )

    def lookup_company_snapshots(self, company_ids: list[int]) -> dict[int, CompanyLookupSnapshot]:
        """Resolve minimal company metadata with a short-lived LRU cache."""
        tenant_id = self.tenant_ctx.tenant_id if self.tenant_ctx else None
        snapshots: dict[int, CompanyLookupSnapshot] = {}
        missing_ids: list[int] = []

        for company_id in company_ids:
            cached = _cache_get(company_id, tenant_id=tenant_id)
            if cached is None:
                missing_ids.append(company_id)
            else:
                snapshots[company_id] = cached

        if missing_ids:
            rows = (
                self.db.query(Tenant.id, Tenant.name, Tenant.slug, Tenant.is_active)
                .filter(Tenant.id.in_(missing_ids))
                .all()
            )
            for row in rows:
                snapshot = CompanyLookupSnapshot(
                    id=int(row.id),
                    name=str(row.name),
                    slug=str(row.slug),
                    is_active=bool(row.is_active),
                )
                snapshots[snapshot.id] = snapshot
                _cache_set(snapshot, tenant_id=tenant_id)

        return snapshots

    def resolve_assigned_companies(self, company_ids: list[int]) -> list[Tenant]:
        if not company_ids:
            return []

        self._enforce_assignment_tenant_scope(company_ids)

        companies = self.db.query(Tenant).filter(Tenant.id.in_(company_ids)).all()
        company_by_id = {company.id: company for company in companies}
        missing_ids = [company_id for company_id in company_ids if company_id not in company_by_id]
        if missing_ids:
            raise ValidationError(
                "Some company IDs are invalid",
                error_code=AudienceErrorCode.AUDIENCE_002.value,
            )

        inactive_ids = [
            company_id for company_id in company_ids if not company_by_id[company_id].is_active
        ]
        if inactive_ids:
            raise ValidationError(
                "Inactive companies cannot be assigned to documents",
                error_code=AudienceErrorCode.AUDIENCE_008.value,
            )

        return [company_by_id[company_id] for company_id in company_ids]

    def reconcile_active_companies(
        self,
        assigned_companies: list[Tenant] | None,
        visibility: DocumentVisibility,
    ) -> AudienceReconciliationResult:
        original_company_ids = [company.id for company in (assigned_companies or [])]
        active_companies: list[Tenant] = []
        stale_companies: list[dict[str, object]] = []

        if original_company_ids:
            tenants = self.db.query(Tenant).filter(Tenant.id.in_(original_company_ids)).all()
            tenant_map = {tenant.id: tenant for tenant in tenants}

            for company_id in original_company_ids:
                tenant = tenant_map.get(company_id)
                if tenant is None:
                    stale_companies.append({"id": company_id, "reason": "deleted"})
                elif not tenant.is_active:
                    stale_companies.append(
                        {"id": company_id, "name": tenant.name, "reason": "deactivated"}
                    )
                else:
                    active_companies.append(tenant)

        resolved_visibility = visibility
        if visibility == DocumentVisibility.COMPANY and not active_companies:
            resolved_visibility = DocumentVisibility.INTERNAL

        return AudienceReconciliationResult(
            active_companies=active_companies,
            stale_companies=stale_companies,
            visibility=resolved_visibility,
        )
