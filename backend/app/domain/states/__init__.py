"""Domain workflow stage objects."""

from app.domain.states.document_stage import (
    ActiveDocumentStage,
    ApprovedDocumentStage,
    ArchivedDocumentStage,
    DocumentStage,
    DraftDocumentStage,
    PendingReviewDocumentStage,
    document_stage_for,
)
from app.domain.states.review_stage import (
    ApprovedReviewStage,
    CancelledReviewStage,
    NoReviewStage,
    PendingReviewStage,
    RejectedReviewStage,
    ReviewStage,
    VersionReviewStage,
    review_stage_for,
    version_review_stage_for,
)

__all__ = [
    "ActiveDocumentStage",
    "ApprovedDocumentStage",
    "ApprovedReviewStage",
    "ArchivedDocumentStage",
    "CancelledReviewStage",
    "DocumentStage",
    "DraftDocumentStage",
    "NoReviewStage",
    "PendingReviewDocumentStage",
    "PendingReviewStage",
    "RejectedReviewStage",
    "ReviewStage",
    "VersionReviewStage",
    "document_stage_for",
    "review_stage_for",
    "version_review_stage_for",
]
