"""Application commands for review workflow operations."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from sqlalchemy import update
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
from app.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from app.models import (
    ActionType,
    AuditLog,
    Document,
    NotificationType,
    ReviewRequest,
    ReviewStatus,
    Tenant,
    User,
    Version,
)
from app.services.notification_service import NotificationService
from app.services.permissions import Permission, has_permission

logger = logging.getLogger(__name__)


class ApproveReviewCommandErrorCode(str, Enum):
    """Expected approve-review command failure categories."""

    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    CONFLICT = "conflict"
    VALIDATION = "validation"


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
        chat_db: Session | None = None,
        review_policy: ReviewPolicy | None = None,
        document_access_policy: DocumentAccessPolicy | None = None,
    ):
        self.db = db
        self.notification_service = NotificationService(db, chat_db=chat_db)
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

    def _load_review(
        self,
        review_id: int,
        *,
        for_update: bool = False,
    ) -> ReviewRequest | None:
        query = (
            self.db.query(ReviewRequest)
            .options(
                joinedload(ReviewRequest.document).joinedload(Document.assigned_companies),
                joinedload(ReviewRequest.submitter),
            )
            .filter(ReviewRequest.id == review_id)
            .populate_existing()
        )
        if for_update and self.db.bind is not None and self.db.bind.dialect.name != "sqlite":
            query = query.with_for_update()
        return query.first()

    def _approve_pending_review_row(
        self,
        *,
        review_id: int,
        reviewer_id: int,
        comments: str | None,
        reviewed_at: datetime,
    ) -> None:
        approval_stmt = (
            update(ReviewRequest)
            .where(
                ReviewRequest.id == review_id,
                ReviewRequest.status == ReviewStatus.PENDING,
            )
            .values(
                status=ReviewStatus.APPROVED,
                reviewed_by=reviewer_id,
                review_comments=comments,
                reviewed_at=reviewed_at,
            )
        )
        update_result = self.db.execute(approval_stmt)
        if update_result.rowcount != 1:
            raise ConflictError("This review has already been processed by another reviewer")

    def _validate(self, context: CommandContext[ApproveReviewCommand]) -> None:
        review = self._load_review(context.command.review_id)
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
        if not self.document_access_policy.can_access_document_tenant(
            current_user, review.document
        ):
            raise NotFoundError("Document not found")

        can_approve = self.review_policy.can_approve_review(
            reviewer=current_user,
            submitter=review.submitter,
            has_approve_permission=has_permission(current_user, Permission.APPROVE_REVIEW),
            has_peer_approve_permission=has_permission(
                current_user, Permission.APPROVE_PEER_REVIEW
            ),
        )
        if not can_approve:
            raise PermissionDeniedError(
                "You cannot approve this review (cannot approve own submission)"
            )

    def _execute_command(self, context: CommandContext[ApproveReviewCommand]) -> ReviewRequest:
        review = self._load_review(context.command.review_id, for_update=True)
        if not review:
            raise NotFoundError("Review not found")
        context.state["review"] = review

        ReviewAggregate(review)
        document_aggregate = DocumentAggregate(review.document)
        current_user = context.command.current_user
        document = review.document

        # Validate audience only after authorization to preserve tenant-boundary 404 semantics.
        document_aggregate.ensure_audience_ready_for_submit()

        # Perform audience resolution before approval
        audience_resolution = self._resolve_audience_drift(review, document)
        if audience_resolution["has_drift"]:
            logger.info(
                "Review approve audience resolution for review=%d document=%d: %s",
                review.id,
                document.id,
                json.dumps(audience_resolution),
            )
            # Store resolution info on context for audit
            context.state["audience_resolution"] = audience_resolution

        # Optimistic lock: reject approval if audience changed since submission
        if (
            review.audience_version_snapshot is not None
            and document.audience_version != review.audience_version_snapshot
        ):
            raise ConflictError(
                "Audience has changed since this review was submitted — "
                "re-submit for review required."
            )

        reviewed_at = datetime.utcnow()
        self._approve_pending_review_row(
            review_id=review.id,
            reviewer_id=current_user.id,
            comments=context.command.comments,
            reviewed_at=reviewed_at,
        )
        review.status = ReviewStatus.APPROVED
        review.reviewed_by = current_user.id
        review.review_comments = context.command.comments
        review.reviewed_at = reviewed_at
        document_aggregate.finalize_review_approval()

        # Build audit details with audience resolution
        audit_details = f"Approved review #{review.id} for version {review.version_id or 'n/a'}"
        if audience_resolution["has_drift"]:
            resolution_summary = []
            if audience_resolution.get("visibility_change"):
                resolution_summary.append(
                    f"visibility: {audience_resolution['visibility_change']['from']} -> "
                    f"{audience_resolution['visibility_change']['to']}"
                )
            if audience_resolution.get("removed_stale_companies"):
                stale_names = [c["name"] for c in audience_resolution["removed_stale_companies"]]
                resolution_summary.append(f"removed stale companies: {stale_names}")
            if audience_resolution.get("companies_added"):
                resolution_summary.append(
                    f"companies added since submit: {audience_resolution['companies_added']}"
                )
            if audience_resolution.get("companies_removed"):
                resolution_summary.append(
                    f"companies removed since submit: {audience_resolution['companies_removed']}"
                )
            if resolution_summary:
                audit_details += f" | Audience resolution: {'; '.join(resolution_summary)}"

        self.db.add(
            AuditLog(
                user_id=current_user.id,
                document_id=review.document_id,
                action=ActionType.UPDATE,
                details=audit_details,
            )
        )
        self.notification_service.create_notification(
            user_id=review.submitted_by,
            notification_type=NotificationType.REVIEW_APPROVED,
            title="Document approved",
            message=f"Your document '{review.document.title}' has been approved by {current_user.full_name}",
            link=f"/documents/{review.document_id}",
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

    def _resolve_audience_drift(self, review: ReviewRequest, document) -> dict:
        """
        Detect and resolve audience drift between submit snapshot and current state.
        Returns resolution details for audit trail.
        """
        result = {
            "has_drift": False,
            "snapshot_visibility": review.audience_visibility_snapshot,
            "current_visibility": document.visibility.value if document.visibility else None,
            "visibility_change": None,
            "snapshot_company_ids": [],
            "current_company_ids": [],
            "companies_added": [],
            "companies_removed": [],
            "removed_stale_companies": [],
        }

        # Parse snapshot company IDs
        if review.audience_company_ids_snapshot:
            try:
                result["snapshot_company_ids"] = json.loads(review.audience_company_ids_snapshot)
            except (json.JSONDecodeError, TypeError):
                result["snapshot_company_ids"] = []

        # Get current company IDs
        result["current_company_ids"] = [c.id for c in (document.assigned_companies or [])]

        # Detect visibility change
        if result["snapshot_visibility"] != result["current_visibility"]:
            result["has_drift"] = True
            result["visibility_change"] = {
                "from": result["snapshot_visibility"],
                "to": result["current_visibility"],
            }

        # Detect company changes
        snapshot_set = set(result["snapshot_company_ids"])
        current_set = set(result["current_company_ids"])

        result["companies_added"] = list(current_set - snapshot_set)
        result["companies_removed"] = list(snapshot_set - current_set)

        if result["companies_added"] or result["companies_removed"]:
            result["has_drift"] = True

        # Detect stale companies in current assignment
        if result["current_company_ids"]:
            stale_companies = (
                self.db.query(Tenant)
                .filter(
                    Tenant.id.in_(result["current_company_ids"]),
                    Tenant.is_active.is_(False),
                )
                .all()
            )
            if stale_companies:
                result["has_drift"] = True
                result["removed_stale_companies"] = [
                    {"id": c.id, "name": c.name, "reason": "deactivated"} for c in stale_companies
                ]
                # Note: We don't actually remove stale companies here - that's done
                # at publish time. We just record them for the audit trail.
                # The publish_version method enforces the stale company block.

        return result

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
        except ValidationError as exc:
            return Result.err(
                ApproveReviewCommandError(
                    code=ApproveReviewCommandErrorCode.VALIDATION,
                    message=exc.message,
                )
            )
