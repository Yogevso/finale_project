"""
Feedback Management API - Admin/Manager endpoints for managing customer feedback
"""

from datetime import datetime
from typing import List, Optional, Set

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models import (
    Attachment,
    Comment,
    Document,
    Feedback,
    FeedbackStatus,
    FeedbackType,
    Notification,
    NotificationType,
    Tenant,
    User,
    UserRole,
    Version,
)
from app.security import get_current_user


def get_document_contributors(db: Session, document_id: int) -> Set[int]:
    """
    Get all user IDs who have 'touched' (contributed to) a document.
    This includes:
    - Document creator
    - Version creators (editors)
    - Attachment uploaders
    - Commenters
    """
    contributors: Set[int] = set()
    
    # Get document creator
    document = db.query(Document).filter(Document.id == document_id).first()
    if document:
        contributors.add(document.created_by)
    
    # Get version creators
    versions = db.query(Version.created_by).filter(Version.document_id == document_id).distinct().all()
    for (user_id,) in versions:
        contributors.add(user_id)
    
    # Get attachment uploaders
    attachments = db.query(Attachment.uploaded_by).filter(Attachment.document_id == document_id).distinct().all()
    for (user_id,) in attachments:
        contributors.add(user_id)
    
    # Get commenters
    comments = db.query(Comment.user_id).filter(Comment.document_id == document_id).distinct().all()
    for (user_id,) in comments:
        contributors.add(user_id)
    
    return contributors


def can_view_feedback(db: Session, feedback: Feedback, current_user: User, contributors: Set[int] = None) -> bool:
    """
    Check if a user can view a specific feedback.
    Rules:
    - Feedback author can always see their own feedback
    - Internal staff who have contributed to the document can see all feedback
    - System admins can see all feedback
    """
    # Feedback author can always see their own
    if feedback.user_id == current_user.id:
        return True
    
    # System admin can see all
    if current_user.role == UserRole.SYSTEM_ADMIN:
        return True
    
    # Internal staff who have contributed to this document can see feedback
    if current_user.role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.EDITOR, UserRole.VIEWER]:
        if contributors is None:
            contributors = get_document_contributors(db, feedback.document_id)
        if current_user.id in contributors:
            return True
    
    return False


# ========== Schemas ==========
class FeedbackDetailResponse(BaseModel):
    """Detailed feedback response for management"""

    id: int
    document_id: int
    document_title: str
    document_number: str
    user_id: int
    user_name: str
    user_email: str
    tenant_id: Optional[int] = None
    tenant_name: Optional[str] = None
    feedback_type: FeedbackType
    status: FeedbackStatus
    content: str
    response: Optional[str] = None
    responded_by: Optional[int] = None
    responder_name: Optional[str] = None
    responded_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackListManagementResponse(BaseModel):
    """Paginated feedback list for management"""

    items: List[FeedbackDetailResponse]
    total: int
    page: int
    per_page: int
    has_more: bool


class FeedbackRespondRequest(BaseModel):
    """Request to respond to feedback"""

    response: str = Field(..., min_length=1, max_length=5000)


class FeedbackStatusUpdate(BaseModel):
    """Request to update feedback status"""

    status: FeedbackStatus


router = APIRouter(prefix="/feedback", tags=["Feedback Management"])


def require_admin_or_manager(current_user: User = Depends(get_current_user)) -> User:
    """Require admin or manager role"""
    if current_user.role not in [UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin or manager access required"
        )
    return current_user


def require_internal_staff(current_user: User = Depends(get_current_user)) -> User:
    """Require internal staff role (not customer)"""
    if current_user.role not in [UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER, UserRole.EDITOR, UserRole.VIEWER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Internal staff access required"
        )
    return current_user


# ========== List All Feedback ==========
@router.get("", response_model=FeedbackListManagementResponse)
async def list_all_feedback(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[FeedbackStatus] = Query(None, alias="status"),
    type_filter: Optional[FeedbackType] = Query(None, alias="type"),
    company_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_internal_staff),
):
    """
    List feedback with contributor-based visibility filtering.
    
    Only shows feedback for documents the current user has contributed to
    (unless user is system admin who can see all).
    """
    # Get all feedback first, then filter by visibility
    query = db.query(Feedback).options(
        joinedload(Feedback.user),
        joinedload(Feedback.document),
        joinedload(Feedback.responder),
    )

    # Apply filters
    if status_filter:
        query = query.filter(Feedback.status == status_filter)

    if type_filter:
        query = query.filter(Feedback.feedback_type == type_filter)

    if company_id:
        query = query.join(Feedback.user).filter(User.tenant_id == company_id)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Feedback.content.ilike(search_term),
                Feedback.user.has(User.full_name.ilike(search_term)),
                Feedback.document.has(Document.title.ilike(search_term)),
            )
        )

    # Order by newest first
    query = query.order_by(Feedback.created_at.desc())

    # Get all matching feedback
    all_feedback = query.all()
    
    # Filter by contributor visibility (unless system admin)
    if current_user.role == UserRole.SYSTEM_ADMIN:
        visible_feedback = all_feedback
    else:
        # Cache contributors per document to avoid repeated queries
        contributors_cache: dict[int, Set[int]] = {}
        visible_feedback = []
        
        for fb in all_feedback:
            if fb.document_id not in contributors_cache:
                contributors_cache[fb.document_id] = get_document_contributors(db, fb.document_id)
            
            if can_view_feedback(db, fb, current_user, contributors_cache[fb.document_id]):
                visible_feedback.append(fb)
    
    # Get total count of visible items
    total = len(visible_feedback)
    
    # Manual pagination on filtered results
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    items = visible_feedback[start_idx:end_idx]

    # Build response
    response_items = []
    for fb in items:
        tenant = (
            db.query(Tenant).filter(Tenant.id == fb.user.tenant_id).first()
            if fb.user.tenant_id
            else None
        )
        response_items.append(
            FeedbackDetailResponse(
                id=fb.id,
                document_id=fb.document_id,
                document_title=fb.document.title if fb.document else "Unknown",
                document_number=fb.document.document_number if fb.document else "",
                user_id=fb.user_id,
                user_name=fb.user.full_name if fb.user else "Unknown",
                user_email=fb.user.email if fb.user else "",
                tenant_id=fb.user.tenant_id if fb.user else None,
                tenant_name=tenant.name if tenant else None,
                feedback_type=fb.feedback_type,
                status=fb.status,
                content=fb.content,
                response=fb.response,
                responded_by=fb.responded_by,
                responder_name=fb.responder.full_name if fb.responder else None,
                responded_at=fb.responded_at,
                created_at=fb.created_at,
            )
        )

    return FeedbackListManagementResponse(
        items=response_items,
        total=total,
        page=page,
        per_page=per_page,
        has_more=(page * per_page) < total,
    )


# ========== Get Feedback Details ==========
@router.get("/{feedback_id}", response_model=FeedbackDetailResponse)
async def get_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_internal_staff),
):
    """
    Get feedback details with contributor-based visibility.
    """
    feedback = (
        db.query(Feedback)
        .options(
            joinedload(Feedback.user),
            joinedload(Feedback.document),
            joinedload(Feedback.responder),
        )
        .filter(Feedback.id == feedback_id)
        .first()
    )

    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    # Check visibility using contributor rules
    if not can_view_feedback(db, feedback, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this feedback"
        )

    tenant = (
        db.query(Tenant).filter(Tenant.id == feedback.user.tenant_id).first()
        if feedback.user.tenant_id
        else None
    )

    return FeedbackDetailResponse(
        id=feedback.id,
        document_id=feedback.document_id,
        document_title=feedback.document.title if feedback.document else "Unknown",
        document_number=feedback.document.document_number if feedback.document else "",
        user_id=feedback.user_id,
        user_name=feedback.user.full_name if feedback.user else "Unknown",
        user_email=feedback.user.email if feedback.user else "",
        tenant_id=feedback.user.tenant_id if feedback.user else None,
        tenant_name=tenant.name if tenant else None,
        feedback_type=feedback.feedback_type,
        status=feedback.status,
        content=feedback.content,
        response=feedback.response,
        responded_by=feedback.responded_by,
        responder_name=feedback.responder.full_name if feedback.responder else None,
        responded_at=feedback.responded_at,
        created_at=feedback.created_at,
    )


# ========== Respond to Feedback ==========
@router.post("/{feedback_id}/respond", response_model=FeedbackDetailResponse)
async def respond_to_feedback(
    feedback_id: int,
    data: FeedbackRespondRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
):
    """
    Respond to customer feedback. Sets status to RESPONDED and notifies customer.
    Only allowed for contributors to the document.
    """
    feedback = (
        db.query(Feedback)
        .options(
            joinedload(Feedback.user),
            joinedload(Feedback.document),
        )
        .filter(Feedback.id == feedback_id)
        .first()
    )

    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    # Check visibility using contributor rules
    if not can_view_feedback(db, feedback, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to respond to this feedback"
        )

    # Update feedback
    feedback.response = data.response
    feedback.responded_by = current_user.id
    feedback.responded_at = datetime.utcnow()
    feedback.status = FeedbackStatus.RESPONDED

    # Create notification for the customer
    notification = Notification(
        user_id=feedback.user_id,
        type=NotificationType.FEEDBACK_RESPONDED,
        title="Your feedback received a response",
        message=f"Your feedback on '{feedback.document.title}' has been responded to",
        link="/portal/feedback",
    )
    db.add(notification)

    db.commit()
    db.refresh(feedback)

    # Reload with responder
    feedback = (
        db.query(Feedback)
        .options(
            joinedload(Feedback.user),
            joinedload(Feedback.document),
            joinedload(Feedback.responder),
        )
        .filter(Feedback.id == feedback.id)
        .first()
    )

    tenant = (
        db.query(Tenant).filter(Tenant.id == feedback.user.tenant_id).first()
        if feedback.user.tenant_id
        else None
    )

    return FeedbackDetailResponse(
        id=feedback.id,
        document_id=feedback.document_id,
        document_title=feedback.document.title if feedback.document else "Unknown",
        document_number=feedback.document.document_number if feedback.document else "",
        user_id=feedback.user_id,
        user_name=feedback.user.full_name if feedback.user else "Unknown",
        user_email=feedback.user.email if feedback.user else "",
        tenant_id=feedback.user.tenant_id if feedback.user else None,
        tenant_name=tenant.name if tenant else None,
        feedback_type=feedback.feedback_type,
        status=feedback.status,
        content=feedback.content,
        response=feedback.response,
        responded_by=feedback.responded_by,
        responder_name=feedback.responder.full_name if feedback.responder else None,
        responded_at=feedback.responded_at,
        created_at=feedback.created_at,
    )


# ========== Update Feedback Status ==========
@router.put("/{feedback_id}/status", response_model=FeedbackDetailResponse)
async def update_feedback_status(
    feedback_id: int,
    data: FeedbackStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_internal_staff),
):
    """
    Update feedback status (e.g., mark as closed).
    Only allowed for contributors to the document.
    """
    feedback = (
        db.query(Feedback)
        .options(
            joinedload(Feedback.user),
            joinedload(Feedback.document),
            joinedload(Feedback.responder),
        )
        .filter(Feedback.id == feedback_id)
        .first()
    )

    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    # Check visibility using contributor rules
    if not can_view_feedback(db, feedback, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this feedback"
        )

    feedback.status = data.status
    db.commit()
    db.refresh(feedback)

    tenant = (
        db.query(Tenant).filter(Tenant.id == feedback.user.tenant_id).first()
        if feedback.user.tenant_id
        else None
    )

    return FeedbackDetailResponse(
        id=feedback.id,
        document_id=feedback.document_id,
        document_title=feedback.document.title if feedback.document else "Unknown",
        document_number=feedback.document.document_number if feedback.document else "",
        user_id=feedback.user_id,
        user_name=feedback.user.full_name if feedback.user else "Unknown",
        user_email=feedback.user.email if feedback.user else "",
        tenant_id=feedback.user.tenant_id if feedback.user else None,
        tenant_name=tenant.name if tenant else None,
        feedback_type=feedback.feedback_type,
        status=feedback.status,
        content=feedback.content,
        response=feedback.response,
        responded_by=feedback.responded_by,
        responder_name=feedback.responder.full_name if feedback.responder else None,
        responded_at=feedback.responded_at,
        created_at=feedback.created_at,
    )


# ========== Get Feedback Statistics ==========
@router.get("/stats/summary")
async def get_feedback_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
):
    """
    Get feedback statistics summary.
    """
    total = db.query(func.count(Feedback.id)).scalar() or 0
    pending = (
        db.query(func.count(Feedback.id)).filter(Feedback.status == FeedbackStatus.PENDING).scalar()
        or 0
    )
    responded = (
        db.query(func.count(Feedback.id))
        .filter(Feedback.status == FeedbackStatus.RESPONDED)
        .scalar()
        or 0
    )
    closed = (
        db.query(func.count(Feedback.id)).filter(Feedback.status == FeedbackStatus.CLOSED).scalar()
        or 0
    )

    # By type
    by_type = {}
    for ft in FeedbackType:
        count = db.query(func.count(Feedback.id)).filter(Feedback.feedback_type == ft).scalar() or 0
        by_type[ft.value] = count

    return {
        "total": total,
        "pending": pending,
        "responded": responded,
        "closed": closed,
        "by_type": by_type,
    }
