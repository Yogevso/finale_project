"""Version Service - Business logic for document versions"""

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import joinedload

from app.config import settings
from app.domain.aggregates import DocumentAggregate
from app.domain.events import DocumentPublished, InProcessDomainEventDispatcher
from app.domain.factories import VersionFactory
from app.domain.states import version_review_stage_for
from app.errors import ConflictError, InvalidStateError, NotFoundError, PermissionDeniedError
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

        version = self.version_repository.get_by_id_for_document(
            version_id,
            document_id,
            include_users=True,
        )

        if not version:
            raise NotFoundError("Version not found")

        if version.is_published:
            raise InvalidStateError("Version is already published")

        if current_user.role not in [UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER]:
            raise PermissionDeniedError("Only admins and managers can publish versions")

        latest_review = self._latest_review_for_version(document_id, version_id)
        version_review_stage_for(
            latest_review.status if latest_review else None
        ).ensure_publishable_for_version()

        with UnitOfWork(self.db):
            version.is_published = True
            version.published_at = datetime.utcnow()
            version.published_by = current_user.id

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

        self.db.refresh(version)

        version = self.version_repository.get_by_id_for_document(
            version_id,
            document_id,
            include_users=True,
        )
        latest_review = self._latest_review_for_version(document_id, version_id)
        return VersionService._serialize_version(version, latest_review)

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
