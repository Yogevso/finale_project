"""Viewer Portal - Public Document API (No Auth Required)"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Attachment, Comment, Document, DocumentStatus, Version
from app.schemas import (
    AttachmentResponse,
    CommentResponse,
    DocumentListResponse,
    DocumentResponse,
    VersionResponse,
)

router = APIRouter(prefix="/viewer/documents", tags=["viewer"])


def _get_active_document_or_404(db: Session, document_id: int) -> Document:
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.status == DocumentStatus.ACTIVE,
        )
        .first()
    )
    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found or not published",
        )
    return document


def _get_published_version_or_404(db: Session, document_id: int, version_id: int) -> Version:
    version = (
        db.query(Version)
        .filter(
            Version.id == version_id,
            Version.document_id == document_id,
            Version.is_published.is_(True),
        )
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Published version not found")
    return version


@router.get("", response_model=DocumentListResponse)
def list_published_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    List published/active documents (public access, no auth required).
    Only shows documents with status='active'.
    """
    query = db.query(Document).filter(Document.status == DocumentStatus.ACTIVE)

    # Search by title or description
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Document.title.ilike(search_term)) | (Document.description.ilike(search_term))
        )

    # Filter by category
    if category:
        query = query.filter(Document.category == category)

    # Get total count
    total = query.count()

    # Paginate
    offset = (page - 1) * page_size
    documents = query.order_by(Document.updated_at.desc()).offset(offset).limit(page_size).all()

    return DocumentListResponse(
        items=[DocumentResponse.model_validate(d) for d in documents],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    """Get list of categories from published documents."""
    categories = (
        db.query(Document.category)
        .filter(
            Document.status == DocumentStatus.ACTIVE,
            Document.category.isnot(None),
        )
        .distinct()
        .all()
    )
    return [c[0] for c in categories if c[0]]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_published_document(
    document_id: int,
    db: Session = Depends(get_db),
):
    """Get a single published document by ID."""
    document = _get_active_document_or_404(db, document_id)
    return DocumentResponse.model_validate(document)


@router.get("/{document_id}/versions", response_model=list[VersionResponse])
def get_published_versions(
    document_id: int,
    db: Session = Depends(get_db),
):
    """Get published versions for a document."""
    _get_active_document_or_404(db, document_id)

    # Get only published versions
    versions = (
        db.query(Version)
        .filter(
            Version.document_id == document_id,
            Version.is_published.is_(True),
        )
        .order_by(Version.version_number.desc())
        .all()
    )

    return [VersionResponse.model_validate(v) for v in versions]


@router.get("/{document_id}/versions/{version_id}/attachments", response_model=list[AttachmentResponse])
def get_version_attachments(
    document_id: int,
    version_id: int,
    db: Session = Depends(get_db),
):
    """Get document attachments available for a specific published version."""
    _get_active_document_or_404(db, document_id)
    version = _get_published_version_or_404(db, document_id, version_id)
    cutoff_timestamp = version.published_at or version.created_at

    attachments = (
        db.query(Attachment)
        .filter(
            Attachment.document_id == document_id,
            Attachment.uploaded_at <= cutoff_timestamp,
        )
        .order_by(Attachment.uploaded_at.desc())
        .all()
    )

    return [AttachmentResponse.model_validate(a) for a in attachments]


@router.get("/{document_id}/attachments", response_model=list[AttachmentResponse])
def get_document_attachments(
    document_id: int,
    db: Session = Depends(get_db),
):
    """Get attachments for a published document."""
    _get_active_document_or_404(db, document_id)

    attachments = (
        db.query(Attachment)
        .filter(Attachment.document_id == document_id)
        .order_by(Attachment.uploaded_at.desc())
        .all()
    )

    return [AttachmentResponse.model_validate(a) for a in attachments]


@router.get("/{document_id}/comments", response_model=list[CommentResponse])
def get_document_comments(
    document_id: int,
    db: Session = Depends(get_db),
):
    """Get comments for a published document (read-only for viewers)."""
    _get_active_document_or_404(db, document_id)

    comments = (
        db.query(Comment)
        .filter(Comment.document_id == document_id)
        .order_by(Comment.created_at.asc())
        .all()
    )

    return [CommentResponse.model_validate(c) for c in comments]
