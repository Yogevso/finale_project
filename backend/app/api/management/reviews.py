"""Review/Approval Workflow API Routes"""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from app.application.commands.dependencies import get_approve_review_command_handler
from app.application.commands.review_commands import (
    ApproveReviewCommand,
    ApproveReviewCommandErrorCode,
    ApproveReviewCommandHandler,
)
from app.application.policies import DocumentAccessPolicy, ReviewPolicy
from app.db import get_chat_db, get_db
from app.domain.aggregates import DocumentAggregate, ReviewAggregate
from app.errors import ConflictError, PermissionDeniedError, ValidationError
from app.models import (
    ActionType,
    Document,
    DocumentStatus,
    NotificationType,
    ReviewRequest,
    ReviewStatus,
    User,
    UserRole,
    Version,
)
from app.schemas import (
    ApprovalPolicyCheck,
    AudienceDiff,
    PreApprovePolicy,
    ReviewAction,
    ReviewListResponse,
    ReviewReject,
    ReviewResponse,
    ReviewSlaProcessResponse,
    ReviewSubmit,
)
from app.security import get_current_active_user
from app.services.audit_helper import write_audit_log
from app.services.notification_service import NotificationService
from app.services.permissions import Permission, has_permission
from app.services.review_sla_service import ReviewSlaService

router = APIRouter(prefix="/reviews", tags=["Reviews"])
review_policy = ReviewPolicy()
document_access_policy = DocumentAccessPolicy()


def _cancel_stale_pending_reviews(
    db: Session,
    document_id: int,
    *,
    exclude_review_id: int | None = None,
) -> int:
    """Cancel all PENDING reviews for a document (except the one being explicitly handled).

    Returns the number of reviews cancelled.
    """
    query = db.query(ReviewRequest).filter(
        ReviewRequest.document_id == document_id,
        ReviewRequest.status == ReviewStatus.PENDING,
    )
    if exclude_review_id is not None:
        query = query.filter(ReviewRequest.id != exclude_review_id)

    now = datetime.utcnow()
    count = 0
    for stale_review in query.all():
        stale_review.status = ReviewStatus.CANCELLED
        stale_review.reviewed_at = now
        count += 1
    return count


def _ensure_document_tenant_access(document: Document, user: User) -> None:
    """Enforce tenant boundary for non-system-admin users."""
    if not document_access_policy.can_access_document_tenant(user, document):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")


def _compute_audience_diff(review: ReviewRequest, document: Document) -> AudienceDiff:
    """Compute the diff between review audience snapshot and current document audience."""
    # Parse snapshot
    snapshot_visibility = review.audience_visibility_snapshot
    snapshot_company_ids = []
    if review.audience_company_ids_snapshot:
        try:
            parsed_ids = json.loads(review.audience_company_ids_snapshot)
            if isinstance(parsed_ids, list):
                snapshot_company_ids = [int(company_id) for company_id in parsed_ids]
        except (TypeError, ValueError, json.JSONDecodeError):
            snapshot_company_ids = []

    # Get current state
    current_visibility = document.visibility.value if document.visibility else None
    current_company_ids = [c.id for c in (document.assigned_companies or [])]

    # Compute diff
    visibility_changed = snapshot_visibility != current_visibility
    snapshot_set = set(snapshot_company_ids)
    current_set = set(current_company_ids)
    companies_added = list(current_set - snapshot_set)
    companies_removed = list(snapshot_set - current_set)

    has_changes = visibility_changed or bool(companies_added) or bool(companies_removed)

    return AudienceDiff(
        has_changes=has_changes,
        snapshot_visibility=snapshot_visibility,
        current_visibility=current_visibility,
        visibility_changed=visibility_changed,
        snapshot_company_ids=snapshot_company_ids,
        current_company_ids=current_company_ids,
        companies_added=companies_added,
        companies_removed=companies_removed,
    )


def can_submit_for_review(user: User) -> bool:
    """Check if user can submit documents for review (editors+)"""
    return review_policy.can_submit_for_review(user)


def can_review_documents(user: User) -> bool:
    """Check if user can review/approve documents (editors+ for peer review, managers+ for final approval)"""
    return review_policy.can_review_documents(user)


def can_approve(user: User, review: ReviewRequest) -> bool:
    """Check if user can approve this specific review
    - User cannot approve their own submission
    - Editors can peer-review (approve other editors' work)
    - Managers+ can approve anyone's work
    """
    return review_policy.can_approve_review(
        reviewer=user,
        submitter=review.submitter,
        has_approve_permission=has_permission(user, Permission.APPROVE_REVIEW),
        has_peer_approve_permission=has_permission(user, Permission.APPROVE_PEER_REVIEW),
    )


def _resolve_review_version_id(
    db: Session,
    *,
    document_id: int,
    requested_version_id: int | None,
) -> int | None:
    """Resolve which unpublished version should be attached to a review request."""
    if requested_version_id:
        version = (
            db.query(Version)
            .filter(
                Version.id == requested_version_id,
                Version.document_id == document_id,
            )
            .first()
        )
        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Version not found for this document",
            )
        if version.is_published:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot submit an already published version for review",
            )
        return version.id

    latest_unpublished_version = (
        db.query(Version)
        .filter(
            Version.document_id == document_id,
            Version.is_published.is_(False),
        )
        .order_by(Version.version_number.desc())
        .first()
    )
    if latest_unpublished_version:
        return latest_unpublished_version.id

    return None


# ========== Submit for Review ==========
@router.post("/documents/{document_id}/submit", response_model=ReviewResponse)
async def submit_for_review(
    document_id: int,
    data: ReviewSubmit,
    db: Session = Depends(get_db),
    chat_db: Session = Depends(get_chat_db),
    current_user: User = Depends(get_current_active_user),
):
    """Submit a document for review"""
    notification_service = NotificationService(db, chat_db=chat_db)

    if not can_submit_for_review(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to submit documents for review",
        )

    # Get document with assigned companies for audience snapshot
    document = (
        db.query(Document)
        .options(joinedload(Document.assigned_companies))
        .filter(Document.id == document_id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    _ensure_document_tenant_access(document, current_user)
    document_aggregate = DocumentAggregate(document)

    if document.status != DocumentStatus.ACTIVE:
        document_aggregate.ensure_submittable_for_review()
    document_aggregate.ensure_audience_ready_for_submit()

    # Reject if there's already a pending review
    existing = (
        db.query(ReviewRequest)
        .filter(
            and_(
                ReviewRequest.document_id == document_id,
                ReviewRequest.status == ReviewStatus.PENDING,
            )
        )
        .first()
    )
    if existing:
        raise ConflictError("Document already has a pending review submission")

    # Validate explicit version or attach latest version automatically
    version_id = _resolve_review_version_id(
        db,
        document_id=document_id,
        requested_version_id=data.version_id,
    )
    if document.status == DocumentStatus.ACTIVE and version_id is None:
        raise ConflictError(
            "Create a new draft version before submitting an active document for review"
        )

    # Capture audience state snapshot
    company_ids = [c.id for c in (document.assigned_companies or [])]
    audience_visibility_snapshot = document.visibility.value if document.visibility else None
    audience_company_ids_snapshot = json.dumps(company_ids) if company_ids else None

    # Create review request
    review = ReviewRequest(
        document_id=document_id,
        version_id=version_id,
        submitted_by=current_user.id,
        message=data.message,
        status=ReviewStatus.PENDING,
        audience_visibility_snapshot=audience_visibility_snapshot,
        audience_company_ids_snapshot=audience_company_ids_snapshot,
        audience_version_snapshot=document.audience_version,
    )
    db.add(review)
    db.flush()

    # Update document status
    document_aggregate.enter_review_submission()

    # Audit event
    write_audit_log(
        user_id=current_user.id,
        document_id=document_id,
        action=ActionType.UPDATE,
        details=f"Submitted review request #{review.id} for version {version_id or 'latest'}",
    )

    # Create notifications for reviewers (editors, managers, admins)
    reviewers = db.query(User).filter(
        and_(
            User.id != current_user.id,
            User.is_active.is_(True),
            User.role.in_(
                [UserRole.EDITOR, UserRole.MANAGER, UserRole.ADMIN, UserRole.SYSTEM_ADMIN]
            ),
        )
    )
    if current_user.role != UserRole.SYSTEM_ADMIN:
        reviewers = reviewers.filter(User.tenant_id == current_user.tenant_id)
    reviewers = reviewers.all()

    for reviewer in reviewers:
        notification_service.create_notification(
            user_id=reviewer.id,
            notification_type=NotificationType.REVIEW_SUBMITTED,
            title="Document submitted for review",
            message=f"{current_user.full_name} submitted '{document.title}' for review",
            link=f"/documents/{document_id}",
        )

    db.commit()
    db.refresh(review)

    # Load relationships
    review = (
        db.query(ReviewRequest)
        .options(
            joinedload(ReviewRequest.document),
            joinedload(ReviewRequest.submitter),
        )
        .filter(ReviewRequest.id == review.id)
        .first()
    )

    return review


# ========== Get Pending Reviews ==========
@router.get("/pending", response_model=ReviewListResponse)
async def get_pending_reviews(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get reviews pending current user's action (excludes own submissions)"""
    if not can_review_documents(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to review documents",
        )

    # Get pending reviews that user can review (not their own)
    query = (
        db.query(ReviewRequest)
        .join(Document, ReviewRequest.document_id == Document.id)
        .options(
            joinedload(ReviewRequest.document),
            joinedload(ReviewRequest.submitter),
        )
        .filter(
            and_(
                ReviewRequest.status == ReviewStatus.PENDING,
                ReviewRequest.submitted_by != current_user.id,
            )
        )
        .order_by(ReviewRequest.submitted_at.desc())
    )
    if current_user.role != UserRole.SYSTEM_ADMIN:
        query = query.filter(Document.tenant_id == current_user.tenant_id)

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return ReviewListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        has_more=(page * per_page) < total,
    )


# ========== Get My Submissions ==========
@router.get("/my-submissions", response_model=ReviewListResponse)
async def get_my_submissions(
    status_filter: Optional[ReviewStatus] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get reviews submitted by current user"""
    query = (
        db.query(ReviewRequest)
        .join(Document, ReviewRequest.document_id == Document.id)
        .options(
            joinedload(ReviewRequest.document),
            joinedload(ReviewRequest.reviewer),
        )
        .filter(ReviewRequest.submitted_by == current_user.id)
    )
    if current_user.role != UserRole.SYSTEM_ADMIN:
        query = query.filter(Document.tenant_id == current_user.tenant_id)

    if status_filter:
        query = query.filter(ReviewRequest.status == status_filter)

    query = query.order_by(ReviewRequest.submitted_at.desc())

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return ReviewListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        has_more=(page * per_page) < total,
    )


@router.post("/sla/process", response_model=ReviewSlaProcessResponse)
async def process_review_sla(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Process reminder and escalation notifications for overdue pending reviews."""
    if current_user.role not in {UserRole.MANAGER, UserRole.ADMIN, UserRole.SYSTEM_ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to process review SLA reminders",
        )

    service = ReviewSlaService(db)
    return service.process_pending_reviews(actor=current_user)


# ========== Get Review Details ==========
@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get review details with audience diff compared to current document state."""
    review = (
        db.query(ReviewRequest)
        .options(
            joinedload(ReviewRequest.document).joinedload(Document.assigned_companies),
            joinedload(ReviewRequest.submitter),
            joinedload(ReviewRequest.reviewer),
        )
        .filter(ReviewRequest.id == review_id)
        .first()
    )

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    _ensure_document_tenant_access(review.document, current_user)

    # Check access - submitter, reviewer, or has review permissions
    if review.submitted_by != current_user.id and not can_review_documents(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this review",
        )

    # Compute audience diff if snapshot exists
    audience_diff = None
    if review.audience_visibility_snapshot:
        audience_diff = _compute_audience_diff(review, review.document)

    # Build response with audience diff
    return ReviewResponse(
        id=review.id,
        document_id=review.document_id,
        version_id=review.version_id,
        submitted_by=review.submitted_by,
        reviewed_by=review.reviewed_by,
        status=review.status,
        message=review.message,
        review_comments=review.review_comments,
        submitted_at=review.submitted_at,
        reviewed_at=review.reviewed_at,
        reviewer_reminded_at=review.reviewer_reminded_at,
        manager_escalated_at=review.manager_escalated_at,
        created_at=review.created_at,
        audience_visibility_snapshot=review.audience_visibility_snapshot,
        audience_company_ids_snapshot=review.audience_company_ids_snapshot,
        audience_diff=audience_diff,
        document=review.document,
        submitter=review.submitter,
        reviewer=review.reviewer,
    )


# ========== Pre-Approve Policy Check ==========
@router.get("/{review_id}/approve/preflight", response_model=PreApprovePolicy)
async def pre_approve_policy(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get pre-approval policy explanation payload.

    Returns a checklist of policy requirements that must be satisfied before
    approving the review, along with human-readable explanations.
    """
    review = (
        db.query(ReviewRequest)
        .options(
            joinedload(ReviewRequest.document).joinedload(Document.assigned_companies),
            joinedload(ReviewRequest.submitter),
        )
        .filter(ReviewRequest.id == review_id)
        .first()
    )

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    _ensure_document_tenant_access(review.document, current_user)

    checks = []
    warnings = []

    # Check 1: Review is pending
    is_pending = review.status == ReviewStatus.PENDING
    checks.append(
        ApprovalPolicyCheck(
            id="review_pending",
            label="Review is pending",
            passed=is_pending,
            message=None if is_pending else f"Review status is {review.status.value}, not pending",
        )
    )

    # Check 2: User can review documents
    can_review = can_review_documents(current_user)
    checks.append(
        ApprovalPolicyCheck(
            id="user_can_review",
            label="User has review permissions",
            passed=can_review,
            message=None if can_review else "User does not have permission to review documents",
        )
    )

    # Check 3: User cannot approve own submission
    not_own_submission = review.submitted_by != current_user.id
    checks.append(
        ApprovalPolicyCheck(
            id="not_own_submission",
            label="Not own submission",
            passed=not_own_submission,
            message=None if not_own_submission else "Cannot approve your own submission",
        )
    )

    # Check 4: User can approve this review (based on role)
    user_can_approve = can_approve(current_user, review) if is_pending else False
    checks.append(
        ApprovalPolicyCheck(
            id="user_can_approve",
            label="User can approve this review",
            passed=user_can_approve,
            message=None if user_can_approve else "User role cannot approve this submission",
        )
    )

    # Check 5: Audience configuration is valid
    try:
        DocumentAggregate(review.document).ensure_audience_ready_for_submit()
        audience_valid = True
        audience_message = None
    except ValidationError as e:
        audience_valid = False
        audience_message = str(e.message)

    checks.append(
        ApprovalPolicyCheck(
            id="audience_valid",
            label="Audience configuration valid",
            passed=audience_valid,
            message=audience_message,
        )
    )

    # Check for audience drift
    if review.audience_visibility_snapshot:
        audience_diff = _compute_audience_diff(review, review.document)
        if audience_diff.has_changes:
            warnings.append(
                f"Audience has changed since submission: "
                f"visibility {audience_diff.snapshot_visibility} -> {audience_diff.current_visibility}"
            )
            if audience_diff.companies_added:
                warnings.append(f"Companies added: {audience_diff.companies_added}")
            if audience_diff.companies_removed:
                warnings.append(f"Companies removed: {audience_diff.companies_removed}")

    # Build audience summary
    doc = review.document
    visibility = doc.visibility.value if doc.visibility else "internal"
    company_count = len(doc.assigned_companies or [])
    if visibility == "public":
        audience_summary = "Document will be visible to everyone (public)"
    elif visibility == "company" and company_count > 0:
        company_names = [c.name for c in doc.assigned_companies[:3]]
        if company_count > 3:
            company_names.append(f"and {company_count - 3} more")
        audience_summary = f"Document visible to: {', '.join(company_names)}"
    else:
        audience_summary = "Document is internal only"

    can_approve_result = all(c.passed for c in checks)

    return PreApprovePolicy(
        can_approve=can_approve_result,
        checks=checks,
        audience_summary=audience_summary,
        warnings=warnings,
    )


# ========== Approve Review ==========
@router.post("/{review_id}/approve", response_model=ReviewResponse)
async def approve_review(
    review_id: int,
    data: ReviewAction,
    current_user: User = Depends(get_current_active_user),
    approve_review_command_handler: ApproveReviewCommandHandler = Depends(
        get_approve_review_command_handler
    ),
):
    """Approve a review request"""
    result = approve_review_command_handler.execute(
        ApproveReviewCommand(
            review_id=review_id,
            comments=data.comments,
            current_user=current_user,
        )
    )
    if result.is_err:
        if result.error.code == ApproveReviewCommandErrorCode.NOT_FOUND:
            detail = result.error.message
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail,
            )
        if result.error.code == ApproveReviewCommandErrorCode.PERMISSION_DENIED:
            raise PermissionDeniedError(result.error.message)
        if result.error.code == ApproveReviewCommandErrorCode.CONFLICT:
            raise ConflictError(result.error.message)
        if result.error.code == ApproveReviewCommandErrorCode.VALIDATION:
            raise ValidationError(result.error.message)
        raise HTTPException(status_code=500, detail="Unexpected approve-review command error")

    return result.value


# ========== Reject Review ==========
@router.post("/{review_id}/reject", response_model=ReviewResponse)
async def reject_review(
    review_id: int,
    data: ReviewReject,
    db: Session = Depends(get_db),
    chat_db: Session = Depends(get_chat_db),
    current_user: User = Depends(get_current_active_user),
):
    """Reject a review request (comments required)"""
    notification_service = NotificationService(db, chat_db=chat_db)

    review = (
        db.query(ReviewRequest)
        .options(
            joinedload(ReviewRequest.document),
            joinedload(ReviewRequest.submitter),
        )
        .filter(ReviewRequest.id == review_id)
        .first()
    )

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    _ensure_document_tenant_access(review.document, current_user)
    review_aggregate = ReviewAggregate(review)
    document_aggregate = DocumentAggregate(review.document)

    review_aggregate.ensure_pending()

    if not can_approve(current_user, review):
        raise PermissionDeniedError("You cannot reject this review")

    # Reject the review

    review_aggregate.reject(
        reviewer_id=current_user.id,
        comments=data.comments,
        reviewed_at=datetime.utcnow(),
    )

    # Return document to draft
    document_aggregate.revert_review_submission()

    # H-16: cancel any other orphaned PENDING reviews for this document
    _cancel_stale_pending_reviews(db, review.document_id, exclude_review_id=review.id)

    # Notify submitter
    notification_service.create_notification(
        user_id=review.submitted_by,
        notification_type=NotificationType.REVIEW_REJECTED,
        title="Document rejected",
        message=f"Your document '{review.document.title}' was rejected by {current_user.full_name}. Reason: {data.comments[:100]}...",
        link=f"/documents/{review.document_id}",
    )
    write_audit_log(
        user_id=current_user.id,
        document_id=review.document_id,
        action=ActionType.UPDATE,
        details=f"Rejected review #{review.id} for version {review.version_id or 'n/a'}",
    )

    db.commit()
    db.refresh(review)

    # Reload with relationships
    review = (
        db.query(ReviewRequest)
        .options(
            joinedload(ReviewRequest.document),
            joinedload(ReviewRequest.submitter),
            joinedload(ReviewRequest.reviewer),
        )
        .filter(ReviewRequest.id == review.id)
        .first()
    )

    return review


# ========== Cancel Submission ==========
@router.post("/{review_id}/cancel", response_model=ReviewResponse)
async def cancel_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Cancel own review submission.

    This restores the document to draft status. Note that any company assignments
    made after submission are preserved - the cancellation does NOT roll back
    audience changes. The review's audience snapshot remains for audit purposes.
    """
    review = (
        db.query(ReviewRequest)
        .options(
            joinedload(ReviewRequest.document).joinedload(Document.assigned_companies),
        )
        .filter(ReviewRequest.id == review_id)
        .first()
    )

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    _ensure_document_tenant_access(review.document, current_user)
    review_aggregate = ReviewAggregate(review)
    document_aggregate = DocumentAggregate(review.document)

    review_aggregate.ensure_submitter(current_user.id)
    review_aggregate.ensure_pending()

    # Compute audience diff before cancellation for audit trail
    audience_diff = None
    if review.audience_visibility_snapshot:
        audience_diff = _compute_audience_diff(review, review.document)

    # Cancel the review
    review_aggregate.cancel(reviewed_at=datetime.utcnow())

    # Return document to draft
    document_aggregate.revert_review_submission()

    # H-16: cancel any other orphaned PENDING reviews for this document
    _cancel_stale_pending_reviews(db, review.document_id, exclude_review_id=review.id)

    # Enhanced audit log with audience reconciliation info
    diff_info = ""
    if audience_diff and audience_diff.has_changes:
        diff_info = (
            f" Audience changed since submission: "
            f"visibility {audience_diff.snapshot_visibility} -> {audience_diff.current_visibility}, "
            f"companies added={audience_diff.companies_added}, "
            f"companies removed={audience_diff.companies_removed}"
        )
    write_audit_log(
        user_id=current_user.id,
        document_id=review.document_id,
        action=ActionType.UPDATE,
        details=f"Cancelled review #{review.id} for version {review.version_id or 'n/a'}.{diff_info}",
    )

    db.commit()
    db.refresh(review)

    # Return response with audience diff
    return ReviewResponse(
        id=review.id,
        document_id=review.document_id,
        version_id=review.version_id,
        submitted_by=review.submitted_by,
        reviewed_by=review.reviewed_by,
        status=review.status,
        message=review.message,
        review_comments=review.review_comments,
        submitted_at=review.submitted_at,
        reviewed_at=review.reviewed_at,
        reviewer_reminded_at=review.reviewer_reminded_at,
        manager_escalated_at=review.manager_escalated_at,
        created_at=review.created_at,
        audience_visibility_snapshot=review.audience_visibility_snapshot,
        audience_company_ids_snapshot=review.audience_company_ids_snapshot,
        audience_diff=audience_diff,
        document=review.document,
        submitter=review.submitter,
        reviewer=review.reviewer,
    )


# ========== Get Document Review History ==========
@router.get("/documents/{document_id}/history", response_model=ReviewListResponse)
async def get_document_review_history(
    document_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get all reviews for a document"""
    # Verify document exists
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    _ensure_document_tenant_access(document, current_user)

    query = (
        db.query(ReviewRequest)
        .options(
            joinedload(ReviewRequest.submitter),
            joinedload(ReviewRequest.reviewer),
        )
        .filter(ReviewRequest.document_id == document_id)
        .order_by(ReviewRequest.submitted_at.desc())
    )

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return ReviewListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        has_more=(page * per_page) < total,
    )
