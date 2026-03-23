"""Document Service"""

import json
import logging
import re
import threading
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from time import monotonic
from typing import List, Optional

from sqlalchemy import case, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies.tenant import TenantContext
from app.domain.aggregates import DocumentAggregate
from app.domain.events import CompanyAssignmentsUpdated, InProcessDomainEventDispatcher
from app.domain.factories import DocumentFactory
from app.domain.specifications import DocumentVisibilityCompanyAssignmentSpec
from app.domain.value_objects import DocumentNumber
from app.errors import InvalidStateError, NotFoundError, PermissionDeniedError, ValidationError
from app.errors.audience_errors import AudienceErrorCode
from app.models import (
    ActionType,
    AudienceEventType,
    AuditLog,
    Document,
    DocumentNumberSequence,
    DocumentStatus,
    DocumentVisibility,
    DocumentWatcher,
    NotificationType,
    Platform,
    Tenant,
    Topic,
    User,
    UserRole,
    Version,
)
from app.application.policies.access_policies import DocumentAccessPolicy
from app.schemas import DocumentCreate, DocumentUpdate
from app.services.base_service import TenantAwareService
from app.services.notification_service import NotificationService
from app.services.outbox import build_outbox_event_dispatcher
from app.services.uow import UnitOfWork
from app.services.audit_helper import write_audit_log
from app.utils.audience_audit_signing import sign_payload
from app.utils.concurrency import ensure_if_match_matches
from app.utils.topic_normalization import build_topic_lookup, normalize_topic_to_slug

logger = logging.getLogger(__name__)
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


# Module-level TTL cache shared across requests (thread-safe).
_company_cache_lock = threading.Lock()
_company_cache: dict[tuple[int | None, int], _CompanyLookupCacheEntry] = {}


def _cache_get(company_id: int, tenant_id: int | None = None) -> CompanyLookupSnapshot | None:
    key = (tenant_id, company_id)
    now = monotonic()
    with _company_cache_lock:
        entry = _company_cache.get(key)
        if entry is None:
            return None
        if entry.expires_at <= now:
            _company_cache.pop(key, None)
            return None
        return entry.snapshot


def _cache_set(snapshot: CompanyLookupSnapshot, tenant_id: int | None = None) -> None:
    key = (tenant_id, snapshot.id)
    now = monotonic()
    with _company_cache_lock:
        _company_cache[key] = _CompanyLookupCacheEntry(
            snapshot=snapshot,
            expires_at=now + COMPANY_LOOKUP_CACHE_TTL_SECONDS,
        )
        # Evict oldest entries when over capacity
        if len(_company_cache) > COMPANY_LOOKUP_CACHE_MAX_ENTRIES:
            excess = len(_company_cache) - COMPANY_LOOKUP_CACHE_MAX_ENTRIES
            for k in list(_company_cache)[:excess]:
                _company_cache.pop(k, None)


class DocumentService(TenantAwareService[Document]):
    """Document CRUD service with multi-tenancy support"""

    model = Document
    _company_visibility_assignment_spec = DocumentVisibilityCompanyAssignmentSpec()

    def __init__(
        self,
        db: Session,
        tenant_ctx: Optional[TenantContext] = None,
        *,
        chat_db: Session | None = None,
        event_dispatcher: InProcessDomainEventDispatcher | None = None,
    ):
        super().__init__(db, tenant_ctx)
        self.event_dispatcher = event_dispatcher or build_outbox_event_dispatcher(db)
        self.notification_service = NotificationService(db, chat_db=chat_db)

    def _base_query(self):
        """Base query with tenant filtering applied"""
        return super()._base_query(Document)

    def _verify_access(self, document: Document) -> None:
        """Verify current user can access this document"""
        if not document:
            raise NotFoundError("Document not found")

        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            if document.tenant_id != self.tenant_ctx.tenant_id:
                raise NotFoundError("Document not found")

    _access_policy = DocumentAccessPolicy()
    _WRITE_ROLES = {UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER, UserRole.EDITOR}
    # Route layer enforces MANAGER+ for delete endpoints; service layer
    # allows EDITOR+ so internal callers (e.g. upload-workflow compensation)
    # can clean up documents the user just created.
    _DELETE_ROLES = {UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER, UserRole.EDITOR}

    def _verify_write_access(self, document: Document, user: User) -> None:
        """Verify user can modify this document (tenant + role + policy check)."""
        self._verify_access(document)
        if user.role not in self._WRITE_ROLES:
            raise PermissionDeniedError("Insufficient permissions to modify documents")
        if not self._access_policy.can_edit_document(user, document, has_edit_permission=True):
            raise PermissionDeniedError("Document access denied by policy")

    def _verify_delete_access(self, document: Document, user: User) -> None:
        """Verify user can delete this document (requires MANAGER+)."""
        self._verify_access(document)
        if user.role not in self._DELETE_ROLES:
            raise PermissionDeniedError("Insufficient permissions to delete documents")
        if not self._access_policy.can_delete_document(user, document, has_delete_permission=True):
            raise PermissionDeniedError("Document access denied by policy")

    def _discover_max_existing_suffix(self, prefix: str) -> int:
        existing = (
            self.db.query(Document.document_number)
            .filter(Document.document_number.like(f"{prefix}-%"))
            .all()
        )
        max_suffix = 0
        for (document_number,) in existing:
            suffix = DocumentNumber.extract_sequence_suffix(document_number, prefix)
            if suffix is not None and suffix > max_suffix:
                max_suffix = suffix
        return max_suffix

    def _insert_sequence_row_if_missing(self, date_key: str, seed_sequence: int) -> None:
        dialect_name = self.db.bind.dialect.name if self.db.bind else ""
        values = {"date_key": date_key, "next_value": seed_sequence}

        if dialect_name == "sqlite":
            stmt = sqlite_insert(DocumentNumberSequence).values(**values)
            self.db.execute(stmt.on_conflict_do_nothing(index_elements=["date_key"]))
            return

        if dialect_name == "postgresql":
            stmt = postgresql_insert(DocumentNumberSequence).values(**values)
            self.db.execute(stmt.on_conflict_do_nothing(index_elements=["date_key"]))
            return

        try:
            with self.db.begin_nested():
                self.db.add(DocumentNumberSequence(**values))
                self.db.flush()
        except IntegrityError:
            pass

    def _reserve_document_sequence(self, date_key: str) -> int:
        # Use RETURNING clause to make increment and retrieval atomic,
        # preventing race conditions where concurrent transactions get same number.
        # Works on PostgreSQL and SQLite 3.35+.
        update_stmt = (
            update(DocumentNumberSequence)
            .where(DocumentNumberSequence.date_key == date_key)
            .values(
                next_value=DocumentNumberSequence.next_value + 1,
                updated_at=datetime.utcnow(),
            )
            .returning(DocumentNumberSequence.next_value)
        )
        result = self.db.execute(update_stmt)
        row = result.fetchone()
        if row is None:
            raise RuntimeError("Failed to reserve a document number sequence value")
        return int(row[0])

    def generate_document_number(self) -> str:
        """Generate unique document number (DOC-YYYYMMDD-XXXX)"""
        date_key = datetime.utcnow().strftime("%Y%m%d")
        prefix = DocumentNumber.prefix_for_date_key(date_key)

        if self.db.get(DocumentNumberSequence, date_key) is None:
            seed_sequence = self._discover_max_existing_suffix(prefix)
            self._insert_sequence_row_if_missing(date_key, seed_sequence)

        next_sequence = self._reserve_document_sequence(date_key)
        return str(DocumentNumber.from_date_key(date_key, next_sequence))

    @staticmethod
    def _slugify_platform(name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower())
        slug = slug.strip("-")
        return slug or "platform"

    @staticmethod
    def _normalize_platform_name(name: Optional[str]) -> str:
        if not name or not name.strip():
            return "Unspecified"
        return name.strip()

    @staticmethod
    def _require_platform_selection(
        *, platform_name: Optional[str] = None, platform_id: Optional[int] = None
    ) -> None:
        if platform_id is not None:
            return
        if platform_name is not None and platform_name.strip():
            return
        raise ValidationError("Platform is required")

    def _normalize_topic(self, raw_topic: Optional[str]) -> Optional[str]:
        normalized = normalize_topic_to_slug(raw_topic)
        if normalized is None:
            return None

        topics = self.db.query(Topic).all()
        if not topics:
            return normalized

        topic_lookup = build_topic_lookup(topics)
        return normalize_topic_to_slug(raw_topic, topic_lookup) or normalized

    def _get_or_create_platform(
        self, platform_name: Optional[str] = None, platform_id: Optional[int] = None
    ) -> Platform:
        if platform_id is not None:
            platform = self.db.query(Platform).filter(Platform.id == platform_id).first()
            if not platform:
                raise NotFoundError(f"Platform {platform_id} not found")
            return platform

        normalized_name = self._normalize_platform_name(platform_name)
        platform = (
            self.db.query(Platform)
            .filter(func.lower(Platform.name) == normalized_name.lower())
            .first()
        )
        if platform:
            return platform

        base_slug = self._slugify_platform(normalized_name)
        slug = base_slug
        suffix = 2
        while self.db.query(Platform).filter(Platform.slug == slug).first():
            slug = f"{base_slug}-{suffix}"
            suffix += 1

        platform = Platform(name=normalized_name, slug=slug)
        self.db.add(platform)
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            # Race condition: another request created this slug concurrently — retry lookup
            existing = (
                self.db.query(Platform)
                .filter(func.lower(Platform.name) == normalized_name.lower())
                .first()
            )
            if existing:
                return existing
            raise
        return platform

    @staticmethod
    def _normalize_company_ids(company_ids: Optional[List[int]]) -> List[int]:
        if not company_ids:
            return []

        normalized_ids = list(dict.fromkeys(company_ids))
        if any(company_id <= 0 for company_id in normalized_ids):
            raise ValidationError(
                "Company IDs must be positive integers",
                error_code=AudienceErrorCode.AUDIENCE_002.value,
            )
        return normalized_ids

    def _enforce_assignment_tenant_scope(self, company_ids: List[int]) -> None:
        """
        Prevent tenant-scoped users from assigning foreign company IDs.

        System admins and unscoped internal users keep existing behavior.
        """
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

    def _lookup_company_snapshots(self, company_ids: List[int]) -> dict[int, CompanyLookupSnapshot]:
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

    def _resolve_assigned_companies(self, company_ids: List[int]) -> List[Tenant]:
        if not company_ids:
            return []

        self._enforce_assignment_tenant_scope(company_ids)
        snapshots_by_id = self._lookup_company_snapshots(company_ids)
        missing_ids = [company_id for company_id in company_ids if company_id not in snapshots_by_id]
        if missing_ids:
            raise ValidationError(
                "Some company IDs are invalid",
                error_code=AudienceErrorCode.AUDIENCE_002.value,
            )

        inactive_ids = [
            company_id
            for company_id in company_ids
            if not snapshots_by_id[company_id].is_active
        ]
        if inactive_ids:
            raise ValidationError(
                "Inactive companies cannot be assigned to documents",
                error_code=AudienceErrorCode.AUDIENCE_008.value,
            )

        companies = self.db.query(Tenant).filter(Tenant.id.in_(company_ids)).all()
        company_by_id = {company.id: company for company in companies}
        missing_object_ids = [company_id for company_id in company_ids if company_id not in company_by_id]
        if missing_object_ids:
            raise ValidationError(
                "Some company IDs are invalid",
                error_code=AudienceErrorCode.AUDIENCE_002.value,
            )
        return [company_by_id[company_id] for company_id in company_ids]

    def _validate_company_visibility_assignment(
        self,
        *,
        visibility: DocumentVisibility,
        company_ids: List[int],
    ) -> None:
        self._company_visibility_assignment_spec.assert_satisfied(
            visibility=visibility,
            company_ids=company_ids,
        )

    def create_document(self, document_data: DocumentCreate, user: User) -> Document:
        """Create a new document (requires EDITOR role or above)."""
        if user.role not in self._WRITE_ROLES:
            raise PermissionDeniedError("Insufficient permissions to create documents")
        normalized_company_ids = self._normalize_company_ids(document_data.company_ids)
        self._validate_company_visibility_assignment(
            visibility=document_data.visibility,
            company_ids=normalized_company_ids,
        )
        assigned_companies = self._resolve_assigned_companies(normalized_company_ids)

        # Use provided document number or generate one
        if document_data.document_number:
            # document_number is globally unique
            existing = (
                self.db.query(Document)
                .filter(Document.document_number == document_data.document_number)
                .first()
            )
            if existing:
                raise ValidationError("Document ID already exists")
            document_number = document_data.document_number
        else:
            document_number = self.generate_document_number()

        # Get tenant_id from context or user
        tenant_id = None
        if self.tenant_ctx:
            tenant_id = self.tenant_ctx.tenant_id
        elif user.tenant_id:
            tenant_id = user.tenant_id

        parent_id = document_data.parent_id
        if parent_id:
            parent = self._base_query().filter(Document.id == parent_id).first()
            if not parent:
                raise NotFoundError("Parent document not found")
            # Task 193: carry-over audience from parent when duplicating.
            # If the caller didn't explicitly set visibility (left default INTERNAL),
            # inherit from the parent.
            if document_data.visibility == DocumentVisibility.INTERNAL and parent.visibility != DocumentVisibility.INTERNAL:
                document_data = document_data.model_copy(
                    update={"visibility": parent.visibility}
                )
            # Inherit company assignments if the caller didn't specify any.
            if not normalized_company_ids and parent.assigned_companies:
                parent_company_ids = [c.id for c in parent.assigned_companies]
                normalized_company_ids = self._normalize_company_ids(parent_company_ids)
                assigned_companies = self._resolve_assigned_companies(normalized_company_ids)
            if document_data.platform_id is None and not (document_data.platform and document_data.platform.strip()):
                document_data = document_data.model_copy(
                    update={"platform": parent.platform, "platform_id": parent.platform_id}
                )
            # Re-validate after carry-over
            self._validate_company_visibility_assignment(
                visibility=document_data.visibility,
                company_ids=normalized_company_ids,
            )

        self._require_platform_selection(
            platform_name=document_data.platform,
            platform_id=document_data.platform_id,
        )

        # Create document with retry in case of document_number collision
        attempts = 0
        while True:
            attempts += 1
            try:
                with UnitOfWork(self.db) as uow:
                    platform = self._get_or_create_platform(
                        platform_name=document_data.platform, platform_id=document_data.platform_id
                    )
                    document = DocumentFactory.create_document(
                        title=document_data.title,
                        document_number=document_number,
                        description=document_data.description,
                        version_label=document_data.version_label,
                        status=document_data.status,
                        visibility=document_data.visibility,
                        category=document_data.category,
                        topic=self._normalize_topic(document_data.topic),
                        platform_name=platform.name,
                        platform_id=platform.id,
                        release_branch=document_data.release_branch,
                        tags=document_data.tags,
                        due_date=document_data.due_date,
                        created_by=user.id,
                        tenant_id=tenant_id,
                        parent_id=parent_id,
                    )
                    self.db.add(document)
                    uow.flush()

                    if assigned_companies:
                        document.assigned_companies = assigned_companies

                    # Create initial version placeholder. Real content is managed via explicit
                    # version edits/uploads, not the document description metadata field.
                    version = DocumentFactory.create_initial_version(
                        document_id=document.id,
                        created_by=user.id,
                    )
                    self.db.add(version)

                    audit = DocumentFactory.create_creation_audit(
                        user_id=user.id,
                        document_id=document.id,
                        title=document.title,
                    )
                    self.db.add(audit)

                self.db.refresh(document)
                return document
            except IntegrityError as exc:
                if (
                    (
                        "documents.document_number" in str(exc)
                        or "UNIQUE constraint failed: documents.document_number" in str(exc)
                    )
                    and not document_data.document_number
                    and attempts < 5
                ):
                    document_number = self.generate_document_number()
                    continue
                raise

    def get_document(self, document_id: int) -> Optional[Document]:
        """Get document by ID with tenant filtering"""
        document = self._base_query().filter(Document.id == document_id).first()
        return document

    def get_watch_status(self, document_id: int, user: User) -> bool:
        """Return whether the user follows the document."""
        document = self.get_document(document_id)
        self._verify_access(document)
        return (
            self.db.query(DocumentWatcher)
            .filter(
                DocumentWatcher.document_id == document_id,
                DocumentWatcher.user_id == user.id,
            )
            .first()
            is not None
        )

    def watch_document(self, document_id: int, user: User) -> DocumentWatcher:
        """Follow a document to receive notifications about future updates."""
        document = self.get_document(document_id)
        self._verify_access(document)

        existing = (
            self.db.query(DocumentWatcher)
            .filter(
                DocumentWatcher.document_id == document_id,
                DocumentWatcher.user_id == user.id,
            )
            .first()
        )
        if existing:
            return existing

        watcher = DocumentWatcher(document_id=document_id, user_id=user.id)
        with UnitOfWork(self.db):
            self.db.add(watcher)

        self.db.refresh(watcher)
        return watcher

    def unwatch_document(self, document_id: int, user: User) -> None:
        """Stop following a document."""
        document = self.get_document(document_id)
        self._verify_access(document)

        watcher = (
            self.db.query(DocumentWatcher)
            .filter(
                DocumentWatcher.document_id == document_id,
                DocumentWatcher.user_id == user.id,
            )
            .first()
        )
        if watcher is None:
            return

        with UnitOfWork(self.db):
            self.db.delete(watcher)

    def get_documents(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[DocumentStatus] = None,
        visibility: Optional[DocumentVisibility] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        company_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = "desc",
    ) -> tuple[List[Document], int]:
        """Get list of documents with filters, pagination, and tenant filtering"""
        query = self._base_query()

        # Apply filters
        if status:
            query = query.filter(Document.status == status)

        if visibility:
            query = query.filter(Document.visibility == visibility)

        if category:
            query = query.filter(Document.category == category)

        if company_id:
            query = query.filter(Document.assigned_companies.any(Tenant.id == company_id))

        if date_from:
            start_dt = datetime.combine(date_from, datetime.min.time())
            query = query.filter(Document.created_at >= start_dt)

        if date_to:
            end_dt = datetime.combine(date_to + timedelta(days=1), datetime.min.time())
            query = query.filter(Document.created_at < end_dt)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Document.title.ilike(search_pattern),
                    Document.description.ilike(search_pattern),
                    Document.document_number.ilike(search_pattern),
                    Document.tags.ilike(search_pattern),
                )
            )

        # Get total count
        total = query.count()

        # Apply sorting
        allowed_sort_fields = {"title", "created_at", "updated_at", "status", "category"}
        sort_column = Document.created_at  # default
        if sort_by and sort_by in allowed_sort_fields:
            sort_column = getattr(Document, sort_by)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # Apply pagination
        documents = query.offset(skip).limit(limit).all()

        return documents, total

    @staticmethod
    def _normalize_title_for_similarity(value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", " ", value.strip().lower())
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized

    @staticmethod
    def _levenshtein_distance(left: str, right: str) -> int:
        if left == right:
            return 0
        if not left:
            return len(right)
        if not right:
            return len(left)

        previous_row = list(range(len(right) + 1))
        for left_index, left_char in enumerate(left, start=1):
            current_row = [left_index]
            for right_index, right_char in enumerate(right, start=1):
                insert_cost = current_row[right_index - 1] + 1
                delete_cost = previous_row[right_index] + 1
                replace_cost = previous_row[right_index - 1] + (left_char != right_char)
                current_row.append(min(insert_cost, delete_cost, replace_cost))
            previous_row = current_row
        return previous_row[-1]

    def list_tags(self, *, query: str | None = None, limit: int = 20) -> list[str]:
        """Return distinct tenant-scoped tags for autocomplete."""
        tag_values = self._base_query().with_entities(Document.tags).filter(Document.tags.isnot(None)).all()
        normalized_query = (query or "").strip().lower()

        unique_tags: list[str] = []
        seen: set[str] = set()
        for (raw_tags,) in tag_values:
            if not raw_tags:
                continue
            for tag in raw_tags.split(","):
                cleaned = tag.strip()
                lowered = cleaned.lower()
                if not cleaned or lowered in seen:
                    continue
                if normalized_query and normalized_query not in lowered:
                    continue
                seen.add(lowered)
                unique_tags.append(cleaned)

        unique_tags.sort(key=lambda value: value.lower())
        return unique_tags[:limit]

    def find_duplicate_titles(
        self,
        title: str,
        *,
        threshold: float = 0.8,
        limit: int = 5,
    ) -> list[dict[str, object]]:
        """Return likely duplicate documents within the current tenant scope."""
        normalized_title = self._normalize_title_for_similarity(title)
        if not normalized_title:
            return []

        matches: list[dict[str, object]] = []
        documents = self._base_query().with_entities(Document.id, Document.title, Document.document_number).all()
        for document_id, document_title, document_number in documents:
            candidate_title = self._normalize_title_for_similarity(document_title or "")
            if not candidate_title:
                continue
            longest_length = max(len(normalized_title), len(candidate_title))
            if longest_length == 0:
                continue
            distance = self._levenshtein_distance(normalized_title, candidate_title)
            similarity = 1 - (distance / longest_length)
            if similarity < threshold:
                continue
            matches.append(
                {
                    "document_id": int(document_id),
                    "title": str(document_title),
                    "document_number": str(document_number),
                    "similarity": round(float(similarity), 3),
                }
            )

        matches.sort(
            key=lambda item: (
                -float(item["similarity"]),
                str(item["title"]).lower(),
                int(item["document_id"]),
            )
        )
        return matches[:limit]

    def bulk_update_metadata(
        self,
        *,
        document_ids: List[int],
        user: User,
        category: Optional[str] = None,
        visibility: Optional[DocumentVisibility] = None,
        company_ids: Optional[List[int]] = None,
        reason: Optional[str] = None,
    ) -> list[int]:
        """Apply one metadata update payload to multiple documents."""
        unique_document_ids = list(dict.fromkeys(document_ids))
        if not unique_document_ids:
            raise ValidationError("Select at least one document")

        update_payload = DocumentUpdate(
            category=category,
            visibility=visibility,
            company_ids=company_ids,
            reason=reason,
        )
        if (
            update_payload.category is None
            and update_payload.visibility is None
            and update_payload.company_ids is None
        ):
            raise ValidationError("Provide at least one metadata field to update")

        updated_ids: list[int] = []
        for document_id in unique_document_ids:
            document = self.get_document(document_id)
            self._verify_access(document)
            if document is None:
                continue
            self.update_document(
                document_id,
                update_payload,
                user,
                if_match=str(document.row_version),
            )
            updated_ids.append(document_id)

        return updated_ids

    def get_document_stats(self) -> dict[str, int]:
        """Return aggregate document counts for dashboard summary cards."""
        stats_row = (
            self._base_query()
            .with_entities(
                func.count(Document.id).label("total"),
                func.sum(case((Document.status == DocumentStatus.ACTIVE, 1), else_=0)).label(
                    "published"
                ),
                func.sum(case((Document.status == DocumentStatus.APPROVED, 1), else_=0)).label(
                    "approved"
                ),
                func.sum(case((Document.status == DocumentStatus.DRAFT, 1), else_=0)).label(
                    "draft"
                ),
            )
            .one()
        )

        return {
            "total": int(stats_row.total or 0),
            "published": int(stats_row.published or 0),
            "approved": int(stats_row.approved or 0),
            "draft": int(stats_row.draft or 0),
        }

    def update_document(
        self,
        document_id: int,
        document_data: DocumentUpdate,
        user: User,
        *,
        if_match: str | None = None,
    ) -> Document:
        """Update document with tenant verification"""
        document = self.get_document(document_id)
        self._verify_write_access(document, user)
        ensure_if_match_matches(
            if_match=if_match,
            resource_type="document",
            resource_id=document.id,
            row_version=document.row_version,
        )
        document_aggregate = DocumentAggregate(document)

        with UnitOfWork(self.db):
            # Track changes
            changes = []
            previous_visibility = document.visibility
            visibility_changed = False
            old_company_ids = sorted(company.id for company in document.assigned_companies)
            current_company_ids = old_company_ids.copy()
            has_visibility_update = document_data.visibility is not None
            has_company_assignment_update = document_data.company_ids is not None
            normalized_company_ids = self._normalize_company_ids(document_data.company_ids)

            # Update fields
            if document_data.title is not None:
                if document.title != document_data.title:
                    changes.append(
                        f"Title changed from '{document.title}' to '{document_data.title}'"
                    )
                document.title = document_data.title

            if document_data.description is not None:
                document.description = document_data.description

            if document_data.version_label is not None:
                document.version_label = document_data.version_label

            if document_data.status is not None:
                if document.status != document_data.status:
                    changes.append(
                        f"Status changed from '{document.status.value}' to '{document_data.status.value}'"
                    )
                document.status = document_data.status

            if document_data.visibility is not None:
                if document.visibility != document_data.visibility:
                    if not (document_data.reason and document_data.reason.strip()):
                        raise ValidationError(
                            "Visibility changes require a reason",
                            error_code=AudienceErrorCode.AUDIENCE_004.value,
                        )
                    document_aggregate.ensure_visibility_change_allowed(user.role)
                    changes.append(
                        f"Visibility changed from '{document.visibility.value}' to '{document_data.visibility.value}'"
                    )
                    visibility_changed = True
                document.visibility = document_data.visibility

            target_visibility = document_data.visibility or document.visibility
            if has_visibility_update or has_company_assignment_update:
                if target_visibility == DocumentVisibility.COMPANY:
                    target_company_ids = (
                        normalized_company_ids if has_company_assignment_update else current_company_ids
                    )
                    document_aggregate.ensure_visibility_assignment_invariants(
                        visibility=target_visibility,
                        company_ids=target_company_ids,
                    )
                    document.assigned_companies = self._resolve_assigned_companies(target_company_ids)
                elif has_company_assignment_update and normalized_company_ids:
                    document_aggregate.ensure_visibility_assignment_invariants(
                        visibility=target_visibility,
                        company_ids=normalized_company_ids,
                    )
                elif previous_visibility == DocumentVisibility.COMPANY:
                    document.assigned_companies = []
                elif has_company_assignment_update:
                    document.assigned_companies = []

            if document_data.category is not None:
                document.category = document_data.category

            if document_data.topic is not None:
                document.topic = self._normalize_topic(document_data.topic)

            if "platform" in document_data.model_fields_set:
                self._require_platform_selection(
                    platform_name=document_data.platform,
                    platform_id=document_data.platform_id,
                )

            if document_data.platform is not None or document_data.platform_id is not None:
                platform = self._get_or_create_platform(
                    platform_name=document_data.platform, platform_id=document_data.platform_id
                )
                if document.platform_id != platform.id:
                    changes.append(f"Platform changed to '{platform.name}'")
                # H-14: Only set the FK; keep string in sync during deprecation period
                document.platform = platform.name
                document.platform_id = platform.id

            if document_data.release_branch is not None:
                document.release_branch = document_data.release_branch

            if document_data.tags is not None:
                document.tags = document_data.tags

            if "due_date" in document_data.model_fields_set:
                document.due_date = document_data.due_date

            # Create new version if there are changes
            if changes:
                latest_version = (
                    self.db.query(Version)
                    .filter(Version.document_id == document_id)
                    .order_by(Version.version_number.desc())
                    .first()
                )
                version = DocumentFactory.create_patch_version(
                    document_id=document.id,
                    latest_version=latest_version,
                    changes_summary="; ".join(changes),
                    created_by=user.id,
                )
                self.db.add(version)

            new_company_ids = sorted(company.id for company in document.assigned_companies)
            added_company_ids = [
                company_id for company_id in new_company_ids if company_id not in old_company_ids
            ]
            removed_company_ids = [
                company_id for company_id in old_company_ids if company_id not in new_company_ids
            ]
            company_assignment_changed = bool(added_company_ids or removed_company_ids)

            # Bump audience_version on any audience mutation
            if visibility_changed or company_assignment_changed:
                document.audience_version = (document.audience_version or 1) + 1

            assignment_diff_payload = (
                {
                    "old_company_ids": old_company_ids,
                    "new_company_ids": new_company_ids,
                    "added_company_ids": added_company_ids,
                    "removed_company_ids": removed_company_ids,
                }
                if company_assignment_changed
                else None
            )

            # Create audit log
            if visibility_changed:
                reason = (document_data.reason or "").strip()
                signed_payload = {
                    "event": AudienceEventType.VISIBILITY_CHANGED.value,
                    "document_id": int(document.id),
                    "user_id": int(user.id),
                    "from_visibility": previous_visibility.value if previous_visibility else None,
                    "to_visibility": document.visibility.value if document.visibility else None,
                    "reason": reason,
                }
                signature_key_id, signature = sign_payload(signed_payload)
                details = json.dumps(
                    {
                        "event": "visibility_change",
                        "from_visibility": previous_visibility.value if previous_visibility else None,
                        "to_visibility": document.visibility.value if document.visibility else None,
                        "reason": reason,
                    },
                    sort_keys=True,
                )
                audit = AuditLog(
                    user_id=user.id,
                    document_id=document.id,
                    action=ActionType.UPDATE,
                    audience_event_type=AudienceEventType.VISIBILITY_CHANGED,
                    details=details,
                    assignment_diff=(
                        json.dumps(assignment_diff_payload, sort_keys=True)
                        if assignment_diff_payload
                        else None
                    ),
                    signature_key_id=signature_key_id,
                    signature=signature,
                )
            elif company_assignment_changed:
                event_type = (
                    AudienceEventType.ASSIGNMENT_CREATED
                    if added_company_ids
                    else AudienceEventType.ASSIGNMENT_REMOVED
                )
                audit = AuditLog(
                    user_id=user.id,
                    document_id=document.id,
                    action=ActionType.UPDATE,
                    audience_event_type=event_type,
                    details=json.dumps(
                        {
                            "event": "assignment_update",
                            "assigned_count": len(new_company_ids),
                        },
                        sort_keys=True,
                    ),
                    assignment_diff=json.dumps(assignment_diff_payload, sort_keys=True),
                )
            else:
                audit = AuditLog(
                    user_id=user.id,
                    document_id=document.id,
                    action=ActionType.UPDATE,
                    details="; ".join(changes) if changes else "Document updated",
                )
            self.db.add(audit)

        self.db.refresh(document)

        if changes:
            summary = "; ".join(changes)
            self.notification_service.notify_document_watchers(
                document=document,
                actor_user=user,
                notification_type=NotificationType.DOCUMENT_UPDATED,
                title=f"{user.full_name or user.username} updated a document you follow",
                message=f"{document.title}: {summary[:200]}",
                link=f"/documents/{document.id}",
            )

        # If visibility or company assignments changed, invalidate portal cache
        if has_visibility_update or has_company_assignment_update:
            from app.projections import (
                invalidate_portal_audience_cache,
                invalidate_search_audience_cache,
            )
            invalidate_portal_audience_cache()
            invalidate_search_audience_cache()
            # Sync FTS5 search index so queries reflect the new audience
            from app.services.search_index_service import SearchIndexSyncService
            SearchIndexSyncService(self.db).sync_document(document_id)

        return document

    def delete_document(self, document_id: int, user: User) -> None:
        """Delete document with tenant verification"""
        document = self.get_document(document_id)
        self._verify_delete_access(document, user)

        with UnitOfWork(self.db):
            # Keep audit + delete in one transaction to avoid partial writes.
            audit = AuditLog(
                user_id=user.id,
                document_id=document.id,
                action=ActionType.DELETE,
                details=f"Deleted document: {document.title}",
            )
            self.db.add(audit)

            # Delete document (cascade will delete versions, attachments, comments)
            self.db.delete(document)

    def assign_company_set(
        self,
        document_id: int,
        company_ids: List[int],
        *,
        if_match: str | None = None,
    ) -> int:
        """Replace the full assigned-company set for a document."""
        document = self.get_document(document_id)
        self._verify_access(document)
        old_company_ids = sorted(company.id for company in (document.assigned_companies or []))
        actor_user_id = self.tenant_ctx.user_id if self.tenant_ctx else None

        requested_ids = self._normalize_company_ids(company_ids)
        if document.visibility == DocumentVisibility.COMPANY and not requested_ids:
            raise ValidationError(
                "Company visibility requires at least one assigned company",
                error_code=AudienceErrorCode.AUDIENCE_001.value,
            )
        assigned_companies = self._resolve_assigned_companies(requested_ids)

        # API callers (tenant-scoped service instances) must provide If-Match tokens,
        # but direct internal service usage remains backwards-compatible.
        if if_match is not None or self.tenant_ctx is not None:
            ensure_if_match_matches(
                if_match=if_match,
                resource_type="document",
                resource_id=document.id,
                row_version=document.row_version,
            )

        # Replay-safe no-op: reapplying the same assignment set must be idempotent.
        if sorted(requested_ids) == old_company_ids:
            return len(requested_ids)

        with UnitOfWork(self.db):
            document.assigned_companies = assigned_companies
            document.updated_at = datetime.utcnow()
            document.audience_version = (document.audience_version or 1) + 1

            new_company_ids = [company.id for company in assigned_companies]
            added_company_ids = [company_id for company_id in new_company_ids if company_id not in old_company_ids]
            removed_company_ids = [
                company_id for company_id in old_company_ids if company_id not in new_company_ids
            ]
            assignment_diff = {
                "old_company_ids": old_company_ids,
                "new_company_ids": new_company_ids,
                "added_company_ids": added_company_ids,
                "removed_company_ids": removed_company_ids,
            }
            if added_company_ids or removed_company_ids:
                event_type = (
                    AudienceEventType.ASSIGNMENT_CREATED
                    if added_company_ids
                    else AudienceEventType.ASSIGNMENT_REMOVED
                )
                write_audit_log(
                    user_id=actor_user_id,
                    document_id=document.id,
                    action=ActionType.UPDATE,
                    audience_event_type=event_type,
                    details=json.dumps(
                        {
                            "event": "assignment_set_replaced",
                            "assigned_count": len(new_company_ids),
                        },
                        sort_keys=True,
                    ),
                    assignment_diff=json.dumps(assignment_diff, sort_keys=True),
                )
                self.db.flush()
                self.event_dispatcher.dispatch(
                    CompanyAssignmentsUpdated(
                        document_id=document.id,
                        document_row_version=int(document.row_version or 1),
                        assigned_company_ids=tuple(sorted(new_company_ids)),
                        actor_user_id=actor_user_id,
                    )
                )

        # Safety net: explicitly invalidate portal + search cache after audience change
        from app.projections import (
            invalidate_portal_audience_cache,
            invalidate_search_audience_cache,
        )
        invalidate_portal_audience_cache()
        invalidate_search_audience_cache()
        # Sync FTS5 search index so queries reflect the new audience
        from app.services.search_index_service import SearchIndexSyncService
        SearchIndexSyncService(self.db).sync_document(document_id)

        return len(requested_ids)

    def archive_document(self, document_id: int, user: User) -> dict:
        """
        Soft-delete a document by setting status to ARCHIVED.

        Preserves all data including audience assignments for potential restore.
        Returns snapshot of audience state at archive time.
        """
        document = self.get_document(document_id)
        self._verify_access(document)

        if document.status == DocumentStatus.ARCHIVED:
            raise InvalidStateError("Document is already archived")

        if user.role not in [UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER]:
            raise PermissionDeniedError("Only admins and managers can archive documents")

        # Capture audience state before archiving
        company_ids = [c.id for c in (document.assigned_companies or [])]
        visibility_snapshot = document.visibility.value if document.visibility else None
        company_ids_snapshot = company_ids.copy()
        previous_status = document.status.value

        with UnitOfWork(self.db):
            document.status = DocumentStatus.ARCHIVED
            document.updated_at = datetime.utcnow()

            write_audit_log(
                user_id=user.id,
                document_id=document.id,
                action=ActionType.UPDATE,
                audience_event_type=AudienceEventType.AUDIENCE_SNAPSHOT_TAKEN,
                details=(
                    f"Archived document '{document.title}'. "
                    f"Previous status: {previous_status}. "
                    f"Audience preserved: visibility={visibility_snapshot}, companies={company_ids_snapshot}"
                ),
            )

        logger.info(
            "Document %d archived by user %d. Audience preserved: visibility=%s companies=%s",
            document_id,
            user.id,
            visibility_snapshot,
            company_ids_snapshot,
        )

        # Archived docs should be removed from active search/public results
        from app.projections import invalidate_search_audience_cache
        invalidate_search_audience_cache()
        from app.services.search_index_service import SearchIndexSyncService
        SearchIndexSyncService(self.db).sync_document(document_id)

        return {
            "document_id": document_id,
            "status": "archived",
            "previous_status": previous_status,
            "audience_snapshot": {
                "visibility": visibility_snapshot,
                "company_ids": company_ids_snapshot,
            },
        }

    def restore_document(self, document_id: int, user: User) -> dict:
        """
        Restore a soft-deleted (archived) document.

        Performs audience reconciliation:
        - Validates that assigned companies still exist and are active
        - Removes stale companies from assignments
        - Logs any audience changes

        Returns the restored document state with any audience changes noted.
        """
        document = self.get_document(document_id)
        self._verify_access(document)

        if document.status != DocumentStatus.ARCHIVED:
            raise InvalidStateError("Only archived documents can be restored")

        if user.role not in [UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER]:
            raise PermissionDeniedError("Only admins and managers can restore documents")

        # Reconcile audience - check for stale companies
        original_company_ids = [c.id for c in (document.assigned_companies or [])]

        # Check which companies are still active
        active_companies = []
        stale_companies = []

        if original_company_ids:
            tenants = self.db.query(Tenant).filter(Tenant.id.in_(original_company_ids)).all()
            tenant_map = {t.id: t for t in tenants}

            for cid in original_company_ids:
                tenant = tenant_map.get(cid)
                if tenant is None:
                    stale_companies.append({"id": cid, "reason": "deleted"})
                elif not tenant.is_active:
                    stale_companies.append({"id": cid, "name": tenant.name, "reason": "deactivated"})
                else:
                    active_companies.append(tenant)

        # Determine appropriate status for restore
        # If document was published before, restore to ACTIVE. Otherwise DRAFT.
        has_published_version = any(v.is_published for v in document.versions)
        restore_status = DocumentStatus.ACTIVE if has_published_version else DocumentStatus.DRAFT

        # Handle audience changes
        audience_changes = {
            "removed_stale_companies": stale_companies,
            "original_company_count": len(original_company_ids),
            "restored_company_count": len(active_companies),
        }

        # Validate company visibility with remaining companies
        if document.visibility == DocumentVisibility.COMPANY and not active_companies:
            # All companies were stale - need to change visibility
            audience_changes["visibility_change"] = {
                "from": "company",
                "to": "internal",
                "reason": "No active companies remain after reconciliation",
            }
            new_visibility = DocumentVisibility.INTERNAL
        else:
            new_visibility = document.visibility

        with UnitOfWork(self.db):
            document.status = restore_status
            document.visibility = new_visibility
            document.assigned_companies = active_companies
            document.updated_at = datetime.utcnow()

            write_audit_log(
                user_id=user.id,
                document_id=document.id,
                action=ActionType.UPDATE,
                audience_event_type=AudienceEventType.AUDIENCE_ROLLBACK,
                details=(
                    f"Restored document '{document.title}' from archive. "
                    f"New status: {restore_status.value}. "
                    f"Audience reconciliation: {audience_changes}"
                ),
            )

        logger.info(
            "Document %d restored by user %d. Audience reconciliation: %s",
            document_id,
            user.id,
            audience_changes,
        )

        return {
            "document_id": document_id,
            "status": restore_status.value,
            "visibility": new_visibility.value,
            "audience_reconciliation": audience_changes,
            "active_company_ids": [c.id for c in active_companies],
        }
