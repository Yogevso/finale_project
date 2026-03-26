"""Publication workflows for document versions."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import datetime

from app.config import settings
from app.domain.aggregates import DocumentAggregate
from app.domain.events import DocumentPublished, InProcessDomainEventDispatcher
from app.domain.states import version_review_stage_for
from app.errors import (
    InvalidStateError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.feature_flags import BackendFeatureFlag, is_backend_feature_enabled
from app.models import (
    ActionType,
    Attachment,
    AudienceEventType,
    Document,
    NotificationType,
    ReviewRequest,
    ReviewStatus,
    Tenant,
    User,
    UserRole,
)
from app.repositories import VersionRepository
from app.services.audit_helper import write_audit_log
from app.services.notification_service import NotificationService
from app.services.outbox import build_outbox_event_dispatcher
from app.services.uow import UnitOfWork

logger = logging.getLogger(__name__)


def _snapshot_document_audience(document: Document) -> tuple[str | None, str | None]:
    company_ids = [company.id for company in (document.assigned_companies or [])]
    visibility = document.visibility.value if document.visibility else None
    company_ids_snapshot = json.dumps(company_ids) if company_ids else None
    return visibility, company_ids_snapshot


class VersionPublicationService:
    """Handle publish and force-publish workflows for versions."""

    def __init__(
        self,
        db,
        *,
        version_repository: VersionRepository,
        notification_service: NotificationService,
        event_dispatcher: InProcessDomainEventDispatcher | None = None,
        get_document_for_user: Callable[[int, User], Document],
        latest_review_for_version: Callable[[int, int], ReviewRequest | None],
        actor_display_name: Callable[[User], str],
        notify_version_watchers: Callable[..., None],
        schedule_pdf_export_generation: Callable[[list[int]], None],
        run_publish_audience_validation_gate: Callable[[Document], None],
        is_company_audience_enforcement_enabled: Callable[..., bool],
        serialize_version: Callable[..., dict],
    ) -> None:
        self.db = db
        self.version_repository = version_repository
        self.notification_service = notification_service
        self.event_dispatcher = event_dispatcher or build_outbox_event_dispatcher(db)
        self.get_document_for_user = get_document_for_user
        self.latest_review_for_version = latest_review_for_version
        self.actor_display_name = actor_display_name
        self.notify_version_watchers = notify_version_watchers
        self.schedule_pdf_export_generation = schedule_pdf_export_generation
        self.run_publish_audience_validation_gate = run_publish_audience_validation_gate
        self.is_company_audience_enforcement_enabled = (
            is_company_audience_enforcement_enabled
        )
        self.serialize_version = serialize_version

    def _capture_attachment_snapshot(
        self,
        *,
        document_id: int,
        publish_cutoff: datetime,
    ) -> list[int]:
        rows = (
            self.db.query(Attachment.id)
            .filter(
                Attachment.document_id == document_id,
                Attachment.uploaded_at <= publish_cutoff,
            )
            .all()
        )
        return [attachment_id for (attachment_id,) in rows]

    def publish_version(self, document_id: int, version_id: int, current_user: User) -> dict:
        """Publish a reviewed version and emit post-publish side effects."""
        document = self.get_document_for_user(document_id, current_user)
        actor_display_name = self.actor_display_name(current_user)
        self.db.refresh(document, attribute_names=["assigned_companies"])

        audience_warnings: list[str] = []
        enforce_company_audience = self.is_company_audience_enforcement_enabled(
            rollout_key=document.tenant_id
        )
        safe_mode_enabled = is_backend_feature_enabled(
            BackendFeatureFlag.AUDIENCE_VALIDATION_SAFE_MODE
        )

        version = self.version_repository.get_by_id_for_document(
            version_id,
            document_id,
            include_users=True,
        )
        if not version:
            raise NotFoundError("Version not found")

        audience_visibility_snapshot, audience_company_ids_snapshot = _snapshot_document_audience(
            document
        )

        if version.is_published:
            if (
                version.audience_visibility_snapshot == audience_visibility_snapshot
                and version.audience_company_ids_snapshot == audience_company_ids_snapshot
            ):
                logger.info(
                    "Idempotent publish retry for document=%d version=%d - already published with matching audience",
                    document_id,
                    version_id,
                )
                latest_review = self.latest_review_for_version(document_id, version_id)
                return self.serialize_version(version, latest_review, warnings=[])

            raise InvalidStateError(
                "Version is already published with different audience state. "
                "Current audience does not match published snapshot."
            )

        if current_user.role not in [UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER]:
            raise PermissionDeniedError("Only admins and managers can publish versions")

        company_ids = json.loads(audience_company_ids_snapshot) if audience_company_ids_snapshot else []
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
                stale_names = [company.name for company in stale_companies]
                if enforce_company_audience:
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

                warning_message = (
                    "Audience enforcement disabled: proceeding despite deactivated companies "
                    f"in audience ({stale_names})."
                )
                audience_warnings.append(warning_message)
                logger.warning(
                    "Publish advisory for document=%d version=%d: %s",
                    document_id,
                    version_id,
                    warning_message,
                )

        latest_review = self.latest_review_for_version(document_id, version_id)
        version_review_stage_for(
            latest_review.status if latest_review else None
        ).ensure_publishable_for_version()

        if latest_review.reviewer and not latest_review.reviewer.is_active:
            raise ValidationError(
                "The reviewer who approved this version has been deactivated. "
                "Please request a new review before publishing."
            )

        try:
            self.run_publish_audience_validation_gate(document)
        except ValidationError as exc:
            if enforce_company_audience:
                raise

            warning_message = (
                "Audience enforcement disabled: proceeding with advisory warning - "
                f"{exc}"
            )
            audience_warnings.append(warning_message)
            logger.warning(
                "Publish advisory for document=%d version=%d: %s",
                document_id,
                version_id,
                warning_message,
            )
        except (ConnectionError, TimeoutError) as exc:
            if not safe_mode_enabled:
                raise InvalidStateError(
                    "Audience validation service is unavailable; publish blocked."
                ) from exc

            warning_message = (
                "Audience validation service unreachable; safe-mode fallback allowed publish."
            )
            audience_warnings.append(warning_message)
            logger.warning(
                "Publish safe-mode fallback for document=%d version=%d: %s",
                document_id,
                version_id,
                warning_message,
            )

        attachment_ids: list[int] = []
        try:
            with UnitOfWork(self.db):
                version.is_published = True
                version.published_at = datetime.utcnow()
                version.published_by = current_user.id
                version.audience_visibility_snapshot = audience_visibility_snapshot
                version.audience_company_ids_snapshot = audience_company_ids_snapshot

                attachment_ids = self._capture_attachment_snapshot(
                    document_id=document.id,
                    publish_cutoff=version.published_at,
                )
                version.published_attachment_ids_snapshot = (
                    json.dumps(attachment_ids) if attachment_ids else None
                )

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
                if audience_warnings:
                    write_audit_log(
                        user_id=current_user.id,
                        document_id=document.id,
                        action=ActionType.PUBLISH,
                        audience_event_type=AudienceEventType.AUDIENCE_SNAPSHOT_TAKEN,
                        details=json.dumps(
                            {
                                "event": "publish_with_advisory_audience_warnings",
                                "warnings": audience_warnings,
                            },
                            sort_keys=True,
                        ),
                    )
        except Exception as exc:  # policy: FAIL_FAST — publish must succeed or abort
            logger.error(
                "Publish failed for document=%d version=%d user=%d. "
                "Audience state at failure: visibility=%s, companies=%s. Error: %s",
                document_id,
                version_id,
                current_user.id,
                audience_visibility_snapshot,
                audience_company_ids_snapshot,
                str(exc),
            )
            raise

        self.db.refresh(version)

        if attachment_ids:
            self.schedule_pdf_export_generation(attachment_ids)

        self.notify_version_watchers(
            document=document,
            current_user=current_user,
            notification_type=NotificationType.DOCUMENT_PUBLISHED,
            title=f"{actor_display_name} published a document you follow",
            message=document.title,
            link=f"/documents/{document.id}",
        )

        version = self.version_repository.get_by_id_for_document(
            version_id,
            document_id,
            include_users=True,
        )
        latest_review = self.latest_review_for_version(document_id, version_id)
        return self.serialize_version(version, latest_review, warnings=audience_warnings)

    def force_publish_version(
        self,
        document_id: int,
        version_id: int,
        current_user: User,
        reason: str,
        acknowledge_risks: bool,
    ) -> dict:
        """Force publish a version with explicit system-admin override."""
        if current_user.role != UserRole.SYSTEM_ADMIN:
            raise PermissionDeniedError("Only system admins can force publish versions")
        if not acknowledge_risks:
            raise InvalidStateError("Must acknowledge risks to force publish")
        if len(reason) < 10:
            raise InvalidStateError("Reason must be at least 10 characters")

        document = self.get_document_for_user(document_id, current_user)
        self.db.refresh(document, attribute_names=["assigned_companies"])

        version = self.version_repository.get_by_id_for_document(
            version_id,
            document_id,
            include_users=True,
        )
        if not version:
            raise NotFoundError("Version not found")

        if version.is_published:
            return {
                "version_id": version.id,
                "document_id": document_id,
                "published_at": version.published_at.isoformat() if version.published_at else None,
                "forced_by_user_id": current_user.id,
                "reason": reason,
                "warnings_overridden": ["Version was already published"],
            }

        warnings_overridden: list[str] = []

        latest_review = self.latest_review_for_version(document_id, version_id)
        if not latest_review or latest_review.status != ReviewStatus.APPROVED:
            warnings_overridden.append("No approved review - bypassing review requirement")

        try:
            DocumentAggregate(document).ensure_audience_ready_for_submit()
        except Exception as exc:  # policy: LOSSY — advisory only during force publish
            warnings_overridden.append(f"Audience validation failed: {str(exc)}")

        audience_visibility_snapshot, audience_company_ids_snapshot = _snapshot_document_audience(
            document
        )

        with UnitOfWork(self.db):
            version.is_published = True
            version.published_at = datetime.utcnow()
            version.published_by = current_user.id
            version.audience_visibility_snapshot = audience_visibility_snapshot
            version.audience_company_ids_snapshot = audience_company_ids_snapshot

            DocumentAggregate(document).transition_to_active()

            write_audit_log(
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

        actor_display_name = self.actor_display_name(current_user)
        self.notify_version_watchers(
            document=document,
            current_user=current_user,
            notification_type=NotificationType.DOCUMENT_PUBLISHED,
            title=f"{actor_display_name} force-published a document you follow",
            message=document.title,
            link=f"/documents/{document.id}",
        )

        logger.warning(
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
