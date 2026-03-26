"""Document Management API Routes"""

import logging
import os
import re
from datetime import date, datetime, timedelta
from math import ceil
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
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
from app.application.process_managers import DocumentUploadProcessManager
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
from app.config import settings
from app.db import get_db
from app.dependencies.permissions import (
    require_editor,
    require_internal_user,
    require_manager,
    require_permission,
)
from app.dependencies.services import get_document_service
from app.errors import InvalidStateError, NotFoundError, PermissionDeniedError, ValidationError
from app.errors.audience_errors import AudienceErrorCode
from app.models import DocumentStatus, DocumentVisibility, Tenant, User, UserRole
from app.schemas import (
    AttachmentResponse,
    BulkDocumentMetadataUpdateRequest,
    BulkDocumentMetadataUpdateResponse,
    DocumentCalendarExportResponse,
    DocumentCreate,
    DocumentListResponse,
    DocumentResponse,
    DocumentTagSuggestionsResponse,
    DocumentUpdate,
    DocumentWatchResponse,
    DocumentWatchStatusResponse,
    DuplicateCheckResponse,
    MessageResponse,
    TenantSummary,
)
from app.services.attachment_service import AttachmentService
from app.services.document_service import DocumentService
from app.services.permissions import Permission
from app.utils.html_to_docx import html_to_docx_bytes

router = APIRouter()
logger = logging.getLogger(__name__)
AUDIENCE_ASSIGNMENT_SCHEMA_VERSION = settings.AUDIENCE_ASSIGNMENT_SCHEMA_VERSION


def _escape_ical_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _build_document_calendar_export(*, document: object, due_date: date) -> str:
    document_title = getattr(document, "title", "Document due date")
    document_number = getattr(document, "document_number", None)
    document_id = getattr(document, "id", None)
    escaped_title = _escape_ical_text(str(document_title))
    escaped_description = _escape_ical_text(
        f"{document_number or 'Document'} due date"
    )
    uid = f"document-due-{document_id or 'unknown'}@finale-project"
    dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    start = due_date.strftime("%Y%m%d")
    end = (due_date + timedelta(days=1)).strftime("%Y%m%d")
    return (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//Finale Project//Document Workflow//EN\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{uid}\r\n"
        f"DTSTAMP:{dtstamp}\r\n"
        f"DTSTART;VALUE=DATE:{start}\r\n"
        f"DTEND;VALUE=DATE:{end}\r\n"
        f"SUMMARY:{escaped_title}\r\n"
        f"DESCRIPTION:{escaped_description}\r\n"
        "STATUS:CONFIRMED\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )


def _calendar_filename(document_number: str | None, document_id: int) -> str:
    seed = document_number or f"document-{document_id}"
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", seed.strip()).strip("-").lower()
    return f"{slug or f'document-{document_id}'}-due-date.ics"


class CompanyAssignRequest(BaseModel):
    """Request body for assigning companies to a document"""

    company_ids: List[int]


class GenerateWordRequest(BaseModel):
    """Request body for generating a Word file from HTML content."""

    html_content: str
    filename: Optional[str] = None


class DocumentStatsResponse(BaseModel):
    """Dashboard summary counts for documents in current tenant scope."""

    total: int
    published: int
    approved: int
    draft: int


def _apply_company_set_update(
    *,
    document_id: int,
    request: CompanyAssignRequest,
    if_match: Optional[str],
    response: Response,
    assign_company_set_command_handler: AssignCompanySetCommandHandler,
    document_service: DocumentService,
    success_message: str,
) -> MessageResponse:
    result = assign_company_set_command_handler.execute(
        AssignCompanySetCommand(
            document_id=document_id,
            company_ids=request.company_ids,
            if_match=if_match,
        )
    )
    if result.is_err:
        if result.error.code == AssignCompanySetCommandErrorCode.DOCUMENT_NOT_FOUND:
            raise NotFoundError(result.error.message)
        if result.error.code == AssignCompanySetCommandErrorCode.INVALID_COMPANY_SET:
            raise ValidationError(result.error.message, error_code=result.error.error_code)
        raise HTTPException(status_code=500, detail="Unexpected company-assignment command error")

    assigned_count = result.value
    updated_document = document_service.get_document(document_id)
    if updated_document:
        response.headers["ETag"] = f"\"{updated_document.etag}\""
    response.headers["X-API-Schema-Version"] = AUDIENCE_ASSIGNMENT_SCHEMA_VERSION
    return MessageResponse(message=success_message.format(assigned_count=assigned_count))


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
            raise ValidationError(result.error.message, error_code=result.error.error_code)
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
    company_id: Optional[int] = Query(None, description="Filter by assigned company"),
    date_from: Optional[date] = Query(None, description="Filter documents created on or after date"),
    date_to: Optional[date] = Query(None, description="Filter documents created on or before date"),
    sort_by: Optional[str] = Query(None, pattern="^(title|created_at|updated_at|status|category)$", description="Sort field: title, created_at, updated_at, status, category"),
    sort_order: Optional[str] = Query("desc", pattern="^(asc|desc)$", description="Sort direction: asc or desc"),
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
    - Sorting (sort_by, sort_order)
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
            company_id=company_id,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    )

    return DocumentListResponse(
        items=query_result.items,
        total=query_result.total,
        page=page,
        page_size=page_size,
        total_pages=ceil(query_result.total / page_size) if query_result.total > 0 else 0,
    )


@router.get("/documents/tags", response_model=DocumentTagSuggestionsResponse)
def list_document_tags(
    q: Optional[str] = Query(None, description="Optional tag search term"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of tags to return"),
    current_user: User = Depends(require_internal_user),
    document_service: DocumentService = Depends(get_document_service),
):
    """Return tenant-scoped tag suggestions for autocomplete editors."""
    _ = current_user
    return DocumentTagSuggestionsResponse(items=document_service.list_tags(query=q, limit=limit))


@router.get("/documents/duplicate-check", response_model=DuplicateCheckResponse)
def check_duplicate_documents(
    title: str = Query(..., min_length=3, description="Prospective document title"),
    threshold: float = Query(0.8, ge=0.5, le=1.0, description="Similarity threshold"),
    limit: int = Query(5, ge=1, le=20, description="Maximum number of matches to return"),
    current_user: User = Depends(require_editor),
    document_service: DocumentService = Depends(get_document_service),
):
    """Return likely duplicate documents for a draft title."""
    _ = current_user
    matches = document_service.find_duplicate_titles(title, threshold=threshold, limit=limit)
    return DuplicateCheckResponse(
        title=title,
        threshold=threshold,
        has_matches=len(matches) > 0,
        matches=matches,
    )


@router.post("/documents/bulk-metadata", response_model=BulkDocumentMetadataUpdateResponse)
def bulk_update_document_metadata(
    payload: BulkDocumentMetadataUpdateRequest,
    current_user: User = Depends(require_manager),
    document_service: DocumentService = Depends(get_document_service),
):
    """Apply one metadata change-set to multiple documents."""
    updated_ids = document_service.bulk_update_metadata(
        document_ids=payload.document_ids,
        user=current_user,
        category=payload.category,
        visibility=payload.visibility,
        company_ids=payload.company_ids,
        reason=payload.reason,
    )
    return BulkDocumentMetadataUpdateResponse(
        updated_count=len(updated_ids),
        document_ids=updated_ids,
        message=f"Updated metadata for {len(updated_ids)} document(s)",
    )


@router.get("/documents/stats", response_model=DocumentStatsResponse)
def get_document_stats(
    current_user: User = Depends(require_internal_user),
    document_service: DocumentService = Depends(get_document_service),
):
    """Get dashboard document counts for the current tenant/user scope."""
    _ = current_user
    return DocumentStatsResponse(**document_service.get_document_stats())


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    response: Response,
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
    document = result.value
    response.headers["ETag"] = f"\"{document.etag}\""
    return document


@router.get("/documents/{document_id}/watch-status", response_model=DocumentWatchStatusResponse)
def get_document_watch_status(
    document_id: int,
    current_user: User = Depends(require_internal_user),
    document_service: DocumentService = Depends(get_document_service),
):
    """Return whether the current internal user follows the document."""
    return DocumentWatchStatusResponse(
        is_watching=document_service.get_watch_status(document_id, current_user)
    )


@router.post("/documents/{document_id}/watch", response_model=DocumentWatchResponse)
def watch_document(
    document_id: int,
    current_user: User = Depends(require_internal_user),
    document_service: DocumentService = Depends(get_document_service),
):
    """Follow a document and receive future update notifications."""
    watcher = document_service.watch_document(document_id, current_user)
    return DocumentWatchResponse(
        document_id=watcher.document_id,
        user_id=watcher.user_id,
        is_watching=True,
        watched_at=watcher.created_at,
    )


@router.delete("/documents/{document_id}/watch", response_model=DocumentWatchResponse)
def unwatch_document(
    document_id: int,
    current_user: User = Depends(require_internal_user),
    document_service: DocumentService = Depends(get_document_service),
):
    """Stop following a document."""
    document_service.unwatch_document(document_id, current_user)
    return DocumentWatchResponse(
        document_id=document_id,
        user_id=current_user.id,
        is_watching=False,
        watched_at=None,
    )


@router.put("/documents/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: int,
    document_data: DocumentUpdate,
    response: Response,
    if_match: Optional[str] = Header(None, alias="If-Match"),
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
            if_match=if_match,
        )
    )
    if result.is_err:
        if result.error.code == DocumentCommandErrorCode.NOT_FOUND:
            raise NotFoundError(result.error.message)
        if result.error.code == DocumentCommandErrorCode.VALIDATION:
            raise ValidationError(result.error.message, error_code=result.error.error_code)
        raise HTTPException(status_code=500, detail="Unexpected document-update command error")
    document = result.value
    response.headers["ETag"] = f"\"{document.etag}\""
    return document


@router.delete("/documents/{document_id}", response_model=MessageResponse)
def delete_document(
    document_id: int,
    if_match: Optional[str] = Header(None, alias="If-Match"),
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
        DeleteDocumentCommand(document_id=document_id, current_user=current_user, if_match=if_match)
    )
    if result.is_err:
        if result.error.code == DocumentCommandErrorCode.NOT_FOUND:
            raise NotFoundError(result.error.message)
        if result.error.code == DocumentCommandErrorCode.VALIDATION:
            raise ValidationError(result.error.message, error_code=result.error.error_code)
        raise HTTPException(status_code=500, detail="Unexpected document-delete command error")
    return MessageResponse(message="Document deleted successfully")


@router.post(
    "/documents/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED
)
async def upload_document(
    request: Request,
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
    due_date: Optional[date] = Form(None),
    release_notes: Optional[UploadFile] = File(None),
    content_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(require_editor),
    document_service: DocumentService = Depends(get_document_service),
    db: Session = Depends(get_db),
):
    """
    Upload a document file and create a new document with it attached.

    Requires: EDITOR role or above.
    Max file size: 10MB.
    Allowed types: DOCX and PPTX.

    The file name will be used as the document title if not provided.
    """
    normalized_content_type = (file.content_type or "").lower()
    normalized_filename = (file.filename or "").lower()
    allowed_mime_types = {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
    allowed_extensions = {".docx", ".pptx"}
    blocked_mime_prefix = "/".join(("application", "pdf"))
    blocked_extension = "." + "pdf"
    if normalized_content_type.startswith(blocked_mime_prefix) or normalized_filename.endswith(
        blocked_extension
    ):
        raise ValidationError("PDF uploads are not allowed")
    if not (
        normalized_content_type in allowed_mime_types
        or any(normalized_filename.endswith(extension) for extension in allowed_extensions)
    ):
        raise ValidationError("Only DOCX and PPTX files are allowed")

    # Use filename as title if not provided
    raw_filename = file.filename or "Uploaded Document"
    # H-10: Strip directory components to prevent path traversal
    safe_filename = os.path.basename(raw_filename)
    doc_title = title or safe_filename.rsplit(".", 1)[0] if safe_filename else "Uploaded Document"
    form = await request.form()
    raw_company_ids = form.getlist("company_ids")
    company_ids: List[int] = []
    for raw_company_id in raw_company_ids:
        try:
            company_ids.append(int(raw_company_id))
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                "Invalid company_ids value",
                error_code=AudienceErrorCode.AUDIENCE_002.value,
            ) from exc

    allowed_visibility = {"public", "internal", "company"}
    if visibility is not None and visibility not in allowed_visibility:
        raise ValidationError(
            "Invalid visibility value",
            error_code=AudienceErrorCode.AUDIENCE_003.value,
        )

    allowed_status = {item.value for item in DocumentStatus}
    if upload_status is not None and upload_status not in allowed_status:
        raise ValidationError("Invalid status value", error_code="invalid_status")

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
    if visibility_value == "company" and len(company_ids) == 0:
        raise ValidationError(
            "Company visibility requires at least one assigned company",
            error_code=AudienceErrorCode.AUDIENCE_001.value,
        )
    if visibility_value != "company" and len(company_ids) > 0:
        raise ValidationError(
            "Company assignments require company visibility",
            error_code=AudienceErrorCode.AUDIENCE_002.value,
        )
    if status_value == DocumentStatus.ACTIVE.value and not privileged_publish:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and above can upload directly as active",
        )

    # Build parent document payload.
    document_data = DocumentCreate(
        title=doc_title,
        description=description or f"Uploaded from file: {file.filename}",
        status=status_value,
        visibility=visibility_value,
        company_ids=company_ids,
        category=category or "Uploaded",
        topic=topic,
        platform=platform,
        release_branch=release_branch,
        tags=tags or "",
        due_date=due_date,
        document_number=document_number,
        version_label=version_label,
        parent_id=parent_id,
    )
    release_data = None
    if release_notes:
        release_doc_title = f"{doc_title} Release Notes"
        release_data = DocumentCreate(
            title=release_doc_title,
            description=f"Release notes for {doc_title}",
            status=status_value,
            visibility=visibility_value,
            company_ids=company_ids,
            category="Release Notes",
            tags="release-notes",
            document_number=None,
            version_label=version_label,
            parent_id=None,  # Set below after parent document creation.
        )

    upload_manager = DocumentUploadProcessManager(
        db=db,
        document_service=document_service,
        attachment_uploader=AttachmentService.upload_attachment,
        logger=logger,
    )

    try:
        upload_result = await upload_manager.execute(
            parent_document_data=document_data,
            current_user=current_user,
            background_tasks=background_tasks,
            primary_file=file,
            content_file=content_file,
            release_notes_file=release_notes,
            release_notes_document_data=release_data,
        )
        document = upload_result.document
    except HTTPException:
        raise

    # Refresh to get updated data
    db.refresh(document)
    return document


@router.get("/documents/{document_id}/assigned-companies", response_model=List[TenantSummary])
def get_assigned_companies(
    document_id: int,
    response: Response,
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
    response.headers["X-API-Schema-Version"] = AUDIENCE_ASSIGNMENT_SCHEMA_VERSION

    return [TenantSummary(id=c.id, name=c.name, slug=c.slug) for c in document.assigned_companies]


@router.post("/documents/{document_id}/assign-companies", response_model=MessageResponse)
def assign_companies(
    document_id: int,
    request: CompanyAssignRequest,
    response: Response,
    if_match: Optional[str] = Header(None, alias="If-Match"),
    current_user: User = Depends(require_permission(Permission.ASSIGN_COMPANIES)),
    assign_company_set_command_handler: AssignCompanySetCommandHandler = Depends(
        get_assign_company_set_command_handler
    ),
    document_service: DocumentService = Depends(get_document_service),
):
    """
    Replace the companies assigned to a document.
    Manager+ access required.
    """
    _ = current_user
    return _apply_company_set_update(
        document_id=document_id,
        request=request,
        if_match=if_match,
        response=response,
        assign_company_set_command_handler=assign_company_set_command_handler,
        document_service=document_service,
        success_message="Assigned company set updated ({assigned_count} total)",
    )


@router.put("/documents/{document_id}/companies/batch", response_model=MessageResponse)
def assign_companies_batch(
    document_id: int,
    request: CompanyAssignRequest,
    response: Response,
    if_match: Optional[str] = Header(None, alias="If-Match"),
    current_user: User = Depends(require_permission(Permission.ASSIGN_COMPANIES)),
    assign_company_set_command_handler: AssignCompanySetCommandHandler = Depends(
        get_assign_company_set_command_handler
    ),
    document_service: DocumentService = Depends(get_document_service),
):
    """
    Batch replace company assignments in a single command transaction.

    This endpoint is intended for high-volume assignment workflows and applies
    the same optimistic-concurrency and idempotency safeguards as the existing
    assignment endpoints.
    """
    _ = current_user
    return _apply_company_set_update(
        document_id=document_id,
        request=request,
        if_match=if_match,
        response=response,
        assign_company_set_command_handler=assign_company_set_command_handler,
        document_service=document_service,
        success_message="Batch company assignment updated ({assigned_count} total)",
    )


@router.delete(
    "/documents/{document_id}/assign-companies/{company_id}", response_model=MessageResponse
)
def remove_company_assignment(
    document_id: int,
    company_id: int,
    response: Response,
    if_match: Optional[str] = Header(None, alias="If-Match"),
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

    remaining_company_ids = [c.id for c in document.assigned_companies if c.id != company_id]
    document_service.assign_company_set(
        document_id=document_id,
        company_ids=remaining_company_ids,
        if_match=if_match,
    )
    document = document_service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    response.headers["ETag"] = f"\"{document.etag}\""
    response.headers["X-API-Schema-Version"] = AUDIENCE_ASSIGNMENT_SCHEMA_VERSION

    return MessageResponse(message=f"Removed {company.name} from document")


@router.post("/documents/{document_id}/archive", response_model=dict)
def archive_document(
    document_id: int,
    if_match: Optional[str] = Header(None, alias="If-Match"),
    current_user: User = Depends(require_manager),
    document_service: DocumentService = Depends(get_document_service),
):
    """
    Soft-delete (archive) a document.
    Preserves all data including audience snapshot for potential restore.
    Manager+ access required.
    """
    try:
        result = document_service.archive_document(document_id, current_user, if_match=if_match)
        return result
    except NotFoundError:
        raise
    except InvalidStateError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except PermissionDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


@router.post("/documents/{document_id}/restore", response_model=dict)
def restore_document(
    document_id: int,
    if_match: Optional[str] = Header(None, alias="If-Match"),
    current_user: User = Depends(require_manager),
    document_service: DocumentService = Depends(get_document_service),
):
    """
    Restore an archived document.
    Reconciles audience: removes stale/deleted companies, adjusts visibility if needed.
    Manager+ access required.
    """
    try:
        result = document_service.restore_document(document_id, current_user, if_match=if_match)
        return result
    except NotFoundError:
        raise
    except InvalidStateError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except PermissionDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


@router.get(
    "/documents/{document_id}/calendar-export",
    response_model=DocumentCalendarExportResponse,
)
def export_document_due_date_calendar(
    document_id: int,
    current_user: User = Depends(require_internal_user),
    document_query_handler: GetDocumentQueryHandler = Depends(get_document_query_handler),
):
    """Return an iCal payload for the document due date."""
    _ = current_user
    result = document_query_handler.execute(GetDocumentQuery(document_id=document_id))
    if result.is_err:
        raise NotFoundError(result.error.message)

    document = result.value
    if document.due_date is None:
        raise HTTPException(status_code=404, detail="Document does not have a due date")

    return DocumentCalendarExportResponse(
        document_id=document.id,
        filename=_calendar_filename(document.document_number, document.id),
        due_date=document.due_date,
        ical=_build_document_calendar_export(document=document, due_date=document.due_date),
    )
