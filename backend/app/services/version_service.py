"""Version Service - Business logic for document versions"""

import logging
from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import (
    Document,
    DocumentStatus,
    ReviewRequest,
    ReviewStatus,
    User,
    UserRole,
    Version,
    VersionBumpType,
)
from app.schemas import VersionCreate, VersionUpdate
from app.utils.async_tasks import run_async_task

logger = logging.getLogger(__name__)


class VersionService:
    """Service for managing document versions"""

    @staticmethod
    def _get_document_for_user(db: Session, document_id: int, current_user: User) -> Document:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        if (
            current_user.role != UserRole.SYSTEM_ADMIN
            and document.tenant_id != current_user.tenant_id
        ):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        return document

    @staticmethod
    def _parse_semver(
        raw_value: Optional[str], fallback_version_number: int
    ) -> Tuple[int, int, int]:
        """Parse semantic version string (x.y.z), fallback to version_number.0.0."""
        if raw_value:
            parts = raw_value.strip().split(".")
            if len(parts) == 3 and all(part.isdigit() for part in parts):
                return int(parts[0]), int(parts[1]), int(parts[2])
        base = fallback_version_number if fallback_version_number > 0 else 1
        return base, 0, 0

    @staticmethod
    def _format_semver(major: int, minor: int, patch: int) -> str:
        return f"{major}.{minor}.{patch}"

    @staticmethod
    def _bump_semver(previous: Tuple[int, int, int], bump_type: VersionBumpType) -> str:
        major, minor, patch = previous
        if bump_type == VersionBumpType.MAJOR:
            return VersionService._format_semver(major + 1, 0, 0)
        if bump_type == VersionBumpType.MINOR:
            return VersionService._format_semver(major, minor + 1, 0)
        return VersionService._format_semver(major, minor, patch + 1)

    @staticmethod
    def _latest_review_for_version(
        db: Session, document_id: int, version_id: int
    ) -> Optional[ReviewRequest]:
        """Get latest review record for a document version."""
        return (
            db.query(ReviewRequest)
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

    @staticmethod
    def _latest_reviews_for_versions(
        db: Session, document_id: int, version_ids: List[int]
    ) -> dict[int, ReviewRequest]:
        """Get latest review record per version id."""
        if not version_ids:
            return {}

        rows = (
            db.query(ReviewRequest)
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

    @staticmethod
    def get_versions(db: Session, document_id: int, current_user: User) -> List[dict]:
        """Get all versions for a document"""
        VersionService._get_document_for_user(db, document_id, current_user)

        versions = (
            db.query(Version)
            .options(
                joinedload(Version.created_by_user),
                joinedload(Version.published_by_user),
            )
            .filter(Version.document_id == document_id)
            .order_by(Version.version_number.desc())
            .all()
        )
        latest_reviews = VersionService._latest_reviews_for_versions(
            db, document_id, [v.id for v in versions]
        )
        return [VersionService._serialize_version(v, latest_reviews.get(v.id)) for v in versions]

    @staticmethod
    def get_version(db: Session, document_id: int, version_id: int, current_user: User) -> dict:
        """Get a specific version"""
        VersionService._get_document_for_user(db, document_id, current_user)

        version = (
            db.query(Version)
            .options(
                joinedload(Version.created_by_user),
                joinedload(Version.published_by_user),
            )
            .filter(Version.id == version_id, Version.document_id == document_id)
            .first()
        )

        if not version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

        latest_review = VersionService._latest_review_for_version(db, document_id, version_id)
        return VersionService._serialize_version(version, latest_review)

    @staticmethod
    def create_version(
        db: Session, document_id: int, version_data: VersionCreate, current_user: User
    ) -> dict:
        """Create a new version for a document"""
        document = VersionService._get_document_for_user(db, document_id, current_user)

        if current_user.role not in [
            UserRole.SYSTEM_ADMIN,
            UserRole.ADMIN,
            UserRole.MANAGER,
            UserRole.EDITOR,
        ]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins, managers and editors can create versions",
            )

        pending_review = (
            db.query(ReviewRequest)
            .filter(
                ReviewRequest.document_id == document_id,
                ReviewRequest.status == ReviewStatus.PENDING,
            )
            .first()
        )
        if pending_review:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot create a new version while a review is pending",
            )

        last_version = (
            db.query(Version)
            .filter(Version.document_id == document_id)
            .order_by(Version.version_number.desc())
            .first()
        )

        next_version_number = 1 if not last_version else last_version.version_number + 1
        previous_semver = VersionService._parse_semver(
            last_version.semantic_version if last_version else None,
            last_version.version_number if last_version else 1,
        )
        bump_type = version_data.bump_type or VersionBumpType.PATCH
        next_semantic_version = (
            "1.0.0" if not last_version else VersionService._bump_semver(previous_semver, bump_type)
        )

        version = Version(
            document_id=document_id,
            version_number=next_version_number,
            semantic_version=next_semantic_version,
            bump_type=bump_type,
            content=version_data.content,
            changes_summary=version_data.changes_summary,
            created_by=current_user.id,
            is_published=False,
        )

        db.add(version)
        # Keep already-published documents publicly available while drafting the next candidate.
        if document.status not in [DocumentStatus.DRAFT, DocumentStatus.ACTIVE]:
            document.status = DocumentStatus.DRAFT
        db.commit()

        version = (
            db.query(Version)
            .options(
                joinedload(Version.created_by_user),
                joinedload(Version.published_by_user),
            )
            .filter(Version.id == version.id)
            .first()
        )
        return VersionService._serialize_version(version)

    @staticmethod
    def update_version(
        db: Session,
        document_id: int,
        version_id: int,
        version_data: VersionUpdate,
        current_user: User,
    ) -> dict:
        """Update an unpublished version"""
        VersionService._get_document_for_user(db, document_id, current_user)

        version = (
            db.query(Version)
            .options(
                joinedload(Version.created_by_user),
                joinedload(Version.published_by_user),
            )
            .filter(Version.id == version_id, Version.document_id == document_id)
            .first()
        )

        if not version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

        if version.is_published:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify published version - versions are immutable after publishing",
            )

        latest_review = VersionService._latest_review_for_version(db, document_id, version_id)
        if latest_review and latest_review.status == ReviewStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot modify version while it has a pending review",
            )
        if latest_review and latest_review.status == ReviewStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot modify an approved version. Create a new version instead.",
            )

        if current_user.role not in [
            UserRole.SYSTEM_ADMIN,
            UserRole.ADMIN,
            UserRole.MANAGER,
            UserRole.EDITOR,
        ]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins, managers and editors can update versions",
            )

        if version_data.content is not None:
            version.content = version_data.content
        if version_data.changes_summary is not None:
            version.changes_summary = version_data.changes_summary

        db.commit()
        db.refresh(version)

        latest_review = VersionService._latest_review_for_version(db, document_id, version_id)
        return VersionService._serialize_version(version, latest_review)

    @staticmethod
    def publish_version(db: Session, document_id: int, version_id: int, current_user: User) -> dict:
        """Publish a version (requires approval and makes it immutable)."""
        VersionService._get_document_for_user(db, document_id, current_user)

        version = (
            db.query(Version)
            .options(
                joinedload(Version.created_by_user),
                joinedload(Version.published_by_user),
            )
            .filter(Version.id == version_id, Version.document_id == document_id)
            .first()
        )

        if not version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

        if version.is_published:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Version is already published"
            )

        if current_user.role not in [UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins and managers can publish versions",
            )

        latest_review = VersionService._latest_review_for_version(db, document_id, version_id)
        if not latest_review:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot publish without an approved review for this version",
            )
        if latest_review.status == ReviewStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot publish version while review is pending",
            )
        if latest_review.status != ReviewStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot publish version that is not approved. Submit and approve review first.",
            )

        version.is_published = True
        version.published_at = datetime.utcnow()
        version.published_by = current_user.id

        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.status = DocumentStatus.ACTIVE

        db.commit()
        db.refresh(version)

        try:
            from app.services.email_service import email_service

            if document and settings.EMAIL_ENABLED:
                author = db.query(User).filter(User.id == document.created_by).first()
                if author and author.email:
                    run_async_task(
                        email_service.send_document_published(
                            to_email=author.email,
                            document_title=document.title,
                            document_number=document.document_number,
                            document_url=f"{settings.BASE_URL}/viewer/documents/{document.id}",
                        )
                    )
                    logger.info(f"Queued publish notification for document {document.id}")
        except Exception as e:
            logger.warning(f"Failed to send publish notification: {e}")

        version = (
            db.query(Version)
            .options(
                joinedload(Version.created_by_user),
                joinedload(Version.published_by_user),
            )
            .filter(Version.id == version_id, Version.document_id == document_id)
            .first()
        )
        latest_review = VersionService._latest_review_for_version(db, document_id, version_id)
        return VersionService._serialize_version(version, latest_review)

    @staticmethod
    def delete_version(db: Session, document_id: int, version_id: int, current_user: User) -> None:
        """Delete an unpublished version"""
        VersionService._get_document_for_user(db, document_id, current_user)

        version = (
            db.query(Version)
            .filter(Version.id == version_id, Version.document_id == document_id)
            .first()
        )

        if not version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

        if version.is_published:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete published version"
            )

        if current_user.role not in [UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins and managers can delete versions",
            )

        db.delete(version)
        db.commit()

    @staticmethod
    def get_latest_published(db: Session, document_id: int) -> Optional[Version]:
        """Get the latest published version for a document"""
        return (
            db.query(Version)
            .filter(
                Version.document_id == document_id,
                Version.is_published == True,  # noqa: E712
            )
            .order_by(Version.version_number.desc())
            .first()
        )
