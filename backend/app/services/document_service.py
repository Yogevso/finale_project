"""Document Service"""

import logging
import re
from datetime import datetime
from typing import List, Optional

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies.tenant import TenantContext
from app.domain.aggregates import DocumentAggregate
from app.domain.factories import DocumentFactory
from app.domain.specifications import DocumentVisibilityCompanyAssignmentSpec
from app.domain.value_objects import DocumentNumber
from app.errors import InvalidStateError, NotFoundError, PermissionDeniedError, ValidationError
from app.models import (
    ActionType,
    AuditLog,
    Document,
    DocumentNumberSequence,
    DocumentStatus,
    DocumentVisibility,
    Platform,
    Tenant,
    Topic,
    User,
    UserRole,
    Version,
)
from app.schemas import DocumentCreate, DocumentUpdate
from app.services.base_service import TenantAwareService
from app.services.uow import UnitOfWork
from app.utils.concurrency import ensure_if_match_matches
from app.utils.topic_normalization import build_topic_lookup, normalize_topic_to_slug

logger = logging.getLogger(__name__)


class DocumentService(TenantAwareService[Document]):
    """Document CRUD service with multi-tenancy support"""

    model = Document
    _company_visibility_assignment_spec = DocumentVisibilityCompanyAssignmentSpec()

    def __init__(self, db: Session, tenant_ctx: Optional[TenantContext] = None):
        super().__init__(db, tenant_ctx)

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
        update_result = self.db.execute(
            update(DocumentNumberSequence)
            .where(DocumentNumberSequence.date_key == date_key)
            .values(
                next_value=DocumentNumberSequence.next_value + 1,
                updated_at=datetime.utcnow(),
            )
        )
        if update_result.rowcount != 1:
            raise RuntimeError("Failed to reserve a document number sequence value")

        next_value = self.db.execute(
            select(DocumentNumberSequence.next_value).where(DocumentNumberSequence.date_key == date_key)
        ).scalar_one()
        return int(next_value)

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
        self.db.flush()
        return platform

    @staticmethod
    def _normalize_company_ids(company_ids: Optional[List[int]]) -> List[int]:
        if not company_ids:
            return []

        normalized_ids = list(dict.fromkeys(company_ids))
        if any(company_id <= 0 for company_id in normalized_ids):
            raise ValidationError(
                "Company IDs must be positive integers",
                error_code="invalid_company_set",
            )
        return normalized_ids

    def _resolve_assigned_companies(self, company_ids: List[int]) -> List[Tenant]:
        if not company_ids:
            return []

        companies = self.db.query(Tenant).filter(Tenant.id.in_(company_ids)).all()
        company_by_id = {company.id: company for company in companies}
        missing_ids = [company_id for company_id in company_ids if company_id not in company_by_id]
        if missing_ids:
            raise ValidationError("Some company IDs are invalid", error_code="invalid_company_set")

        inactive_ids = [company.id for company in companies if not company.is_active]
        if inactive_ids:
            raise ValidationError(
                "Inactive companies cannot be assigned to documents",
                error_code="invalid_company_set",
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
        """Create a new document"""
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
            # Re-validate after carry-over
            self._validate_company_visibility_assignment(
                visibility=document_data.visibility,
                company_ids=normalized_company_ids,
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

    def get_documents(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[DocumentStatus] = None,
        visibility: Optional[DocumentVisibility] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
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

        # Apply pagination
        documents = query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()

        return documents, total

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
        self._verify_access(document)
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
            current_company_ids = [company.id for company in document.assigned_companies]
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
                    document_aggregate.ensure_visibility_change_allowed(user.role)
                    changes.append(
                        f"Visibility changed from '{document.visibility.value}' to '{document_data.visibility.value}'"
                    )
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

            if document_data.platform is not None or document_data.platform_id is not None:
                platform = self._get_or_create_platform(
                    platform_name=document_data.platform, platform_id=document_data.platform_id
                )
                if document.platform_id != platform.id:
                    changes.append(f"Platform changed to '{platform.name}'")
                document.platform = platform.name
                document.platform_id = platform.id

            if document_data.release_branch is not None:
                document.release_branch = document_data.release_branch

            if document_data.tags is not None:
                document.tags = document_data.tags

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

            # Create audit log
            audit = AuditLog(
                user_id=user.id,
                document_id=document.id,
                action=ActionType.UPDATE,
                details="; ".join(changes) if changes else "Document updated",
            )
            self.db.add(audit)

        self.db.refresh(document)

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
        self._verify_access(document)

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

        requested_ids = self._normalize_company_ids(company_ids)
        if document.visibility == DocumentVisibility.COMPANY and not requested_ids:
            raise ValidationError(
                "Company visibility requires at least one assigned company",
                error_code="missing_company_assignment",
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

        with UnitOfWork(self.db):
            document.assigned_companies = assigned_companies
            document.updated_at = datetime.utcnow()

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

            audit = AuditLog(
                user_id=user.id,
                document_id=document.id,
                action=ActionType.UPDATE,
                details=(
                    f"Archived document '{document.title}'. "
                    f"Previous status: {previous_status}. "
                    f"Audience preserved: visibility={visibility_snapshot}, companies={company_ids_snapshot}"
                ),
            )
            self.db.add(audit)

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

            audit = AuditLog(
                user_id=user.id,
                document_id=document.id,
                action=ActionType.UPDATE,
                details=(
                    f"Restored document '{document.title}' from archive. "
                    f"New status: {restore_status.value}. "
                    f"Audience reconciliation: {audience_changes}"
                ),
            )
            self.db.add(audit)

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
