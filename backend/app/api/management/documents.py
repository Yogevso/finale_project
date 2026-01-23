"""Document Management API Routes"""

from math import ceil
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.permissions import (
    require_editor,
    require_internal_user,
    require_manager,
)
from app.dependencies.tenant import TenantContext, get_tenant_context
from app.models import Document, DocumentStatus, Tenant, User, UserRole
from app.schemas import (
    DocumentCreate,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdate,
    MessageResponse,
    TenantSummary,
)
from app.security import get_current_active_user
from app.services.attachment_service import AttachmentService
from app.services.document_service import DocumentService

router = APIRouter()


class CompanyAssignRequest(BaseModel):
    """Request body for assigning companies to a document"""

    company_ids: List[int]


@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(
    document_data: DocumentCreate,
    current_user: User = Depends(require_editor),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Create a new document.

    Requires: EDITOR role or above.
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
    current_user: User = Depends(require_internal_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Get paginated list of documents with optional filters.

    Requires: Internal user (not customer - customers use portal API).
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
        skip=skip, limit=page_size, status=status, category=category, search=search
    )

    return DocumentListResponse(
        items=documents,
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    current_user: User = Depends(require_internal_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Get document by ID.

    Requires: Internal user (not customer).
    Document must belong to user's tenant.
    """
    service = DocumentService(db, tenant_ctx)
    document = service.get_document(document_id)

    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    return document


@router.put("/documents/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: int,
    document_data: DocumentUpdate,
    current_user: User = Depends(require_editor),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Update document.

    Requires: EDITOR role or above.
    Creates new version if content changes.
    Only documents in user's tenant can be updated.
    """
    service = DocumentService(db, tenant_ctx)
    return service.update_document(document_id, document_data, current_user)


@router.delete("/documents/{document_id}", response_model=MessageResponse)
def delete_document(
    document_id: int,
    current_user: User = Depends(require_manager),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Delete document.

    Requires: MANAGER role or above.
    Only documents in user's tenant can be deleted.
    Cascade deletes all versions, attachments, and comments.
    """
    service = DocumentService(db, tenant_ctx)
    service.delete_document(document_id, current_user)
    return MessageResponse(message="Document deleted successfully")


@router.post(
    "/documents/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED
)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    current_user: User = Depends(require_editor),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Upload a document file (PDF/Word) and create a new document with it attached.

    Requires: EDITOR role or above.
    Max file size: 10MB.
    Allowed types: PDF, Word documents.

    The file name will be used as the document title if not provided.
    """
    # Use filename as title if not provided
    doc_title = title or file.filename.rsplit(".", 1)[0] if file.filename else "Uploaded Document"

    # Create the document first
    service = DocumentService(db, tenant_ctx)
    document_data = DocumentCreate(
        title=doc_title,
        description=description or f"Uploaded from file: {file.filename}",
        status="draft",
        category=category or "Uploaded",
        tags=tags or "",
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


def require_manager_or_above(current_user: User = Depends(get_current_active_user)) -> User:
    """Require manager, admin, or system_admin role"""
    if current_user.role not in [UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager access required to manage company assignments",
        )
    return current_user


@router.get("/documents/{document_id}/assigned-companies", response_model=List[TenantSummary])
def get_assigned_companies(
    document_id: int,
    current_user: User = Depends(require_internal_user),
    db: Session = Depends(get_db),
):
    """
    Get list of companies assigned to a document.

    Requires: Internal user.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return [TenantSummary(id=c.id, name=c.name, slug=c.slug) for c in document.assigned_companies]


@router.post("/documents/{document_id}/assign-companies", response_model=MessageResponse)
def assign_companies(
    document_id: int,
    request: CompanyAssignRequest,
    current_user: User = Depends(require_manager_or_above),
    db: Session = Depends(get_db),
):
    """
    Assign companies to a document.
    Manager+ access required.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get companies
    companies = db.query(Tenant).filter(Tenant.id.in_(request.company_ids)).all()
    if len(companies) != len(request.company_ids):
        raise HTTPException(status_code=400, detail="Some company IDs are invalid")

    # Add companies (avoiding duplicates)
    existing_ids = {c.id for c in document.assigned_companies}
    for company in companies:
        if company.id not in existing_ids:
            document.assigned_companies.append(company)

    db.commit()

    return MessageResponse(message=f"Assigned {len(companies)} companies to document")


@router.delete(
    "/documents/{document_id}/assign-companies/{company_id}", response_model=MessageResponse
)
def remove_company_assignment(
    document_id: int,
    company_id: int,
    current_user: User = Depends(require_manager_or_above),
    db: Session = Depends(get_db),
):
    """
    Remove a company from a document's assignments.
    Manager+ access required.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    company = db.query(Tenant).filter(Tenant.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if company not in document.assigned_companies:
        raise HTTPException(status_code=400, detail="Company is not assigned to this document")

    document.assigned_companies.remove(company)
    db.commit()

    return MessageResponse(message=f"Removed {company.name} from document")
