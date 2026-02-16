"""Document Service"""

import re
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies.tenant import TenantContext
from app.models import (
    ActionType,
    AuditLog,
    Document,
    DocumentStatus,
    Platform,
    User,
    UserRole,
    Version,
    VersionBumpType,
)
from app.schemas import DocumentCreate, DocumentUpdate


class DocumentService:
    """Document CRUD service with multi-tenancy support"""

    def __init__(self, db: Session, tenant_ctx: Optional[TenantContext] = None):
        self.db = db
        self.tenant_ctx = tenant_ctx

    def _base_query(self):
        """Base query with tenant filtering applied"""
        query = self.db.query(Document)

        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            query = query.filter(Document.tenant_id == self.tenant_ctx.tenant_id)

        return query

    def _verify_access(self, document: Document) -> None:
        """Verify current user can access this document"""
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        if self.tenant_ctx and not self.tenant_ctx.is_system_admin:
            if document.tenant_id != self.tenant_ctx.tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
                )

    def generate_document_number(self) -> str:
        """Generate unique document number (DOC-YYYYMMDD-XXXX)"""
        from datetime import datetime

        today = datetime.utcnow().strftime("%Y%m%d")
        prefix = f"DOC-{today}"

        # Find the next available sequence for today (global, since document_number is globally unique)
        existing = (
            self.db.query(Document)
            .filter(Document.document_number.like(f"{prefix}-%"))
            .with_entities(Document.document_number)
            .all()
        )

        used_numbers = set()
        for (doc_number,) in existing:
            try:
                suffix = int(doc_number.split("-")[-1])
                used_numbers.add(suffix)
            except (ValueError, IndexError):
                continue

        next_seq = 1
        while next_seq in used_numbers:
            next_seq += 1

        return f"{prefix}-{next_seq:04d}"

    @staticmethod
    def _parse_semver(
        raw_value: Optional[str], fallback_version_number: int
    ) -> Tuple[int, int, int]:
        if raw_value:
            parts = raw_value.strip().split(".")
            if len(parts) == 3 and all(part.isdigit() for part in parts):
                return int(parts[0]), int(parts[1]), int(parts[2])
        base = fallback_version_number if fallback_version_number > 0 else 1
        return base, 0, 0

    @staticmethod
    def _next_patch_version(raw_value: Optional[str], fallback_version_number: int) -> str:
        major, minor, patch = DocumentService._parse_semver(raw_value, fallback_version_number)
        return f"{major}.{minor}.{patch + 1}"

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

    def _get_or_create_platform(
        self, platform_name: Optional[str] = None, platform_id: Optional[int] = None
    ) -> Platform:
        if platform_id is not None:
            platform = self.db.query(Platform).filter(Platform.id == platform_id).first()
            if not platform:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Platform {platform_id} not found",
                )
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

    def create_document(self, document_data: DocumentCreate, user: User) -> Document:
        """Create a new document"""
        # Use provided document number or generate one
        if document_data.document_number:
            # document_number is globally unique
            existing = (
                self.db.query(Document)
                .filter(Document.document_number == document_data.document_number)
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Document ID already exists",
                )
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
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Parent document not found"
                )

        platform = self._get_or_create_platform(
            platform_name=document_data.platform, platform_id=document_data.platform_id
        )

        # Create document with retry in case of document_number collision
        attempts = 0
        while True:
            attempts += 1
            document = Document(
                title=document_data.title,
                document_number=document_number,
                description=document_data.description,
                version_label=document_data.version_label,
                status=document_data.status,
                category=document_data.category,
                topic=document_data.topic,
                platform=platform.name,
                platform_id=platform.id,
                release_branch=document_data.release_branch,
                tags=document_data.tags,
                created_by=user.id,
                tenant_id=tenant_id,
                parent_id=parent_id,
            )

            self.db.add(document)
            try:
                self.db.commit()
            except IntegrityError as exc:
                self.db.rollback()
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
            else:
                self.db.refresh(document)
                break

        # Create initial version placeholder. Real content is managed via explicit
        # version edits/uploads, not the document description metadata field.
        version = Version(
            document_id=document.id,
            version_number=1,
            semantic_version="1.0.0",
            bump_type=VersionBumpType.MAJOR,
            content="",
            changes_summary="Initial version",
            created_by=user.id,
        )
        self.db.add(version)

        # Create audit log
        audit = AuditLog(
            user_id=user.id,
            document_id=document.id,
            action=ActionType.CREATE,
            details=f"Created document: {document.title}",
        )
        self.db.add(audit)

        self.db.commit()
        self.db.refresh(document)

        return document

    def get_document(self, document_id: int) -> Optional[Document]:
        """Get document by ID with tenant filtering"""
        document = self._base_query().filter(Document.id == document_id).first()
        return document

    def get_documents(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[DocumentStatus] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[List[Document], int]:
        """Get list of documents with filters, pagination, and tenant filtering"""
        query = self._base_query()

        # Apply filters
        if status:
            query = query.filter(Document.status == status)

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
        self, document_id: int, document_data: DocumentUpdate, user: User
    ) -> Document:
        """Update document with tenant verification"""
        document = self.get_document(document_id)
        self._verify_access(document)

        # Track changes
        changes = []

        # Update fields
        if document_data.title is not None:
            if document.title != document_data.title:
                changes.append(f"Title changed from '{document.title}' to '{document_data.title}'")
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
                if user.role not in (UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Only managers can change document visibility",
                    )
                changes.append(
                    f"Visibility changed from '{document.visibility.value}' to '{document_data.visibility.value}'"
                )
            document.visibility = document_data.visibility

        if document_data.category is not None:
            document.category = document_data.category

        if document_data.topic is not None:
            document.topic = document_data.topic

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

            new_version_number = (latest_version.version_number + 1) if latest_version else 1
            latest_content = (
                latest_version.content if latest_version and latest_version.content else ""
            )
            next_semantic = self._next_patch_version(
                latest_version.semantic_version if latest_version else None,
                latest_version.version_number if latest_version else 1,
            )

            version = Version(
                document_id=document.id,
                version_number=new_version_number,
                semantic_version=next_semantic,
                bump_type=VersionBumpType.PATCH,
                content=latest_content,
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

        self.db.commit()
        self.db.refresh(document)

        return document

    def delete_document(self, document_id: int, user: User) -> None:
        """Delete document with tenant verification"""
        document = self.get_document(document_id)
        self._verify_access(document)

        # Create audit log before deletion
        audit = AuditLog(
            user_id=user.id,
            document_id=document.id,
            action=ActionType.DELETE,
            details=f"Deleted document: {document.title}",
        )
        self.db.add(audit)
        self.db.commit()

        # Delete document (cascade will delete versions, attachments, comments)
        self.db.delete(document)
        self.db.commit()
