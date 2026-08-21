"""Version Service - Business logic for document versions."""

import json
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session, joinedload

from app.conversion.version_toc import derive_version_toc
from app.domain.aggregates import DocumentAggregate
from app.domain.events import InProcessDomainEventDispatcher
from app.domain.factories import VersionFactory
from app.domain.states import version_review_stage_for
from app.errors import (
    ConflictError,
    InvalidStateError,
    NotFoundError,
    PermissionDeniedError,
)
from app.feature_flags import BackendFeatureFlag, is_backend_feature_enabled
from app.models import (
    ActionType,
    AudienceEventType,
    Document,
    NotificationType,
    ReviewRequest,
    ReviewStatus,
    User,
    UserRole,
    Version,
    VersionBumpType,
)
from app.repositories import DocumentRepository, VersionRepository
from app.schemas import VersionCreate, VersionUpdate
from app.services.audit_helper import write_audit_log
from app.services.base_service import SessionService
from app.services.notification_service import NotificationService
from app.services.outbox import build_outbox_event_dispatcher
from app.services.uow import UnitOfWork
from app.services.version_publication_service import VersionPublicationService
from app.services.version_scheduling_service import VersionSchedulingService
from app.utils.concurrency import ensure_if_match_matches

logger = logging.getLogger(__name__)


def _stored_toc(version: Version) -> list[dict]:
    """Read a version's stored contents, tolerating a null or malformed column."""
    raw = getattr(version, "toc_json", None)
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return parsed if isinstance(parsed, list) else []


class VersionService(SessionService):
    """Service for managing document versions"""

    def __init__(
        self,
        db,
        *,
        chat_db: Session | None = None,
        event_dispatcher: InProcessDomainEventDispatcher | None = None,
        document_repository: DocumentRepository | None = None,
        version_repository: VersionRepository | None = None,
        notification_service: NotificationService | None = None,
        publication_service: VersionPublicationService | None = None,
        scheduling_service: VersionSchedulingService | None = None,
    ):
        super().__init__(db)
        self.document_repository = document_repository or DocumentRepository(db)
        self.version_repository = version_repository or VersionRepository(db)
        self.notification_service = notification_service or NotificationService(db, chat_db=chat_db)
        self.event_dispatcher = event_dispatcher or build_outbox_event_dispatcher(db)
        self.publication_service = publication_service or VersionPublicationService(
            db,
            version_repository=self.version_repository,
            notification_service=self.notification_service,
            event_dispatcher=self.event_dispatcher,
            get_document_for_user=self._get_document_for_user,
            latest_review_for_version=self._latest_review_for_version,
            actor_display_name=self._actor_display_name,
            notify_version_watchers=self._notify_version_watchers,
            schedule_pdf_export_generation=self._schedule_pdf_export_generation,
            run_publish_audience_validation_gate=self._run_publish_audience_validation_gate,
            is_company_audience_enforcement_enabled=self._is_company_audience_enforcement_enabled,
            serialize_version=self._serialize_version,
        )
        self.scheduling_service = scheduling_service or VersionSchedulingService(
            db,
            version_repository=self.version_repository,
            event_dispatcher=self.event_dispatcher,
            get_document_for_user=self._get_document_for_user,
            latest_review_for_version=self._latest_review_for_version,
        )

    @staticmethod
    def _actor_display_name(current_user: User) -> str:
        full_name = getattr(current_user, "full_name", None)
        if isinstance(full_name, str) and full_name.strip():
            return full_name.strip()

        username = getattr(current_user, "username", None)
        if isinstance(username, str) and username.strip():
            return username.strip()

        user_id = getattr(current_user, "id", None)
        if isinstance(user_id, int):
            return f"User #{user_id}"

        return "A teammate"

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
    def _serialize_version(
        version: Version,
        latest_review: Optional[ReviewRequest] = None,
        *,
        warnings: list[str] | None = None,
    ) -> dict:
        return {
            "id": version.id,
            "document_id": version.document_id,
            "version_number": version.version_number,
            "semantic_version": version.semantic_version,
            "bump_type": version.bump_type,
            "row_version": version.row_version,
            "etag": version.etag,
            "content": version.content,
            # Built at conversion time and stored beside the content; omitting it
            # here silently drops it from every listing the service serves.
            "toc_items": version.toc_json,
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
            "warnings": list(warnings or []),
        }

    @staticmethod
    def _is_company_audience_enforcement_enabled(*, rollout_key: str | int | None = None) -> bool:
        return is_backend_feature_enabled(
            BackendFeatureFlag.COMPANY_AUDIENCE_ENFORCEMENT,
            rollout_key=rollout_key,
        )

    @staticmethod
    def _run_publish_audience_validation_gate(document: Document) -> None:
        DocumentAggregate(document).ensure_audience_ready_for_submit()

    def _notify_version_mentions(
        self,
        *,
        document: Document,
        version: Version,
        current_user: User,
        content: str | None,
    ) -> set[int]:
        preview_text = " ".join((content or "").split())[:160]
        actor_display_name = self._actor_display_name(current_user)
        return self.notification_service.notify_mentions(
            content=content,
            actor_user=current_user,
            document=document,
            notification_type=NotificationType.DOCUMENT_UPDATED,
            title_builder=lambda _user: f"{actor_display_name} mentioned you in a document draft",
            message_builder=lambda _user: f"{document.title}: {preview_text}"
            if preview_text
            else document.title,
            link=f"/documents/{document.id}?tab=versions&version={version.id}",
        )

    @staticmethod
    def _schedule_pdf_export_generation(attachment_ids: list[int]) -> None:
        """AH-006: Enqueue durable PDF export jobs for portal/viewer downloads."""
        from app.services.conversion_jobs import enqueue_pdf_export

        enqueue_pdf_export(attachment_ids)

    def _notify_version_watchers(
        self,
        *,
        document: Document,
        current_user: User,
        notification_type: NotificationType,
        title: str,
        message: str,
        link: str,
        exclude_user_ids: set[int] | None = None,
    ) -> None:
        self.notification_service.notify_document_watchers(
            document=document,
            actor_user=current_user,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link,
            exclude_user_ids=exclude_user_ids,
        )

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
        actor_display_name = self._actor_display_name(current_user)

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
            mentioned_user_ids = self._notify_version_mentions(
                document=document,
                version=version,
                current_user=current_user,
                content=version.content,
            )
            self._notify_version_watchers(
                document=document,
                current_user=current_user,
                notification_type=NotificationType.DOCUMENT_UPDATED,
                title=f"{actor_display_name} created a draft on a document you follow",
                message=f"{document.title}: {(version.changes_summary or 'Draft version created')[:200]}",
                link=f"/documents/{document.id}?tab=versions",
                exclude_user_ids=mentioned_user_ids,
            )

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
        document = self._get_document_for_user(document_id, current_user)
        actor_display_name = self._actor_display_name(current_user)

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
                # The contents describe the content; rewriting one without the
                # other leaves a review comparing against entries that no longer
                # match the document.
                rebuilt = derive_version_toc(version.content, _stored_toc(version))
                version.toc_json = json.dumps(rebuilt) if rebuilt else None
            if version_data.changes_summary is not None:
                version.changes_summary = version_data.changes_summary
            mentioned_user_ids = self._notify_version_mentions(
                document=document,
                version=version,
                current_user=current_user,
                content=version.content,
            )
            self._notify_version_watchers(
                document=document,
                current_user=current_user,
                notification_type=NotificationType.DOCUMENT_UPDATED,
                title=f"{actor_display_name} updated a draft on a document you follow",
                message=f"{document.title}: {(version.changes_summary or 'Draft version updated')[:200]}",
                link=f"/documents/{document.id}?tab=versions",
                exclude_user_ids=mentioned_user_ids,
            )

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
        return self.publication_service.publish_version(document_id, version_id, current_user)

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

        checks.append(
            {
                "id": "version_exists",
                "label": "Version exists",
                "passed": version_exists,
                "message": None if version_exists else "Version not found",
            }
        )

        # Check 2: Not already published
        if version:
            not_published = not version.is_published
            checks.append(
                {
                    "id": "not_already_published",
                    "label": "Not already published",
                    "passed": not_published,
                    "message": None if not_published else "Version is already published",
                }
            )
        else:
            checks.append(
                {
                    "id": "not_already_published",
                    "label": "Not already published",
                    "passed": False,
                    "message": "Cannot check - version not found",
                }
            )

        # Check 3: User has permission to publish
        can_publish = current_user.role in [
            UserRole.SYSTEM_ADMIN,
            UserRole.ADMIN,
            UserRole.MANAGER,
        ]
        checks.append(
            {
                "id": "user_can_publish",
                "label": "User can publish",
                "passed": can_publish,
                "message": None if can_publish else "Only admins and managers can publish versions",
            }
        )

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

            checks.append(
                {
                    "id": "review_approved",
                    "label": "Review approved",
                    "passed": review_approved,
                    "message": review_message,
                }
            )
        else:
            checks.append(
                {
                    "id": "review_approved",
                    "label": "Review approved",
                    "passed": False,
                    "message": "Cannot check - version not found",
                }
            )

        # Check 5: Audience readiness (company visibility requires at least one company assignment)
        if document:
            if document.visibility == DocumentVisibility.COMPANY:
                has_company_assignments = (
                    document.assigned_companies is not None and len(document.assigned_companies) > 0
                )
                checks.append(
                    {
                        "id": "audience_ready",
                        "label": "Audience configured",
                        "passed": has_company_assignments,
                        "message": (
                            None
                            if has_company_assignments
                            else "Company visibility requires at least one company assignment"
                        ),
                    }
                )
            else:
                # Internal or public visibility doesn't need company assignments
                checks.append(
                    {
                        "id": "audience_ready",
                        "label": "Audience configured",
                        "passed": True,
                        "message": None,
                    }
                )
        else:
            checks.append(
                {
                    "id": "audience_ready",
                    "label": "Audience configured",
                    "passed": False,
                    "message": "Cannot check - document not found",
                }
            )

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
        from app.models import DocumentVisibility, Tenant

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

            write_audit_log(
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
                            cid
                            for cid in [c.id for c in valid_companies]
                            if cid not in old_company_ids
                        ],
                        "removed_company_ids": [
                            cid
                            for cid in old_company_ids
                            if cid not in [c.id for c in valid_companies]
                        ],
                    },
                    sort_keys=True,
                ),
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
        """Force publish a version with admin override."""
        return self.publication_service.force_publish_version(
            document_id,
            version_id,
            current_user,
            reason,
            acknowledge_risks,
        )

    def schedule_publish(
        self,
        document_id: int,
        version_id: int,
        scheduled_at: datetime,
        current_user: User,
    ) -> dict:
        """Schedule a version to be published at a specific time."""
        return self.scheduling_service.schedule_publish(
            document_id,
            version_id,
            scheduled_at,
            current_user,
        )

    def cancel_scheduled_publish(
        self,
        document_id: int,
        version_id: int,
        current_user: User,
    ) -> dict:
        """Cancel a scheduled publish."""
        return self.scheduling_service.cancel_scheduled_publish(
            document_id,
            version_id,
            current_user,
        )

    def process_scheduled_publishes(self, batch_size: int = 10) -> dict:
        """Process scheduled publishes that are due."""
        return self.scheduling_service.process_scheduled_publishes(batch_size=batch_size)
