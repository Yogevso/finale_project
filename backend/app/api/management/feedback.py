"""
Feedback Management API - Admin/Manager endpoints for managing customer feedback
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models import (
    Document,
    Feedback,
    FeedbackStatus,
    FeedbackType,
    Notification,
    NotificationType,
    Tenant,
    User,
    UserRole,
)
from app.security import get_current_user


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
    current_user: User = Depends(require_admin_or_manager),
):
    """
    List all feedback with filters (admin/manager only).
    """
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

    # Get total count
    total = query.count()

    # Paginate
    items = query.offset((page - 1) * per_page).limit(per_page).all()

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
    current_user: User = Depends(require_admin_or_manager),
):
    """
    Get feedback details (admin/manager only).
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
    current_user: User = Depends(require_admin_or_manager),
):
    """
    Update feedback status (e.g., mark as closed).
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
