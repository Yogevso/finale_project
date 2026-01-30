"""Version Service - Business logic for document versions"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Document, DocumentStatus, User, UserRole, Version
from app.schemas import VersionCreate, VersionUpdate

logger = logging.getLogger(__name__)


class VersionService:
    """Service for managing document versions"""

    @staticmethod
    def get_versions(db: Session, document_id: int, current_user: User) -> List[Version]:
        """Get all versions for a document"""
        # Check document exists
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        return (
            db.query(Version)
            .filter(Version.document_id == document_id)
            .order_by(Version.version_number.desc())
            .all()
        )

    @staticmethod
    def get_version(db: Session, document_id: int, version_id: int, current_user: User) -> Version:
        """Get a specific version"""
        version = (
            db.query(Version)
            .filter(Version.id == version_id, Version.document_id == document_id)
            .first()
        )

        if not version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

        return version

    @staticmethod
    def create_version(
        db: Session, document_id: int, version_data: VersionCreate, current_user: User
    ) -> Version:
        """Create a new version for a document"""
        # Check document exists
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        # Only system_admin, admin, manager or editor can create versions
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

        # Get next version number
        last_version = (
            db.query(Version)
            .filter(Version.document_id == document_id)
            .order_by(Version.version_number.desc())
            .first()
        )

        next_version_number = 1 if not last_version else last_version.version_number + 1

        # Create version
        version = Version(
            document_id=document_id,
            version_number=next_version_number,
            content=version_data.content,
            changes_summary=version_data.changes_summary,
            created_by=current_user.id,
            is_published=False,
        )

        db.add(version)
        db.commit()
        db.refresh(version)

        return version

    @staticmethod
    def update_version(
        db: Session,
        document_id: int,
        version_id: int,
        version_data: VersionUpdate,
        current_user: User,
    ) -> Version:
        """Update an unpublished version"""
        version = (
            db.query(Version)
            .filter(Version.id == version_id, Version.document_id == document_id)
            .first()
        )

        if not version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

        # Cannot update published versions (immutable)
        if version.is_published:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify published version - versions are immutable after publishing",
            )

        # Only system_admin, admin, manager or editor can update
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

        # Update fields
        if version_data.content is not None:
            version.content = version_data.content
        if version_data.changes_summary is not None:
            version.changes_summary = version_data.changes_summary

        db.commit()
        db.refresh(version)

        return version

    @staticmethod
    def publish_version(
        db: Session, document_id: int, version_id: int, current_user: User
    ) -> Version:
        """Publish a version (makes it immutable)"""
        version = (
            db.query(Version)
            .filter(Version.id == version_id, Version.document_id == document_id)
            .first()
        )

        if not version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

        if version.is_published:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Version is already published"
            )

        # Only system_admin, admin or manager can publish
        if current_user.role not in [UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins and managers can publish versions",
            )

        version.is_published = True
        version.published_at = datetime.utcnow()

        # Update document status to active
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.status = DocumentStatus.ACTIVE

        db.commit()
        db.refresh(version)

        # Send email notification (async, fire-and-forget)
        try:
            from app.services.email_service import email_service

            if document and settings.EMAIL_ENABLED:
                # Get document author email
                author = db.query(User).filter(User.id == document.created_by).first()
                if author and author.email:
                    import asyncio

                    asyncio.create_task(
                        email_service.send_document_published(
                            to_email=author.email,
                            document_title=document.title,
                            document_url=f"{settings.BASE_URL}/viewer/documents/{document.id}",
                        )
                    )
                    logger.info(f"Queued publish notification for document {document.id}")
        except Exception as e:
            # Don't fail publish if email fails
            logger.warning(f"Failed to send publish notification: {e}")

        return version

    @staticmethod
    def delete_version(db: Session, document_id: int, version_id: int, current_user: User) -> None:
        """Delete an unpublished version"""
        version = (
            db.query(Version)
            .filter(Version.id == version_id, Version.document_id == document_id)
            .first()
        )

        if not version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

        # Cannot delete published versions
        if version.is_published:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete published version"
            )

        # Only system_admin, admin or manager can delete
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
