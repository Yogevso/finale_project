"""Review/Approval Workflow API Routes"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models import (
    Document,
    DocumentStatus,
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
from app.security import get_current_user

router = APIRouter(prefix="/reviews", tags=["Reviews"])


def can_submit_for_review(user: User) -> bool:
    """Check if user can submit documents for review (editors+)"""
    return user.role in [UserRole.EDITOR, UserRole.MANAGER, UserRole.ADMIN, UserRole.SYSTEM_ADMIN]


def can_review_documents(user: User) -> bool:
    """Check if user can review/approve documents (editors+ for peer review, managers+ for final approval)"""
    return user.role in [UserRole.EDITOR, UserRole.MANAGER, UserRole.ADMIN, UserRole.SYSTEM_ADMIN]


def can_approve(user: User, review: ReviewRequest) -> bool:
    """Check if user can approve this specific review
    - User cannot approve their own submission
    - Editors can peer-review (approve other editors' work)
    - Managers+ can approve anyone's work
    """
    # Cannot approve own submission
    if user.id == review.submitted_by:
        return False

    # Editors can peer-review other editors
    # Managers and above can approve anyone
    return user.role in [UserRole.EDITOR, UserRole.MANAGER, UserRole.ADMIN, UserRole.SYSTEM_ADMIN]


# ========== Submit for Review ==========
@router.post("/documents/{document_id}/submit", response_model=ReviewResponse)
async def submit_for_review(
    document_id: int,
    data: ReviewSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    # Check document status - must be draft
    if document.status != DocumentStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document must be in draft status to submit for review. Current status: {document.status.value}",
        )

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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This document already has a pending review",
        )

    # If no version was provided, attach the latest version automatically
    version_id = data.version_id
    if not version_id:
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

    # Update document status
    document.status = DocumentStatus.PENDING_REVIEW

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
        .all()
    )

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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
):
    """Get reviews submitted by current user"""
    query = (
        db.query(ReviewRequest)
        .options(
            joinedload(ReviewRequest.document),
            joinedload(ReviewRequest.reviewer),
        )
        .filter(ReviewRequest.submitted_by == current_user.id)
    )

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
    current_user: User = Depends(get_current_user),
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve a review request"""
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

    if review.status != ReviewStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Review is not pending. Current status: {review.status.value}",
        )

    if not can_approve(current_user, review):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot approve this review (cannot approve own submission)",
        )

    # Approve the review
    from datetime import datetime

    review.status = ReviewStatus.APPROVED
    review.reviewed_by = current_user.id
    review.review_comments = data.comments
    review.reviewed_at = datetime.utcnow()

    # Update document status to active
    review.document.status = DocumentStatus.ACTIVE
    
    # If this review has a version, mark it as published
    if review.version_id:
        version = db.query(Version).filter(Version.id == review.version_id).first()
        if version:
            version.is_published = True
            version.published_at = datetime.utcnow()

    # Notify submitter
    notification = Notification(
        user_id=review.submitted_by,
        type=NotificationType.REVIEW_APPROVED,
        title="Document approved",
        message=f"Your document '{review.document.title}' has been approved by {current_user.full_name}",
        link=f"/documents/{review.document_id}",
    )
    db.add(notification)

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


# ========== Reject Review ==========
@router.post("/{review_id}/reject", response_model=ReviewResponse)
async def reject_review(
    review_id: int,
    data: ReviewReject,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    if review.status != ReviewStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Review is not pending. Current status: {review.status.value}",
        )

    if not can_approve(current_user, review):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You cannot reject this review"
        )

    # Reject the review
    from datetime import datetime

    review.status = ReviewStatus.REJECTED
    review.reviewed_by = current_user.id
    review.review_comments = data.comments
    review.reviewed_at = datetime.utcnow()

    # Return document to draft
    review.document.status = DocumentStatus.DRAFT

    # Notify submitter
    notification = Notification(
        user_id=review.submitted_by,
        type=NotificationType.REVIEW_REJECTED,
        title="Document rejected",
        message=f"Your document '{review.document.title}' was rejected by {current_user.full_name}. Reason: {data.comments[:100]}...",
        link=f"/documents/{review.document_id}",
    )
    db.add(notification)

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
    current_user: User = Depends(get_current_user),
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

    if review.submitted_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You can only cancel your own submissions"
        )

    if review.status != ReviewStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel review with status: {review.status.value}",
        )

    # Cancel the review
    from datetime import datetime

    review.status = ReviewStatus.CANCELLED
    review.reviewed_at = datetime.utcnow()

    # Return document to draft
    review.document.status = DocumentStatus.DRAFT

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
    current_user: User = Depends(get_current_user),
):
    """Get all reviews for a document"""
    # Verify document exists
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

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
