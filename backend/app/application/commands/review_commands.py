"""Application commands for review workflow operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.application.pipeline import (
    CommandContext,
    CommandExecutionTrace,
    CommandPipeline,
    FunctionCommandAuthorizer,
    FunctionCommandExecutor,
    FunctionCommandPublisher,
    FunctionCommandValidator,
)
from app.application.policies import DocumentAccessPolicy, ReviewPolicy
from app.domain.aggregates import DocumentAggregate, ReviewAggregate
from app.domain.result import Result
from app.errors import ConflictError, NotFoundError, PermissionDeniedError
from app.models import (
    ActionType,
    AuditLog,
    Notification,
    NotificationType,
    ReviewRequest,
    User,
    Version,
)
from app.services.permissions import Permission, has_permission


class ApproveReviewCommandErrorCode(str, Enum):
    """Expected approve-review command failure categories."""

    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    CONFLICT = "conflict"


@dataclass(frozen=True, slots=True)
class ApproveReviewCommandError:
    """Typed approve-review command error payload."""

    code: ApproveReviewCommandErrorCode
    message: str


@dataclass(frozen=True, slots=True)
class ApproveReviewCommand:
    """Approve a pending review request."""

    review_id: int
    comments: str | None
    current_user: User


class ApproveReviewCommandHandler:
    """Converts expected approve-review failures into typed Result errors."""

    def __init__(
        self,
        db: Session,
        *,
        review_policy: ReviewPolicy | None = None,
        document_access_policy: DocumentAccessPolicy | None = None,
    ):
        self.db = db
        self.review_policy = review_policy or ReviewPolicy()
        self.document_access_policy = document_access_policy or DocumentAccessPolicy()
        self._last_trace: CommandExecutionTrace | None = None
        self._pipeline = CommandPipeline[ApproveReviewCommand, ReviewRequest](
            validator=FunctionCommandValidator(self._validate),
            authorizer=FunctionCommandAuthorizer(self._authorize),
            executor=FunctionCommandExecutor(self._execute_command),
            publisher=FunctionCommandPublisher(self._publish),
        )

    @property
    def last_trace(self) -> CommandExecutionTrace | None:
        return self._last_trace

    def _validate(self, context: CommandContext[ApproveReviewCommand]) -> None:
        review = (
            self.db.query(ReviewRequest)
            .options(
                joinedload(ReviewRequest.document),
                joinedload(ReviewRequest.submitter),
            )
            .filter(ReviewRequest.id == context.command.review_id)
            .first()
        )
        if not review:
            raise NotFoundError("Review not found")

        review_aggregate = ReviewAggregate(review)
        review_aggregate.ensure_pending()

        if review.version_id:
            review_version = (
                self.db.query(Version)
                .filter(Version.id == review.version_id, Version.document_id == review.document_id)
                .first()
            )
            latest_version = (
                self.db.query(Version)
                .filter(Version.document_id == review.document_id)
                .order_by(Version.version_number.desc())
                .first()
            )
            review_aggregate.ensure_approvable_version(
                review_version=review_version,
                latest_version=latest_version,
            )

        context.state["review"] = review

    def _authorize(self, context: CommandContext[ApproveReviewCommand]) -> None:
        review = context.state["review"]
        if not isinstance(review, ReviewRequest):
            raise RuntimeError("Missing review in command context")

        current_user = context.command.current_user
        if not self.document_access_policy.can_access_document_tenant(current_user, review.document):
            raise NotFoundError("Document not found")

        can_approve = self.review_policy.can_approve_review(
            reviewer=current_user,
            submitter=review.submitter,
            has_approve_permission=has_permission(current_user, Permission.APPROVE_REVIEW),
            has_peer_approve_permission=has_permission(current_user, Permission.APPROVE_PEER_REVIEW),
        )
        if not can_approve:
            raise PermissionDeniedError(
                "You cannot approve this review (cannot approve own submission)"
            )

    def _execute_command(self, context: CommandContext[ApproveReviewCommand]) -> ReviewRequest:
        review = context.state["review"]
        if not isinstance(review, ReviewRequest):
            raise RuntimeError("Missing review in command context")

        review_aggregate = ReviewAggregate(review)
        document_aggregate = DocumentAggregate(review.document)
        current_user = context.command.current_user

        review_aggregate.approve(
            reviewer_id=current_user.id,
            comments=context.command.comments,
            reviewed_at=datetime.utcnow(),
        )
        document_aggregate.transition_to_approved()

        self.db.add(
            AuditLog(
                user_id=current_user.id,
                document_id=review.document_id,
                action=ActionType.UPDATE,
                details=f"Approved review #{review.id} for version {review.version_id or 'n/a'}",
            )
        )
        self.db.add(
            Notification(
                user_id=review.submitted_by,
                type=NotificationType.REVIEW_APPROVED,
                title="Document approved",
                message=f"Your document '{review.document.title}' has been approved by {current_user.full_name}",
                link=f"/documents/{review.document_id}",
            )
        )

        self.db.commit()
        self.db.refresh(review)

        return (
            self.db.query(ReviewRequest)
            .options(
                joinedload(ReviewRequest.document),
                joinedload(ReviewRequest.submitter),
                joinedload(ReviewRequest.reviewer),
            )
            .filter(ReviewRequest.id == review.id)
            .first()
        )

    def _publish(
        self, context: CommandContext[ApproveReviewCommand], result: ReviewRequest
    ) -> None:
        _ = (context, result)

    def execute(
        self,
        command: ApproveReviewCommand,
    ) -> Result[ReviewRequest, ApproveReviewCommandError]:
        try:
            run = self._pipeline.run(command)
            self._last_trace = run.trace
            return Result.ok(run.value)
        except NotFoundError as exc:
            return Result.err(
                ApproveReviewCommandError(
                    code=ApproveReviewCommandErrorCode.NOT_FOUND,
                    message=exc.message,
                )
            )
        except PermissionDeniedError as exc:
            return Result.err(
                ApproveReviewCommandError(
                    code=ApproveReviewCommandErrorCode.PERMISSION_DENIED,
                    message=exc.message,
                )
            )
        except ConflictError as exc:
            return Result.err(
                ApproveReviewCommandError(
                    code=ApproveReviewCommandErrorCode.CONFLICT,
                    message=exc.message,
                )
            )
        except HTTPException as exc:
            if exc.status_code == status.HTTP_404_NOT_FOUND:
                return Result.err(
                    ApproveReviewCommandError(
                        code=ApproveReviewCommandErrorCode.NOT_FOUND,
                        message=str(exc.detail),
                    )
                )
            if exc.status_code == status.HTTP_403_FORBIDDEN:
                return Result.err(
                    ApproveReviewCommandError(
                        code=ApproveReviewCommandErrorCode.PERMISSION_DENIED,
                        message=str(exc.detail),
                    )
                )
            if exc.status_code == status.HTTP_409_CONFLICT:
                return Result.err(
                    ApproveReviewCommandError(
                        code=ApproveReviewCommandErrorCode.CONFLICT,
                        message=str(exc.detail),
                    )
                )
            raise
