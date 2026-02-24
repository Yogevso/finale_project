"""Document Service"""

import re
from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies.tenant import TenantContext
from app.models import (
    ActionType,
    AuditLog,
    Document,
    DocumentNumberSequence,
    DocumentStatus,
    Platform,
    Topic,
    User,
    UserRole,
    Version,
    VersionBumpType,
)
from app.schemas import DocumentCreate, DocumentUpdate
from app.utils.topic_normalization import build_topic_lookup, normalize_topic_to_slug


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

    @staticmethod
    def _extract_sequence_suffix(document_number: str, prefix: str) -> Optional[int]:
        expected_prefix = f"{prefix}-"
        if not document_number or not document_number.startswith(expected_prefix):
            return None

        suffix = document_number[len(expected_prefix) :]
        if not suffix.isdigit():
            return None
        return int(suffix)

    def _discover_max_existing_suffix(self, prefix: str) -> int:
        existing = (
            self.db.query(Document.document_number)
            .filter(Document.document_number.like(f"{prefix}-%"))
            .all()
        )
        max_suffix = 0
        for (document_number,) in existing:
            suffix = self._extract_sequence_suffix(document_number, prefix)
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
        prefix = f"DOC-{date_key}"

        if self.db.get(DocumentNumberSequence, date_key) is None:
            seed_sequence = self._discover_max_existing_suffix(prefix)
            self._insert_sequence_row_if_missing(date_key, seed_sequence)

        next_sequence = self._reserve_document_sequence(date_key)
        return f"{prefix}-{next_sequence:04d}"

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

        # Create document with retry in case of document_number collision
        attempts = 0
        while True:
            attempts += 1
            try:
                platform = self._get_or_create_platform(
                    platform_name=document_data.platform, platform_id=document_data.platform_id
                )
                document = Document(
                    title=document_data.title,
                    document_number=document_number,
                    description=document_data.description,
                    version_label=document_data.version_label,
                    status=document_data.status,
                    visibility=document_data.visibility,
                    category=document_data.category,
                    topic=self._normalize_topic(document_data.topic),
                    platform=platform.name,
                    platform_id=platform.id,
                    release_branch=document_data.release_branch,
                    tags=document_data.tags,
                    created_by=user.id,
                    tenant_id=tenant_id,
                    parent_id=parent_id,
                )
                self.db.add(document)
                self.db.flush()

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
            except Exception:
                self.db.rollback()
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
