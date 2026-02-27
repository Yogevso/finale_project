"""Review/Approval Workflow API Routes"""

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
from app.db import get_db
from app.domain.aggregates import DocumentAggregate, ReviewAggregate
from app.errors import ConflictError, PermissionDeniedError
from app.models import (
    ActionType,
    AuditLog,
    Document,
    Notification,
    NotificationType,
    ReviewRequest,
    ReviewStatus,
    User,
    UserRole,
    Version,
)
from app.schemas import (
    ReviewAction,
    ReviewListResponse,
    ReviewReject,
    ReviewResponse,
    ReviewSubmit,
)
from app.security import get_current_active_user
from app.services.permissions import Permission, has_permission

router = APIRouter(prefix="/reviews", tags=["Reviews"])
review_policy = ReviewPolicy()
document_access_policy = DocumentAccessPolicy()


def _ensure_document_tenant_access(document: Document, user: User) -> None:
    """Enforce tenant boundary for non-system-admin users."""
    if not document_access_policy.can_access_document_tenant(user, document):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")


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


# ========== Submit for Review ==========
@router.post("/documents/{document_id}/submit", response_model=ReviewResponse)
async def submit_for_review(
    document_id: int,
    data: ReviewSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Submit a document for review"""
    if not can_submit_for_review(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to submit documents for review",
        )

    # Get document
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    _ensure_document_tenant_access(document, current_user)
    document_aggregate = DocumentAggregate(document)

    document_aggregate.ensure_submittable_for_review()

    # Check for existing pending review
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
        raise ConflictError("This document already has a pending review")

    # Validate explicit version or attach latest version automatically
    version_id = data.version_id
    if version_id:
        version = (
            db.query(Version)
            .filter(
                Version.id == version_id,
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
    else:
        latest_version = (
            db.query(Version)
            .filter(Version.document_id == document_id)
            .order_by(Version.version_number.desc())
            .first()
        )
        if latest_version:
            version_id = latest_version.id

    # Create review request
    review = ReviewRequest(
        document_id=document_id,
        version_id=version_id,
        submitted_by=current_user.id,
        message=data.message,
        status=ReviewStatus.PENDING,
    )
    db.add(review)
    db.flush()

    # Update document status
    document_aggregate.transition_to_pending_review()

    # Audit event
    db.add(
        AuditLog(
            user_id=current_user.id,
            document_id=document_id,
            action=ActionType.UPDATE,
            details=f"Submitted review request #{review.id} for version {version_id or 'latest'}",
        )
    )

    # Create notifications for reviewers (editors, managers, admins)
    reviewers = (
        db.query(User)
        .filter(
            and_(
                User.id != current_user.id,
                User.is_active.is_(True),
                User.role.in_(
                    [UserRole.EDITOR, UserRole.MANAGER, UserRole.ADMIN, UserRole.SYSTEM_ADMIN]
                ),
            )
        )
    )
    if current_user.role != UserRole.SYSTEM_ADMIN:
        reviewers = reviewers.filter(User.tenant_id == current_user.tenant_id)
    reviewers = reviewers.all()

    for reviewer in reviewers:
        notification = Notification(
            user_id=reviewer.id,
            type=NotificationType.REVIEW_SUBMITTED,
            title="Document submitted for review",
            message=f"{current_user.full_name} submitted '{document.title}' for review",
            link=f"/documents/{document_id}",
        )
        db.add(notification)

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


# ========== Get Review Details ==========
@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get review details"""
    review = (
        db.query(ReviewRequest)
        .options(
            joinedload(ReviewRequest.document),
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

    return review


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
        raise HTTPException(status_code=500, detail="Unexpected approve-review command error")

    return result.value


# ========== Reject Review ==========
@router.post("/{review_id}/reject", response_model=ReviewResponse)
async def reject_review(
    review_id: int,
    data: ReviewReject,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Reject a review request (comments required)"""
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
    document_aggregate.transition_to_draft()

    # Notify submitter
    notification = Notification(
        user_id=review.submitted_by,
        type=NotificationType.REVIEW_REJECTED,
        title="Document rejected",
        message=f"Your document '{review.document.title}' was rejected by {current_user.full_name}. Reason: {data.comments[:100]}...",
        link=f"/documents/{review.document_id}",
    )
    db.add(notification)
    db.add(
        AuditLog(
            user_id=current_user.id,
            document_id=review.document_id,
            action=ActionType.UPDATE,
            details=f"Rejected review #{review.id} for version {review.version_id or 'n/a'}",
        )
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
    """Cancel own review submission"""
    review = (
        db.query(ReviewRequest)
        .options(
            joinedload(ReviewRequest.document),
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

    # Cancel the review
    review_aggregate.cancel(reviewed_at=datetime.utcnow())

    # Return document to draft
    document_aggregate.transition_to_draft()
    db.add(
        AuditLog(
            user_id=current_user.id,
            document_id=review.document_id,
            action=ActionType.UPDATE,
            details=f"Cancelled review #{review.id} for version {review.version_id or 'n/a'}",
        )
    )

    db.commit()
    db.refresh(review)

    return review


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
