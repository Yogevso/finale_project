"""Document Management API Routes"""
from math import ceil
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.tenant import TenantContext, get_tenant_context
from app.models import DocumentStatus, User, UserRole
from app.schemas import (
    DocumentCreate,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdate,
    MessageResponse,
)
from app.security import get_current_active_user
from app.services.attachment_service import AttachmentService
from app.services.document_service import DocumentService

router = APIRouter()


@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(
    document_data: DocumentCreate,
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Create a new document.

    Automatically generates document number and creates initial version.
    Document is assigned to the user's tenant.
    """
    service = DocumentService(db, tenant_ctx)
    return service.create_document(document_data, current_user)


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[DocumentStatus] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search in title, description, tags"),
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of documents with optional filters.

    Results are filtered by the user's tenant.
    Supports:
    - Pagination (page, page_size)
    - Status filter
    - Category filter
    - Full-text search
    """
    service = DocumentService(db, tenant_ctx)
    skip = (page - 1) * page_size
    documents, total = service.get_documents(
        skip=skip,
        limit=page_size,
        status=status,
        category=category,
        search=search
    )

    return DocumentListResponse(
        items=documents,
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total > 0 else 0
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """Get document by ID (must belong to user's tenant)"""
    service = DocumentService(db, tenant_ctx)
    document = service.get_document(document_id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return document


@router.put("/documents/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: int,
    document_data: DocumentUpdate,
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Update document.

    Creates new version if content changes.
    Only documents in user's tenant can be updated.
    """
    service = DocumentService(db, tenant_ctx)
    return service.update_document(document_id, document_data, current_user)


@router.delete("/documents/{document_id}", response_model=MessageResponse)
def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Delete document.

    Only documents in user's tenant can be deleted.
    Cascade deletes all versions, attachments, and comments.
    """
    service = DocumentService(db, tenant_ctx)
    service.delete_document(document_id, current_user)
    return MessageResponse(message="Document deleted successfully")


@router.post("/documents/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Upload a document file (PDF/Word) and create a new document with it attached.

    Only admins and editors can upload documents.
    Max file size: 10MB.
    Allowed types: PDF, Word documents.

    The file name will be used as the document title if not provided.
    """
    # Check permission - only admin/editor can upload
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.EDITOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and editors can upload documents"
        )

    # Use filename as title if not provided
    doc_title = title or file.filename.rsplit('.', 1)[0] if file.filename else "Uploaded Document"

    # Create the document first
    service = DocumentService(db, tenant_ctx)
    document_data = DocumentCreate(
        title=doc_title,
        description=description or f"Uploaded from file: {file.filename}",
        status="draft",
        category=category or "Uploaded",
        tags=tags or ""
    )
    document = service.create_document(document_data, current_user)

    # Now attach the uploaded file
    try:
        await AttachmentService.upload_attachment(db, document.id, file, current_user)
    except HTTPException as e:
        # If attachment fails, delete the document and re-raise
        service.delete_document(document.id, current_user)
        raise e

    # Refresh to get updated data
    db.refresh(document)
    return document
