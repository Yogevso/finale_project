"""Application command handlers and dependency providers."""

from app.application.commands.document_commands import (
    AssignCompanySetCommand,
    AssignCompanySetCommandError,
    AssignCompanySetCommandErrorCode,
    AssignCompanySetCommandHandler,
    CreateDocumentCommand,
    CreateDocumentCommandHandler,
    DeleteDocumentCommand,
    DeleteDocumentCommandHandler,
    DocumentCommandError,
    DocumentCommandErrorCode,
    UpdateDocumentCommand,
    UpdateDocumentCommandHandler,
)
from app.application.commands.review_commands import (
    ApproveReviewCommand,
    ApproveReviewCommandError,
    ApproveReviewCommandErrorCode,
    ApproveReviewCommandHandler,
)
from app.application.commands.version_commands import (
    PublishApprovedVersionCommand,
    PublishApprovedVersionCommandError,
    PublishApprovedVersionCommandErrorCode,
    PublishApprovedVersionCommandHandler,
)

__all__ = [
    "AssignCompanySetCommand",
    "AssignCompanySetCommandError",
    "AssignCompanySetCommandErrorCode",
    "AssignCompanySetCommandHandler",
    "CreateDocumentCommand",
    "CreateDocumentCommandHandler",
    "DeleteDocumentCommand",
    "DeleteDocumentCommandHandler",
    "DocumentCommandError",
    "DocumentCommandErrorCode",
    "ApproveReviewCommand",
    "ApproveReviewCommandError",
    "ApproveReviewCommandErrorCode",
    "ApproveReviewCommandHandler",
    "PublishApprovedVersionCommand",
    "PublishApprovedVersionCommandError",
    "PublishApprovedVersionCommandErrorCode",
    "PublishApprovedVersionCommandHandler",
    "UpdateDocumentCommand",
    "UpdateDocumentCommandHandler",
]
