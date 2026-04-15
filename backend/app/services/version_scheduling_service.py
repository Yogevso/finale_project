"""Scheduled publication workflows for document versions."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import datetime

from sqlalchemy.orm import joinedload

from app.config import settings
from app.domain.aggregates import DocumentAggregate
from app.domain.events import DocumentPublished, InProcessDomainEventDispatcher
from app.errors import InvalidStateError, NotFoundError, ValidationError
from app.models import ActionType, Document, ReviewRequest, ReviewStatus, Tenant, User, Version
from app.repositories import VersionRepository
from app.services.audit_helper import write_audit_log
from app.services.outbox import build_outbox_event_dispatcher
from app.services.uow import UnitOfWork

logger = logging.getLogger(__name__)


def _snapshot_document_audience(document: Document) -> tuple[str | None, str | None]:
    company_ids = [company.id for company in (document.assigned_companies or [])]
    visibility = document.visibility.value if document.visibility else None
    company_ids_snapshot = json.dumps(company_ids) if company_ids else None
    return visibility, company_ids_snapshot


class VersionSchedulingService:
    """Handle schedule/cancel/process workflows for version publication."""

    def __init__(
        self,
        db,
        *,
        version_repository: VersionRepository,
        event_dispatcher: InProcessDomainEventDispatcher | None = None,
        get_document_for_user: Callable[[int, User], Document],
        latest_review_for_version: Callable[[int, int], ReviewRequest | None],
    ) -> None:
        self.db = db
        self.version_repository = version_repository
        self.event_dispatcher = event_dispatcher or build_outbox_event_dispatcher(db)
        self.get_document_for_user = get_document_for_user
        self.latest_review_for_version = latest_review_for_version

    def schedule_publish(
        self,
        document_id: int,
        version_id: int,
        scheduled_at: datetime,
        current_user: User,
    ) -> dict:
        """Schedule a version to be published later."""
        document = self.get_document_for_user(document_id, current_user)
        version = self.version_repository.get_by_id_for_document(
            version_id,
            document_id,
            include_users=True,
        )
        if not version:
            raise NotFoundError("Version not found")
        if version.is_published:
            raise InvalidStateError("Version is already published")
        if scheduled_at <= datetime.utcnow():
            raise InvalidStateError("Scheduled time must be in the future")

        try:
            DocumentAggregate(document).ensure_audience_ready_for_submit()
        except ValidationError as exc:
            raise InvalidStateError(f"Audience validation failed: {exc}") from exc

        latest_review = self.latest_review_for_version(document_id, version_id)
        if not latest_review or latest_review.status != ReviewStatus.APPROVED:
            raise InvalidStateError("Cannot schedule publish: latest review is not approved")

        scheduled_visibility_snapshot, scheduled_company_ids_snapshot = _snapshot_document_audience(
            document
        )

        with UnitOfWork(self.db):
            version.scheduled_publish_at = scheduled_at
            version.scheduled_publish_audience_validated_at = datetime.utcnow()
            version.audience_visibility_snapshot = scheduled_visibility_snapshot
            version.audience_company_ids_snapshot = scheduled_company_ids_snapshot

            write_audit_log(
                user_id=current_user.id,
                document_id=document_id,
                action=ActionType.UPDATE,
                details=(
                    f"Scheduled publish for version {version.version_number} "
                    f"at {scheduled_at.isoformat()}. "
                    f"Audience validated and snapshot captured at schedule time."
                ),
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
        self.get_document_for_user(document_id, current_user)
        version = self.version_repository.get_by_id_for_document(
            version_id,
            document_id,
            include_users=True,
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

            write_audit_log(
                user_id=current_user.id,
                document_id=document_id,
                action=ActionType.UPDATE,
                details=(
                    f"Cancelled scheduled publish for version {version.version_number}. "
                    f"Was scheduled for {old_scheduled_at.isoformat()}."
                ),
            )

        return {
            "version_id": version.id,
            "document_id": document_id,
            "cancelled_scheduled_at": old_scheduled_at.isoformat(),
        }

    def process_scheduled_publishes(self, batch_size: int = 10) -> dict:
        """Process scheduled publishes that are due."""
        due_versions = (
            self.db.query(Version)
            .options(joinedload(Version.document))
            .filter(
                Version.scheduled_publish_at <= datetime.utcnow(),
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
                audience_visibility_snapshot, audience_company_ids_snapshot = (
                    _snapshot_document_audience(document)
                )
                current_company_ids = (
                    json.loads(audience_company_ids_snapshot)
                    if audience_company_ids_snapshot
                    else []
                )
                original_ids = (
                    json.loads(version.audience_company_ids_snapshot)
                    if version.audience_company_ids_snapshot
                    else []
                )
                audience_diff = {
                    "added": [
                        company_id
                        for company_id in current_company_ids
                        if company_id not in original_ids
                    ],
                    "removed": [
                        company_id
                        for company_id in original_ids
                        if company_id not in current_company_ids
                    ],
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

                stale_companies = (
                    self.db.query(Tenant)
                    .filter(
                        Tenant.id.in_(current_company_ids),
                        Tenant.is_active.is_(False),
                    )
                    .all()
                )
                if stale_companies:
                    stale_ids = [company.id for company in stale_companies]
                    report["failed_stale_company"] += 1
                    report["errors"].append(
                        {
                            "version_id": version.id,
                            "document_id": document.id,
                            "reason": f"Stale companies detected: {stale_ids}",
                        }
                    )
                    logger.error(
                        "Scheduled publish FAILED: stale companies for document=%d version=%d. "
                        "Stale IDs: %s",
                        document.id,
                        version.id,
                        stale_ids,
                    )
                    continue

                try:
                    DocumentAggregate(document).ensure_audience_ready_for_submit()
                except Exception as exc:  # policy: FAIL_FAST — skip this item, continue batch
                    report["failed_validation"] += 1
                    report["errors"].append(
                        {
                            "version_id": version.id,
                            "document_id": document.id,
                            "reason": str(exc),
                        }
                    )
                    logger.error(
                        "Scheduled publish FAILED: validation failed for document=%d version=%d. "
                        "Error: %s",
                        document.id,
                        version.id,
                        str(exc),
                    )
                    continue

                latest_review = self.latest_review_for_version(document.id, version.id)
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

                with UnitOfWork(self.db):
                    version.is_published = True
                    version.published_at = datetime.utcnow()
                    version.scheduled_publish_at = None
                    version.audience_visibility_snapshot = audience_visibility_snapshot
                    version.audience_company_ids_snapshot = audience_company_ids_snapshot

                    DocumentAggregate(document).transition_to_active()

                    write_audit_log(
                        user_id=None,
                        document_id=document.id,
                        action=ActionType.UPDATE,
                        details=(
                            f"SCHEDULED PUBLISH completed - Version {version.version_number}. "
                            f"Audience revalidated at publish time."
                        ),
                    )

                    self.event_dispatcher.dispatch(
                        DocumentPublished(
                            document_id=document.id,
                            version_id=version.id,
                            document_title=document.title,
                            document_number=document.document_number,
                            document_url=f"{settings.BASE_URL}/viewer/documents/{document.id}",
                            document_author_id=document.created_by,
                            published_by_user_id=None,
                        )
                    )

                report["published"] += 1
                logger.info(
                    "Scheduled publish SUCCESS for document=%d version=%d",
                    document.id,
                    version.id,
                )
            except (
                Exception
            ) as exc:  # policy: COMPENSATING — record error, skip item, continue batch
                report["errors"].append(
                    {
                        "version_id": version.id,
                        "document_id": document.id if document else None,
                        "reason": str(exc),
                    }
                )
                logger.exception(
                    "Scheduled publish ERROR for version=%d: %s",
                    version.id,
                    str(exc),
                )

        return report
