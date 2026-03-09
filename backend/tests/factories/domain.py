"""Low-level entity builders for backend tests."""

from __future__ import annotations

from datetime import date, datetime
from typing import TypeVar
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import (
    Attachment,
    AttachmentConversionJob,
    Document,
    DocumentStatus,
    DocumentVisibility,
    Tenant,
    User,
    UserRole,
)
from app.security import get_password_hash

T = TypeVar("T")


def _unique_suffix() -> str:
    return uuid4().hex[:8]


def persist(db: Session, entity: T) -> T:
    """Persist and refresh an entity in one call."""
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


def build_user(
    *,
    email: str | None = None,
    username: str | None = None,
    full_name: str = "Test User",
    role: UserRole = UserRole.EDITOR,
    plain_password: str = "testpass123",
    hashed_password: str | None = None,
    tenant_id: int | None = None,
    is_active: bool = True,
    is_email_verified: bool = True,
) -> User:
    suffix = _unique_suffix()
    resolved_username = username or f"user-{suffix}"
    resolved_email = email or f"{resolved_username}@example.com"
    return User(
        email=resolved_email,
        username=resolved_username,
        full_name=full_name,
        hashed_password=hashed_password or get_password_hash(plain_password),
        role=role,
        tenant_id=tenant_id,
        is_active=is_active,
        is_email_verified=is_email_verified,
    )


def create_user(db: Session, **kwargs) -> User:
    return persist(db, build_user(**kwargs))


def build_tenant(
    *,
    name: str = "Test Company",
    slug: str | None = None,
    is_active: bool = True,
    contact_email: str | None = "contact@testcompany.com",
    company_type: str = "customer",
) -> Tenant:
    suffix = _unique_suffix()
    resolved_slug = slug or f"tenant-{suffix}"
    return Tenant(
        name=name,
        slug=resolved_slug,
        is_active=is_active,
        contact_email=contact_email,
        company_type=company_type,
    )


def create_tenant(db: Session, **kwargs) -> Tenant:
    return persist(db, build_tenant(**kwargs))


def build_document(
    *,
    created_by: int,
    title: str = "Test Document",
    document_number: str | None = None,
    description: str | None = "A test document",
    status: DocumentStatus = DocumentStatus.DRAFT,
    visibility: DocumentVisibility = DocumentVisibility.INTERNAL,
    category: str | None = None,
    tags: str | None = None,
    due_date: date | None = None,
    tenant_id: int | None = None,
    parent_id: int | None = None,
) -> Document:
    suffix = _unique_suffix()
    resolved_document_number = document_number or f"DOC-TEST-{suffix.upper()}"
    return Document(
        title=title,
        document_number=resolved_document_number,
        description=description,
        status=status,
        visibility=visibility,
        category=category,
        tags=tags,
        due_date=due_date,
        created_by=created_by,
        tenant_id=tenant_id,
        parent_id=parent_id,
    )


def create_document(db: Session, **kwargs) -> Document:
    return persist(db, build_document(**kwargs))


def build_attachment(
    *,
    document_id: int,
    uploaded_by: int,
    filename: str = "test-document.pdf",
    original_filename: str | None = None,
    file_size: int = 10,
    size_bytes: int | None = None,
    mime_type: str = "application/pdf",
    storage_path: str | None = None,
    storage_key: str | None = None,
) -> Attachment:
    resolved_original_filename = original_filename or filename
    resolved_size_bytes = file_size if size_bytes is None else size_bytes
    resolved_storage_path = storage_path or f"/tmp/{filename}"
    resolved_storage_key = storage_key or resolved_storage_path
    return Attachment(
        document_id=document_id,
        filename=filename,
        original_filename=resolved_original_filename,
        file_size=file_size,
        size_bytes=resolved_size_bytes,
        mime_type=mime_type,
        storage_path=resolved_storage_path,
        storage_key=resolved_storage_key,
        uploaded_by=uploaded_by,
    )


def create_attachment(db: Session, **kwargs) -> Attachment:
    return persist(db, build_attachment(**kwargs))


def build_attachment_conversion_job(
    *,
    attachment_id: int,
    job_type: str = "preview_pdf",
    status: str = "pending",
    force: bool = False,
    attempts: int = 0,
    max_attempts: int = 3,
    started_at: datetime | None = None,
) -> AttachmentConversionJob:
    return AttachmentConversionJob(
        attachment_id=attachment_id,
        job_type=job_type,
        status=status,
        force=force,
        attempts=attempts,
        max_attempts=max_attempts,
        started_at=started_at,
    )


def create_attachment_conversion_job(db: Session, **kwargs) -> AttachmentConversionJob:
    return persist(db, build_attachment_conversion_job(**kwargs))
