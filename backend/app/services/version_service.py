"""Version Service - Business logic for document versions"""

import json
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import joinedload

from app.config import settings
from app.domain.aggregates import DocumentAggregate
from app.domain.events import DocumentPublished, InProcessDomainEventDispatcher
from app.domain.factories import VersionFactory
from app.domain.states import version_review_stage_for
from app.errors import (
    ConflictError,
    InvalidStateError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.models import (
    Document,
    ReviewRequest,
    ReviewStatus,
    User,
    UserRole,
    Version,
    VersionBumpType,
)
from app.repositories import DocumentRepository, VersionRepository
from app.schemas import VersionCreate, VersionUpdate
from app.services.base_service import SessionService
from app.services.outbox import build_outbox_event_dispatcher
from app.services.uow import UnitOfWork
from app.utils.concurrency import ensure_if_match_matches

logger = logging.getLogger(__name__)


class VersionService(SessionService):
    """Service for managing document versions"""

    def __init__(
        self,
        db,
        *,
        event_dispatcher: InProcessDomainEventDispatcher | None = None,
    ):
        super().__init__(db)
        self.document_repository = DocumentRepository(db)
        self.version_repository = VersionRepository(db)
        self.event_dispatcher = event_dispatcher or build_outbox_event_dispatcher(db)

    def _get_document_for_user(self, document_id: int, current_user: User) -> Document:
        document = self.document_repository.get_by_id(document_id)
        if not document:
            raise NotFoundError("Document not found")

        if (
            current_user.role != UserRole.SYSTEM_ADMIN
            and document.tenant_id != current_user.tenant_id
        ):
            raise NotFoundError("Document not found")

        return document

    def _latest_review_for_version(
        self, document_id: int, version_id: int
    ) -> Optional[ReviewRequest]:
        """Get latest review record for a document version."""
        return (
            self.db.query(ReviewRequest)
            .options(
                joinedload(ReviewRequest.submitter),
                joinedload(ReviewRequest.reviewer),
            )
            .filter(
                ReviewRequest.document_id == document_id,
                ReviewRequest.version_id == version_id,
            )
            .order_by(ReviewRequest.submitted_at.desc(), ReviewRequest.id.desc())
            .first()
        )

    def _latest_reviews_for_versions(
        self, document_id: int, version_ids: List[int]
    ) -> dict[int, ReviewRequest]:
        """Get latest review record per version id."""
        if not version_ids:
            return {}

        rows = (
            self.db.query(ReviewRequest)
            .options(
                joinedload(ReviewRequest.submitter),
                joinedload(ReviewRequest.reviewer),
            )
            .filter(
                ReviewRequest.document_id == document_id,
                ReviewRequest.version_id.in_(version_ids),
            )
            .order_by(
                ReviewRequest.version_id.asc(),
                ReviewRequest.submitted_at.desc(),
                ReviewRequest.id.desc(),
            )
            .all()
        )

        latest_by_version: dict[int, ReviewRequest] = {}
        for review in rows:
            if review.version_id is None:
                continue
            if review.version_id not in latest_by_version:
                latest_by_version[review.version_id] = review
        return latest_by_version

    @staticmethod
    def _serialize_review(review: Optional[ReviewRequest]) -> Optional[dict]:
        if not review:
            return None
        return {
            "id": review.id,
            "status": review.status,
            "submitted_at": review.submitted_at,
            "reviewed_at": review.reviewed_at,
            "submitted_by": review.submitted_by,
            "reviewed_by": review.reviewed_by,
            "submitter": review.submitter,
            "reviewer": review.reviewer,
        }

    @staticmethod
    def _serialize_version(version: Version, latest_review: Optional[ReviewRequest] = None) -> dict:
        return {
            "id": version.id,
            "document_id": version.document_id,
            "version_number": version.version_number,
            "semantic_version": version.semantic_version,
            "bump_type": version.bump_type,
            "row_version": version.row_version,
            "etag": version.etag,
            "content": version.content,
            "changes_summary": version.changes_summary,
            "is_published": version.is_published,
            "published_at": version.published_at,
            "published_by": version.published_by,
            "created_by": version.created_by,
            "created_at": version.created_at,
            "created_by_user": version.created_by_user,
            "published_by_user": version.published_by_user,
            "latest_review": VersionService._serialize_review(latest_review),
            "audience_visibility_snapshot": version.audience_visibility_snapshot,
            "audience_company_ids_snapshot": version.audience_company_ids_snapshot,
        }

    def get_versions(self, document_id: int, current_user: User) -> List[dict]:
        """Get all versions for a document"""
        self._get_document_for_user(document_id, current_user)

        versions = self.version_repository.list_for_document(document_id, include_users=True)
        latest_reviews = self._latest_reviews_for_versions(document_id, [v.id for v in versions])
        return [VersionService._serialize_version(v, latest_reviews.get(v.id)) for v in versions]

    def get_version(self, document_id: int, version_id: int, current_user: User) -> dict:
        """Get a specific version"""
        self._get_document_for_user(document_id, current_user)

        version = self.version_repository.get_by_id_for_document(
            version_id,
            document_id,
            include_users=True,
        )

        if not version:
            raise NotFoundError("Version not found")

        latest_review = self._latest_review_for_version(document_id, version_id)
        return VersionService._serialize_version(version, latest_review)

    def create_version(
        self, document_id: int, version_data: VersionCreate, current_user: User
    ) -> dict:
        """Create a new version for a document"""
        document = self._get_document_for_user(document_id, current_user)
        document_aggregate = DocumentAggregate(document)

        if current_user.role not in [
            UserRole.SYSTEM_ADMIN,
            UserRole.ADMIN,
            UserRole.MANAGER,
            UserRole.EDITOR,
        ]:
            raise PermissionDeniedError("Only admins, managers and editors can create versions")

        pending_review = (
            self.db.query(ReviewRequest)
            .filter(
                ReviewRequest.document_id == document_id,
                ReviewRequest.status == ReviewStatus.PENDING,
            )
            .first()
        )
        if pending_review:
            raise ConflictError("Cannot create a new version while a review is pending")

        last_version = self.version_repository.get_latest_for_document(document_id)
        bump_type = version_data.bump_type or VersionBumpType.PATCH
        version = VersionFactory.create_candidate_version(
            document_id=document_id,
            created_by=current_user.id,
            last_version=last_version,
            bump_type=bump_type,
            content=version_data.content,
            changes_summary=version_data.changes_summary,
        )

        with UnitOfWork(self.db):
            self.db.add(version)
            document_aggregate.prepare_for_new_version_candidate()

        version = self.version_repository.get_by_id_for_document(
            version.id,
            document_id,
            include_users=True,
        )
        return VersionService._serialize_version(version)

    def update_version(
        self,
        document_id: int,
        version_id: int,
        version_data: VersionUpdate,
        current_user: User,
        *,
        if_match: str | None = None,
    ) -> dict:
        """Update an unpublished version"""
        self._get_document_for_user(document_id, current_user)

        version = self.version_repository.get_by_id_for_document(
            version_id,
            document_id,
            include_users=True,
        )

        if not version:
            raise NotFoundError("Version not found")

        if version.is_published:
            raise InvalidStateError(
                "Cannot modify published version - versions are immutable after publishing"
            )

        latest_review = self._latest_review_for_version(document_id, version_id)
        version_review_stage_for(
            latest_review.status if latest_review else None
        ).ensure_version_mutable()

        if current_user.role not in [
            UserRole.SYSTEM_ADMIN,
            UserRole.ADMIN,
            UserRole.MANAGER,
            UserRole.EDITOR,
        ]:
            raise PermissionDeniedError("Only admins, managers and editors can update versions")
        ensure_if_match_matches(
            if_match=if_match,
            resource_type="version",
            resource_id=version.id,
            row_version=version.row_version,
        )

        with UnitOfWork(self.db):
            if version_data.content is not None:
                version.content = version_data.content
            if version_data.changes_summary is not None:
                version.changes_summary = version_data.changes_summary

        self.db.refresh(version)

        latest_review = self._latest_review_for_version(document_id, version_id)
        return VersionService._serialize_version(version, latest_review)

    def publish_approved_version(
        self,
        document_id: int,
        version_id: int,
        current_user: User,
    ) -> dict:
        """Use-case intent alias for publishing an approved version."""
        return self.publish_version(document_id, version_id, current_user)

    def publish_version(self, document_id: int, version_id: int, current_user: User) -> dict:
        """Publish a version (requires approval and makes it immutable)."""
        document = self._get_document_for_user(document_id, current_user)
        # Ensure assigned_companies is loaded for audience snapshot
        self.db.refresh(document, attribute_names=["assigned_companies"])

        version = self.version_repository.get_by_id_for_document(
            version_id,
            document_id,
            include_users=True,
        )

        if not version:
            raise NotFoundError("Version not found")

        # Idempotency: If already published, verify audience snapshot matches and return success
        if version.is_published:
            # Check if current audience state matches the published snapshot
            company_ids = [c.id for c in (document.assigned_companies or [])]
            current_visibility = document.visibility.value if document.visibility else None
            current_company_ids = json.dumps(company_ids) if company_ids else None

            if (
                version.audience_visibility_snapshot == current_visibility
                and version.audience_company_ids_snapshot == current_company_ids
            ):
                # Idempotent retry - same state, return success
                logging.getLogger(__name__).info(
                    "Idempotent publish retry for document=%d version=%d - already published with matching audience",
                    document_id,
                    version_id,
                )
                latest_review = self._latest_review_for_version(document_id, version_id)
                return VersionService._serialize_version(version, latest_review)
            else:
                # Audience changed since publish - not idempotent
                raise InvalidStateError(
                    "Version is already published with different audience state. "
                    "Current audience does not match published snapshot."
                )

        if current_user.role not in [UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER]:
            raise PermissionDeniedError("Only admins and managers can publish versions")

        # Stale company detection - check for deactivated companies in audience
        from app.models import Tenant
        company_ids = [c.id for c in (document.assigned_companies or [])]
        if company_ids:
            stale_companies = (
                self.db.query(Tenant)
                .filter(
                    Tenant.id.in_(company_ids),
                    Tenant.is_active.is_(False),
                )
                .all()
            )
            if stale_companies:
                stale_names = [c.name for c in stale_companies]
                logger.warning(
                    "Publish blocked: stale companies in audience for document=%d version=%d. "
                    "Stale companies: %s",
                    document_id,
                    version_id,
                    stale_names,
                )
                raise InvalidStateError(
                    f"Cannot publish: document has deactivated companies in audience: {stale_names}. "
                    "Please remove them before publishing."
                )

        latest_review = self._latest_review_for_version(document_id, version_id)
        version_review_stage_for(
            latest_review.status if latest_review else None
        ).ensure_publishable_for_version()

        # Ensure audience configuration is valid before publishing
        DocumentAggregate(document).ensure_audience_ready_for_submit()

        # Capture audience state snapshot for carry-forward auditing
        company_ids = [c.id for c in (document.assigned_companies or [])]
        audience_visibility_snapshot = document.visibility.value if document.visibility else None
        audience_company_ids_snapshot = json.dumps(company_ids) if company_ids else None

        try:
            with UnitOfWork(self.db):
                version.is_published = True
                version.published_at = datetime.utcnow()
                version.published_by = current_user.id
                version.audience_visibility_snapshot = audience_visibility_snapshot
                version.audience_company_ids_snapshot = audience_company_ids_snapshot

                DocumentAggregate(document).transition_to_active()
                self.event_dispatcher.dispatch(
                    DocumentPublished(
                        document_id=document.id,
                        version_id=version.id,
                        document_title=document.title,
                        document_number=document.document_number,
                        document_url=f"{settings.BASE_URL}/viewer/documents/{document.id}",
                        document_author_id=document.created_by,
                        published_by_user_id=current_user.id,
                    )
                )
        except Exception as e:
            # Log failed publish attempt with audience state for audit trail
            logging.getLogger(__name__).error(
                "Publish failed for document=%d version=%d user=%d. "
                "Audience state at failure: visibility=%s, companies=%s. Error: %s",
                document_id,
                version_id,
                current_user.id,
                audience_visibility_snapshot,
                audience_company_ids_snapshot,
                str(e),
            )
            # Re-raise to let caller handle the error
            # Database changes auto-rollback via UnitOfWork context manager
            raise

        self.db.refresh(version)

        version = self.version_repository.get_by_id_for_document(
            version_id,
            document_id,
            include_users=True,
        )
        latest_review = self._latest_review_for_version(document_id, version_id)
        return VersionService._serialize_version(version, latest_review)

    def publish_preflight_checks(
        self, document_id: int, version_id: int, current_user: User
    ) -> dict:
        """
        Return a preflight checklist indicating readiness to publish a version.

        The checklist includes:
        - version_exists: The version exists for the document
        - not_already_published: Version is not already published
        - user_can_publish: User has permission to publish
        - review_approved: The version has an approved review
        - audience_ready: Audience configuration is valid (company visibility requires assignments)
        """
        from app.models import DocumentVisibility

        checks = []

        # Check 1: Version exists
        document = None
        version = None
        try:
            document = self._get_document_for_user(document_id, current_user)
            version = self.version_repository.get_by_id_for_document(
                version_id, document_id, include_users=True
            )
            version_exists = version is not None
        except (NotFoundError, PermissionDeniedError):
            version_exists = False

        checks.append({
            "id": "version_exists",
            "label": "Version exists",
            "passed": version_exists,
            "message": None if version_exists else "Version not found",
        })

        # Check 2: Not already published
        if version:
            not_published = not version.is_published
            checks.append({
                "id": "not_already_published",
                "label": "Not already published",
                "passed": not_published,
                "message": None if not_published else "Version is already published",
            })
        else:
            checks.append({
                "id": "not_already_published",
                "label": "Not already published",
                "passed": False,
                "message": "Cannot check - version not found",
            })

        # Check 3: User has permission to publish
        can_publish = current_user.role in [
            UserRole.SYSTEM_ADMIN,
            UserRole.ADMIN,
            UserRole.MANAGER,
        ]
        checks.append({
            "id": "user_can_publish",
            "label": "User can publish",
            "passed": can_publish,
            "message": None if can_publish else "Only admins and managers can publish versions",
        })

        # Check 4: Review is approved
        if version:
            latest_review = self._latest_review_for_version(document_id, version_id)
            review_approved = (
                latest_review is not None and latest_review.status == ReviewStatus.APPROVED
            )
            if not latest_review:
                review_message = "No review submitted for this version"
            elif latest_review.status == ReviewStatus.PENDING:
                review_message = "Review is still pending"
            elif latest_review.status == ReviewStatus.REJECTED:
                review_message = "Review was rejected"
            elif latest_review.status == ReviewStatus.CANCELLED:
                review_message = "Review was cancelled"
            else:
                review_message = None

            checks.append({
                "id": "review_approved",
                "label": "Review approved",
                "passed": review_approved,
                "message": review_message,
            })
        else:
            checks.append({
                "id": "review_approved",
                "label": "Review approved",
                "passed": False,
                "message": "Cannot check - version not found",
            })

        # Check 5: Audience readiness (company visibility requires at least one company assignment)
        if document:
            if document.visibility == DocumentVisibility.COMPANY:
                has_company_assignments = (
                    document.assigned_companies is not None
                    and len(document.assigned_companies) > 0
                )
                checks.append({
                    "id": "audience_ready",
                    "label": "Audience configured",
                    "passed": has_company_assignments,
                    "message": (
                        None
                        if has_company_assignments
                        else "Company visibility requires at least one company assignment"
                    ),
                })
            else:
                # Internal or public visibility doesn't need company assignments
                checks.append({
                    "id": "audience_ready",
                    "label": "Audience configured",
                    "passed": True,
                    "message": None,
                })
        else:
            checks.append({
                "id": "audience_ready",
                "label": "Audience configured",
                "passed": False,
                "message": "Cannot check - document not found",
            })

        # Overall readiness
        ready = all(check["passed"] for check in checks)

        return {"ready": ready, "checks": checks}

    def delete_version(self, document_id: int, version_id: int, current_user: User) -> None:
        """Delete an unpublished version"""
        self._get_document_for_user(document_id, current_user)

        version = self.version_repository.get_by_id_for_document(version_id, document_id)

        if not version:
            raise NotFoundError("Version not found")

        if version.is_published:
            raise InvalidStateError("Cannot delete published version")

        if current_user.role not in [UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER]:
            raise PermissionDeniedError("Only admins and managers can delete versions")

        with UnitOfWork(self.db):
            self.db.delete(version)

    def get_latest_published(self, document_id: int) -> Optional[Version]:
        """Get the latest published version for a document"""
        return self.version_repository.get_latest_published_for_document(document_id)

    def restore_audience_from_version(
        self, document_id: int, version_id: int, current_user: User
    ) -> dict:
        """
        Restore document audience state from a published version's snapshot.

        This provides rollback capability if audience was changed incorrectly
        after a version was published.

        Integrity checks:
        - All company IDs in the snapshot must still exist
        - Visibility value must be valid
        """
        from app.models import ActionType, AudienceEventType, AuditLog, DocumentVisibility, Tenant

        if current_user.role not in [UserRole.SYSTEM_ADMIN, UserRole.ADMIN]:
            raise PermissionDeniedError("Only admins can restore audience state")

        document = self._get_document_for_user(document_id, current_user)
        self.db.refresh(document, attribute_names=["assigned_companies"])

        version = self.version_repository.get_by_id_for_document(version_id, document_id)

        if not version:
            raise NotFoundError("Version not found")

        if not version.is_published:
            raise InvalidStateError("Can only restore from published versions")

        if not version.audience_visibility_snapshot:
            raise InvalidStateError("Version has no audience snapshot to restore from")

        # Parse and validate the snapshot
        try:
            visibility = DocumentVisibility(version.audience_visibility_snapshot)
        except ValueError as exc:
            raise InvalidStateError(
                f"Invalid visibility value in snapshot: {version.audience_visibility_snapshot}"
            ) from exc

        company_ids = json.loads(version.audience_company_ids_snapshot or "[]")

        # Validate all companies still exist (integrity check)
        missing_company_ids = []
        valid_companies = []
        if company_ids:
            companies = self.db.query(Tenant).filter(Tenant.id.in_(company_ids)).all()
            found_ids = {c.id for c in companies}
            missing_company_ids = [cid for cid in company_ids if cid not in found_ids]
            valid_companies = companies

        # Capture current state for audit
        old_visibility = document.visibility.value if document.visibility else None
        old_company_ids = [c.id for c in (document.assigned_companies or [])]

        with UnitOfWork(self.db):
            # Update document visibility
            document.visibility = visibility

            # Update company assignments (only with valid companies)
            document.assigned_companies.clear()
            for company in valid_companies:
                document.assigned_companies.append(company)

            self.db.add(
                AuditLog(
                    user_id=current_user.id,
                    document_id=document_id,
                    action=ActionType.UPDATE,
                    audience_event_type=AudienceEventType.AUDIENCE_ROLLBACK,
                    details=json.dumps(
                        {
                            "event": "restore_audience_from_version",
                            "version_id": version_id,
                            "previous_visibility": old_visibility,
                            "restored_visibility": visibility.value,
                            "missing_company_ids": missing_company_ids,
                        },
                        sort_keys=True,
                    ),
                    assignment_diff=json.dumps(
                        {
                            "old_company_ids": old_company_ids,
                            "new_company_ids": [c.id for c in valid_companies],
                            "added_company_ids": [
                                cid for cid in [c.id for c in valid_companies] if cid not in old_company_ids
                            ],
                            "removed_company_ids": [
                                cid for cid in old_company_ids if cid not in [c.id for c in valid_companies]
                            ],
                        },
                        sort_keys=True,
                    ),
                )
            )

        # Log warning if some companies were missing
        logger = logging.getLogger(__name__)
        if missing_company_ids:
            logger.warning(
                "Audience restore for document=%d from version=%d: "
                "Some companies no longer exist: %s. Restored with valid companies only.",
                document_id,
                version_id,
                missing_company_ids,
            )

        logger.info(
            "Audience restored for document=%d from version=%d by user=%d. "
            "Visibility: %s -> %s, companies: %s -> %s (missing: %s)",
            document_id,
            version_id,
            current_user.id,
            old_visibility,
            visibility.value,
            old_company_ids,
            [c.id for c in valid_companies],
            missing_company_ids,
        )

        return {
            "document_id": document_id,
            "version_id": version_id,
            "restored_visibility": visibility.value,
            "restored_company_ids": [c.id for c in valid_companies],
            "missing_company_ids": missing_company_ids,
            "previous_visibility": old_visibility,
            "previous_company_ids": old_company_ids,
        }

    def force_publish_version(
        self,
        document_id: int,
        version_id: int,
        current_user: User,
        reason: str,
        acknowledge_risks: bool,
    ) -> dict:
        """
        Force publish a version with admin override, bypassing normal review requirements.

        Creates an enhanced audit trail for compliance.
        """
        from app.models import ActionType, AudienceEventType, AuditLog

        # Only system_admin can force publish
        if current_user.role != UserRole.SYSTEM_ADMIN:
            raise PermissionDeniedError("Only system admins can force publish versions")

        if not acknowledge_risks:
            raise InvalidStateError("Must acknowledge risks to force publish")

        if len(reason) < 10:
            raise InvalidStateError("Reason must be at least 10 characters")

        document = self._get_document_for_user(document_id, current_user)
        self.db.refresh(document, attribute_names=["assigned_companies"])

        version = self.version_repository.get_by_id_for_document(
            version_id, document_id, include_users=True
        )

        if not version:
            raise NotFoundError("Version not found")

        # Idempotency check
        if version.is_published:
            return {
                "version_id": version.id,
                "document_id": document_id,
                "published_at": version.published_at.isoformat() if version.published_at else None,
                "forced_by_user_id": current_user.id,
                "reason": reason,
                "warnings_overridden": ["Version was already published"],
            }

        # Collect warnings that are being overridden
        warnings_overridden = []

        # Check for review requirement
        latest_review = self._latest_review_for_version(document_id, version_id)
        if not latest_review or latest_review.status != ReviewStatus.APPROVED:
            warnings_overridden.append("No approved review - bypassing review requirement")

        # Check audience readiness
        try:
            DocumentAggregate(document).ensure_audience_ready_for_submit()
        except Exception as e:
            warnings_overridden.append(f"Audience validation failed: {str(e)}")

        # Capture audience snapshot
        company_ids = [c.id for c in (document.assigned_companies or [])]
        audience_visibility_snapshot = document.visibility.value if document.visibility else None
        audience_company_ids_snapshot = json.dumps(company_ids) if company_ids else None

        with UnitOfWork(self.db):
            version.is_published = True
            version.published_at = datetime.utcnow()
            version.published_by = current_user.id
            version.audience_visibility_snapshot = audience_visibility_snapshot
            version.audience_company_ids_snapshot = audience_company_ids_snapshot

            DocumentAggregate(document).transition_to_active()

            # Enhanced audit trail for forced publish
            self.db.add(
                AuditLog(
                    user_id=current_user.id,
                    document_id=document_id,
                    action=ActionType.UPDATE,
                    audience_event_type=AudienceEventType.AUDIENCE_SNAPSHOT_TAKEN,
                    details=json.dumps(
                        {
                            "event": "forced_publish",
                            "version_number": version.version_number,
                            "reason": reason,
                            "warnings_overridden": warnings_overridden,
                        },
                        sort_keys=True,
                    ),
                )
            )

            self.event_dispatcher.dispatch(
                DocumentPublished(
                    document_id=document.id,
                    version_id=version.id,
                    document_title=document.title,
                    document_number=document.document_number,
                    document_url=f"{settings.BASE_URL}/viewer/documents/{document.id}",
                    document_author_id=document.created_by,
                    published_by_user_id=current_user.id,
                )
            )

        logging.getLogger(__name__).warning(
            "FORCED PUBLISH by user=%d for document=%d version=%d. "
            "Reason: %s. Warnings overridden: %s",
            current_user.id,
            document_id,
            version_id,
            reason,
            warnings_overridden,
        )

        return {
            "version_id": version.id,
            "document_id": document_id,
            "published_at": version.published_at.isoformat() if version.published_at else None,
            "forced_by_user_id": current_user.id,
            "reason": reason,
            "warnings_overridden": warnings_overridden,
        }

    def schedule_publish(
        self,
        document_id: int,
        version_id: int,
        scheduled_at: datetime,
        current_user: User,
    ) -> dict:
        """
        Schedule a version to be published at a specific time.
        Audience validation happens at schedule time and again at publish time.
        """
        from app.models import ActionType, AuditLog

        document = self._get_document_for_user(document_id, current_user)

        version = self.version_repository.get_by_id_for_document(
            version_id, document_id, include_users=True
        )
        if not version:
            raise NotFoundError("Version not found")

        if version.is_published:
            raise InvalidStateError("Version is already published")

        if scheduled_at <= datetime.utcnow():
            raise InvalidStateError("Scheduled time must be in the future")

        # Initial audience validation at schedule time
        try:
            DocumentAggregate(document).ensure_audience_ready_for_submit()
        except ValidationError as exc:
            raise InvalidStateError(f"Audience validation failed: {exc}") from exc

        # Require latest review state to be approved for this version.
        latest_review = self._latest_review_for_version(document_id, version_id)
        if not latest_review or latest_review.status != ReviewStatus.APPROVED:
            raise InvalidStateError("Cannot schedule publish: latest review is not approved")

        # Capture audience snapshot at schedule time to detect drift at execution time.
        company_ids = [c.id for c in (document.assigned_companies or [])]
        scheduled_visibility_snapshot = document.visibility.value if document.visibility else None
        scheduled_company_ids_snapshot = json.dumps(company_ids) if company_ids else None

        with UnitOfWork(self.db):
            version.scheduled_publish_at = scheduled_at
            version.scheduled_publish_audience_validated_at = datetime.utcnow()
            version.audience_visibility_snapshot = scheduled_visibility_snapshot
            version.audience_company_ids_snapshot = scheduled_company_ids_snapshot

            self.db.add(
                AuditLog(
                    user_id=current_user.id,
                    document_id=document_id,
                    action=ActionType.UPDATE,
                    details=(
                        f"Scheduled publish for version {version.version_number} "
                        f"at {scheduled_at.isoformat()}. "
                        f"Audience validated and snapshot captured at schedule time."
                    ),
                )
            )

        logger.info(
            "Scheduled publish for document=%d version=%d at %s by user=%d",
            document_id,
            version_id,
            scheduled_at.isoformat(),
            current_user.id,
        )

        return {
            "version_id": version.id,
            "document_id": document_id,
            "scheduled_publish_at": scheduled_at.isoformat(),
            "audience_validated_at": version.scheduled_publish_audience_validated_at.isoformat(),
        }

    def cancel_scheduled_publish(
        self,
        document_id: int,
        version_id: int,
        current_user: User,
    ) -> dict:
        """Cancel a scheduled publish."""
        from app.models import ActionType, AuditLog

        _ = self._get_document_for_user(document_id, current_user)

        version = self.version_repository.get_by_id_for_document(
            version_id, document_id, include_users=True
        )
        if not version:
            raise NotFoundError("Version not found")

        if not version.scheduled_publish_at:
            raise InvalidStateError("Version is not scheduled for publish")

        if version.is_published:
            raise InvalidStateError("Version is already published")

        old_scheduled_at = version.scheduled_publish_at

        with UnitOfWork(self.db):
            version.scheduled_publish_at = None
            version.scheduled_publish_audience_validated_at = None
            version.audience_visibility_snapshot = None
            version.audience_company_ids_snapshot = None

            self.db.add(
                AuditLog(
                    user_id=current_user.id,
                    document_id=document_id,
                    action=ActionType.UPDATE,
                    details=(
                        f"Cancelled scheduled publish for version {version.version_number}. "
                        f"Was scheduled for {old_scheduled_at.isoformat()}."
                    ),
                )
            )

        return {
            "version_id": version.id,
            "document_id": document_id,
            "cancelled_scheduled_at": old_scheduled_at.isoformat(),
        }

    def process_scheduled_publishes(self, batch_size: int = 10) -> dict:
        """
        Process scheduled publishes that are due.
        Re-validates audience before publishing.
        Returns a report of processed items.
        """
        from app.models import ActionType, AuditLog, Tenant

        now = datetime.utcnow()
        due_versions = (
            self.db.query(Version)
            .options(joinedload(Version.document))
            .filter(
                Version.scheduled_publish_at <= now,
                Version.is_published.is_(False),
            )
            .limit(batch_size)
            .all()
        )

        report = {
            "processed": 0,
            "published": 0,
            "failed_validation": 0,
            "failed_stale_company": 0,
            "errors": [],
        }

        for version in due_versions:
            report["processed"] += 1
            document = version.document

            try:
                # Re-validate audience before publishing
                current_company_ids = [c.id for c in (document.assigned_companies or [])]

                # Check if audience has changed since scheduling
                original_snapshot = version.audience_company_ids_snapshot
                original_ids = json.loads(original_snapshot) if original_snapshot else []

                audience_diff = {
                    "added": [cid for cid in current_company_ids if cid not in original_ids],
                    "removed": [cid for cid in original_ids if cid not in current_company_ids],
                }

                if audience_diff["added"] or audience_diff["removed"]:
                    logger.warning(
                        "Scheduled publish: audience changed for document=%d version=%d. "
                        "Diff: added=%s removed=%s",
                        document.id,
                        version.id,
                        audience_diff["added"],
                        audience_diff["removed"],
                    )
                    # Still proceed but log the drift

                # Check for stale companies (deactivated since scheduling)
                stale_companies = (
                    self.db.query(Tenant)
                    .filter(
                        Tenant.id.in_(current_company_ids),
                        Tenant.is_active.is_(False),
                    )
                    .all()
                )

                if stale_companies:
                    stale_ids = [c.id for c in stale_companies]
                    report["failed_stale_company"] += 1
                    report["errors"].append({
                        "version_id": version.id,
                        "document_id": document.id,
                        "reason": f"Stale companies detected: {stale_ids}",
                    })
                    logger.error(
                        "Scheduled publish FAILED: stale companies for document=%d version=%d. "
                        "Stale IDs: %s",
                        document.id,
                        version.id,
                        stale_ids,
                    )
                    continue

                # Re-validate audience readiness
                try:
                    DocumentAggregate(document).ensure_audience_ready_for_submit()
                except Exception as e:
                    report["failed_validation"] += 1
                    report["errors"].append({
                        "version_id": version.id,
                        "document_id": document.id,
                        "reason": str(e),
                    })
                    logger.error(
                        "Scheduled publish FAILED: validation failed for document=%d version=%d. "
                        "Error: %s",
                        document.id,
                        version.id,
                        str(e),
                    )
                    continue

                # Ensure review is still approved at execution time.
                latest_review = self._latest_review_for_version(document.id, version.id)
                if not latest_review or latest_review.status != ReviewStatus.APPROVED:
                    report["failed_validation"] += 1
                    report["errors"].append(
                        {
                            "version_id": version.id,
                            "document_id": document.id,
                            "reason": "Latest review is not approved at scheduled execution time",
                        }
                    )
                    logger.error(
                        "Scheduled publish FAILED: review not approved for document=%d version=%d",
                        document.id,
                        version.id,
                    )
                    continue

                # Capture fresh snapshot
                audience_visibility_snapshot = document.visibility.value if document.visibility else None
                audience_company_ids_snapshot = json.dumps(current_company_ids) if current_company_ids else None

                with UnitOfWork(self.db):
                    version.is_published = True
                    version.published_at = datetime.utcnow()
                    version.scheduled_publish_at = None  # Clear schedule
                    version.audience_visibility_snapshot = audience_visibility_snapshot
                    version.audience_company_ids_snapshot = audience_company_ids_snapshot

                    DocumentAggregate(document).transition_to_active()

                    self.db.add(
                        AuditLog(
                            user_id=None,  # System action
                            document_id=document.id,
                            action=ActionType.UPDATE,
                            details=(
                                f"SCHEDULED PUBLISH completed - Version {version.version_number}. "
                                f"Audience revalidated at publish time."
                            ),
                        )
                    )

                    self.event_dispatcher.dispatch(
                        DocumentPublished(
                            document_id=document.id,
                            version_id=version.id,
                            document_title=document.title,
                            document_number=document.document_number,
                            document_url=f"{settings.BASE_URL}/viewer/documents/{document.id}",
                            document_author_id=document.created_by,
                            published_by_user_id=None,  # System scheduled publish
                        )
                    )

                report["published"] += 1
                logger.info(
                    "Scheduled publish SUCCESS for document=%d version=%d",
                    document.id,
                    version.id,
                )

            except Exception as e:
                report["errors"].append({
                    "version_id": version.id,
                    "document_id": document.id if document else None,
                    "reason": str(e),
                })
                logger.exception(
                    "Scheduled publish ERROR for version=%d: %s",
                    version.id,
                    str(e),
                )

        return report
