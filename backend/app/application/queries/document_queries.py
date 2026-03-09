"""Application queries for document reads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from app.domain.result import Result
from app.models import Document, DocumentStatus, DocumentVisibility
from app.services.document_service import DocumentService


class GetDocumentQueryErrorCode(str, Enum):
    """Expected document query failure categories."""

    NOT_FOUND = "not_found"


@dataclass(frozen=True, slots=True)
class GetDocumentQueryError:
    """Typed document query error payload."""

    code: GetDocumentQueryErrorCode
    message: str


@dataclass(frozen=True, slots=True)
class GetDocumentQuery:
    """Get one document by identifier within caller scope."""

    document_id: int


@dataclass(frozen=True, slots=True)
class ListDocumentsQuery:
    """List documents with pagination and optional filters."""

    skip: int = 0
    limit: int = 100
    status: DocumentStatus | None = None
    visibility: DocumentVisibility | None = None
    category: str | None = None
    search: str | None = None
    company_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None


@dataclass(frozen=True, slots=True)
class ListDocumentsQueryResult:
    """List-documents query result payload."""

    items: list[Document]
    total: int


class GetDocumentQueryHandler:
    """Returns explicit typed query results for document lookups."""

    def __init__(self, service: DocumentService):
        self.service = service

    def execute(self, query: GetDocumentQuery) -> Result[Document, GetDocumentQueryError]:
        document = self.service.get_document(query.document_id)
        if not document:
            return Result.err(
                GetDocumentQueryError(
                    code=GetDocumentQueryErrorCode.NOT_FOUND,
                    message="Document not found",
                )
            )
        return Result.ok(document)


class ListDocumentsQueryHandler:
    """Read handler for paginated document listing."""

    def __init__(self, service: DocumentService):
        self.service = service

    def execute(self, query: ListDocumentsQuery) -> ListDocumentsQueryResult:
        documents, total = self.service.get_documents(
            skip=query.skip,
            limit=query.limit,
            status=query.status,
            visibility=query.visibility,
            category=query.category,
            search=query.search,
            company_id=query.company_id,
            date_from=query.date_from,
            date_to=query.date_to,
        )
        return ListDocumentsQueryResult(items=documents, total=total)
