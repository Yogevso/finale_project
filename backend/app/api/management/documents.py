"""Document Management API Routes"""

import logging
from math import ceil
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
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

from app.application.commands.dependencies import (
    get_assign_company_set_command_handler,
    get_create_document_command_handler,
    get_delete_document_command_handler,
    get_update_document_command_handler,
)
from app.application.commands.document_commands import (
    AssignCompanySetCommand,
    AssignCompanySetCommandErrorCode,
    AssignCompanySetCommandHandler,
    CreateDocumentCommand,
    CreateDocumentCommandHandler,
    DeleteDocumentCommand,
    DeleteDocumentCommandHandler,
    DocumentCommandErrorCode,
    UpdateDocumentCommand,
    UpdateDocumentCommandHandler,
)
from app.application.queries.dependencies import (
    get_document_query_handler,
    get_list_documents_query_handler,
)
from app.application.queries.document_queries import (
    GetDocumentQuery,
    GetDocumentQueryHandler,
    ListDocumentsQuery,
    ListDocumentsQueryHandler,
)
from app.db import get_db
from app.dependencies.permissions import (
    require_editor,
    require_internal_user,
    require_manager,
    require_permission,
)
from app.dependencies.services import get_document_service
from app.errors import NotFoundError, ValidationError
from app.models import DocumentStatus, DocumentVisibility, Tenant, User, UserRole
from app.schemas import (
    AttachmentResponse,
    DocumentCreate,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdate,
    MessageResponse,
    TenantSummary,
)
from app.services.attachment_service import AttachmentService
from app.services.document_service import DocumentService
from app.services.permissions import Permission
from app.utils.html_to_docx import html_to_docx_bytes

router = APIRouter()
logger = logging.getLogger(__name__)


class CompanyAssignRequest(BaseModel):
    """Request body for assigning companies to a document"""

    company_ids: List[int]


class GenerateWordRequest(BaseModel):
    """Request body for generating a Word file from HTML content."""

    html_content: str
    filename: Optional[str] = None


@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(
    document_data: DocumentCreate,
    current_user: User = Depends(require_editor),
    create_document_command_handler: CreateDocumentCommandHandler = Depends(
        get_create_document_command_handler
    ),
):
    """
    Create a new document.

    Requires: EDITOR role or above.
    Automatically generates document number and creates initial version.
    Document is assigned to the user's tenant.
    """
    result = create_document_command_handler.execute(
        CreateDocumentCommand(document_data=document_data, current_user=current_user)
    )
    if result.is_err:
        if result.error.code == DocumentCommandErrorCode.NOT_FOUND:
            raise NotFoundError(result.error.message)
        if result.error.code == DocumentCommandErrorCode.VALIDATION:
            raise ValidationError(result.error.message)
        raise HTTPException(status_code=500, detail="Unexpected document-create command error")
    return result.value


@router.post(
    "/documents/{document_id}/generate-word",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_word_attachment(
    document_id: int,
    payload: GenerateWordRequest,
    current_user: User = Depends(require_editor),
    document_service: DocumentService = Depends(get_document_service),
    db: Session = Depends(get_db),
):
    """
    Generate a Word file from HTML content and attach it to the document.
    """
    document = document_service.get_document(document_id)
    document_service._verify_access(document)

    docx_bytes = html_to_docx_bytes(payload.html_content)
    safe_name = payload.filename or f"{document.title}.docx"

    attachment = AttachmentService.create_attachment_from_bytes(
        db=db,
        document_id=document_id,
        content=docx_bytes,
        original_filename=safe_name,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        current_user=current_user,
        convert_to_html=False,
    )
    return attachment


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[DocumentStatus] = Query(None, description="Filter by status"),
    visibility: Optional[DocumentVisibility] = Query(None, description="Filter by visibility"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search in title, description, tags"),
    current_user: User = Depends(require_internal_user),
    list_documents_query_handler: ListDocumentsQueryHandler = Depends(
        get_list_documents_query_handler
    ),
):
    """
    Get paginated list of documents with optional filters.

    Requires: Internal user (not customer - customers use portal API).
    Results are filtered by the user's tenant.
    Supports:
    - Pagination (page, page_size)
    - Status filter
    - Visibility filter
    - Category filter
    - Full-text search
    """
    skip = (page - 1) * page_size
    query_result = list_documents_query_handler.execute(
        ListDocumentsQuery(
            skip=skip,
            limit=page_size,
            status=status,
            visibility=visibility,
            category=category,
            search=search,
        )
    )

    return DocumentListResponse(
        items=query_result.items,
        total=query_result.total,
        page=page,
        page_size=page_size,
        pages=ceil(query_result.total / page_size) if query_result.total > 0 else 0,
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    current_user: User = Depends(require_internal_user),
    document_query_handler: GetDocumentQueryHandler = Depends(get_document_query_handler),
):
    """
    Get document by ID.

    Requires: Internal user (not customer).
    Document must belong to user's tenant.
    """
    result = document_query_handler.execute(GetDocumentQuery(document_id=document_id))
    if result.is_err:
        raise NotFoundError(result.error.message)
    return result.value


@router.put("/documents/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: int,
    document_data: DocumentUpdate,
    current_user: User = Depends(require_editor),
    update_document_command_handler: UpdateDocumentCommandHandler = Depends(
        get_update_document_command_handler
    ),
):
    """
    Update document.

    Requires: EDITOR role or above.
    Creates new version if content changes.
    Only documents in user's tenant can be updated.
    """
    result = update_document_command_handler.execute(
        UpdateDocumentCommand(
            document_id=document_id,
            document_data=document_data,
            current_user=current_user,
        )
    )
    if result.is_err:
        if result.error.code == DocumentCommandErrorCode.NOT_FOUND:
            raise NotFoundError(result.error.message)
        if result.error.code == DocumentCommandErrorCode.VALIDATION:
            raise ValidationError(result.error.message)
        raise HTTPException(status_code=500, detail="Unexpected document-update command error")
    return result.value


@router.delete("/documents/{document_id}", response_model=MessageResponse)
def delete_document(
    document_id: int,
    current_user: User = Depends(require_manager),
    delete_document_command_handler: DeleteDocumentCommandHandler = Depends(
        get_delete_document_command_handler
    ),
):
    """
    Delete document.

    Requires: MANAGER role or above.
    Only documents in user's tenant can be deleted.
    Cascade deletes all versions, attachments, and comments.
    """
    result = delete_document_command_handler.execute(
        DeleteDocumentCommand(document_id=document_id, current_user=current_user)
    )
    if result.is_err:
        if result.error.code == DocumentCommandErrorCode.NOT_FOUND:
            raise NotFoundError(result.error.message)
        if result.error.code == DocumentCommandErrorCode.VALIDATION:
            raise ValidationError(result.error.message)
        raise HTTPException(status_code=500, detail="Unexpected document-delete command error")
    return MessageResponse(message="Document deleted successfully")


@router.post(
    "/documents/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    document_number: Optional[str] = Form(None),
    version_label: Optional[str] = Form(None),
    visibility: Optional[str] = Form(None),
    upload_status: Optional[str] = Form(None, alias="status"),
    parent_id: Optional[int] = Form(None),
    topic: Optional[str] = Form(None),
    platform: Optional[str] = Form(None),
    release_branch: Optional[str] = Form(None),
    release_notes: Optional[UploadFile] = File(None),
    content_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(require_editor),
    document_service: DocumentService = Depends(get_document_service),
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

    allowed_visibility = {"public", "internal", "company"}
    if visibility is not None and visibility not in allowed_visibility:
        raise HTTPException(status_code=400, detail="Invalid visibility value")

    allowed_status = {item.value for item in DocumentStatus}
    if upload_status is not None and upload_status not in allowed_status:
        raise HTTPException(status_code=400, detail="Invalid status value")

    privileged_publish = current_user.role in {
        UserRole.SYSTEM_ADMIN,
        UserRole.ADMIN,
        UserRole.MANAGER,
    }
    visibility_value = visibility or "internal"
    status_value = upload_status or DocumentStatus.DRAFT.value

    if visibility_value == "public" and not privileged_publish:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and above can upload public documents",
        )
    if status_value == DocumentStatus.ACTIVE.value and not privileged_publish:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and above can upload directly as active",
        )

    # Create the document first
    document_data = DocumentCreate(
        title=doc_title,
        description=description or f"Uploaded from file: {file.filename}",
        status=status_value,
        visibility=visibility_value,
        category=category or "Uploaded",
        topic=topic,
        platform=platform,
        release_branch=release_branch,
        tags=tags or "",
        document_number=document_number,
        version_label=version_label,
        parent_id=parent_id,
    )
    document = document_service.create_document(document_data, current_user)
    created_document_ids: list[int] = [document.id]

    try:
        # Attach uploaded files to parent document.
        await AttachmentService.upload_attachment(
            db,
            document.id,
            file,
            current_user,
            background_tasks=background_tasks,
        )
        if content_file:
            await AttachmentService.upload_attachment(
                db,
                document.id,
                content_file,
                current_user,
                background_tasks=background_tasks,
            )

        # Optional release notes: create child document and attach release notes file.
        if release_notes:
            release_doc_title = f"{doc_title} Release Notes"
            release_data = DocumentCreate(
                title=release_doc_title,
                description=f"Release notes for {doc_title}",
                status=status_value,
                visibility=visibility_value,
                category="Release Notes",
                tags="release-notes",
                document_number=None,
                version_label=version_label,
                parent_id=document.id,
            )
            release_doc = document_service.create_document(release_data, current_user)
            created_document_ids.append(release_doc.id)
            await AttachmentService.upload_attachment(
                db,
                release_doc.id,
                release_notes,
                current_user,
                background_tasks=background_tasks,
            )
    except Exception as exc:
        # Roll back all created documents (child before parent) to avoid orphan rows.
        for created_document_id in reversed(created_document_ids):
            try:
                document_service.delete_document(created_document_id, current_user)
            except Exception as cleanup_error:
                db.rollback()
                logger.warning(
                    "Failed upload rollback cleanup for document_id=%s: %s",
                    created_document_id,
                    cleanup_error,
                )

        if isinstance(exc, HTTPException):
            raise
        raise

    # Refresh to get updated data
    db.refresh(document)
    return document


@router.get("/documents/{document_id}/assigned-companies", response_model=List[TenantSummary])
def get_assigned_companies(
    document_id: int,
    current_user: User = Depends(require_internal_user),
    document_query_handler: GetDocumentQueryHandler = Depends(get_document_query_handler),
):
    """
    Get list of companies assigned to a document.

    Requires: Internal user.
    """
    result = document_query_handler.execute(GetDocumentQuery(document_id=document_id))
    if result.is_err:
        raise NotFoundError(result.error.message)
    document = result.value

    return [TenantSummary(id=c.id, name=c.name, slug=c.slug) for c in document.assigned_companies]


@router.post("/documents/{document_id}/assign-companies", response_model=MessageResponse)
def assign_companies(
    document_id: int,
    request: CompanyAssignRequest,
    current_user: User = Depends(require_permission(Permission.ASSIGN_COMPANIES)),
    assign_company_set_command_handler: AssignCompanySetCommandHandler = Depends(
        get_assign_company_set_command_handler
    ),
):
    """
    Replace the companies assigned to a document.
    Manager+ access required.
    """
    result = assign_company_set_command_handler.execute(
        AssignCompanySetCommand(document_id=document_id, company_ids=request.company_ids)
    )
    if result.is_err:
        if result.error.code == AssignCompanySetCommandErrorCode.DOCUMENT_NOT_FOUND:
            raise NotFoundError(result.error.message)
        if result.error.code == AssignCompanySetCommandErrorCode.INVALID_COMPANY_SET:
            raise ValidationError(result.error.message, error_code="invalid_company_set")
        raise HTTPException(status_code=500, detail="Unexpected company-assignment command error")

    assigned_count = result.value
    return MessageResponse(message=f"Assigned company set updated ({assigned_count} total)")


@router.delete(
    "/documents/{document_id}/assign-companies/{company_id}", response_model=MessageResponse
)
def remove_company_assignment(
    document_id: int,
    company_id: int,
    current_user: User = Depends(require_permission(Permission.ASSIGN_COMPANIES)),
    document_service: DocumentService = Depends(get_document_service),
    db: Session = Depends(get_db),
):
    """
    Remove a company from a document's assignments.
    Manager+ access required.
    """
    document = document_service.get_document(document_id)
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
