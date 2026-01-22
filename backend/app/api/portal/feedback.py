"""
Portal Feedback API - Customer feedback submission and tracking
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    Document,
    DocumentStatus,
    DocumentVisibility,
    Feedback,
    FeedbackStatus,
    User,
    UserRole,
)
from app.schemas.portal import (
    FeedbackCreate,
    FeedbackListResponse,
    FeedbackResponse,
)
from app.security import get_current_active_user

router = APIRouter(prefix="/portal", tags=["Customer Feedback"])


def require_customer(current_user: User = Depends(get_current_active_user)) -> User:
    """Dependency to ensure user is a customer"""
    if current_user.role != UserRole.CUSTOMER:
        raise HTTPException(status_code=403, detail="This endpoint is only for customer users.")
    return current_user


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    feedback_data: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """
    Submit feedback on a document.
    Customer must have access to the document.
    """
    # Verify document exists and customer has access
    document = (
        db.query(Document)
        .filter(
            Document.id == feedback_data.document_id,
        )
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check document is published
    if document.status not in [DocumentStatus.PUBLISHED, DocumentStatus.ACTIVE]:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check visibility
    if document.visibility == DocumentVisibility.INTERNAL:
        raise HTTPException(status_code=403, detail="You don't have access to this document")

    if document.visibility == DocumentVisibility.COMPANY:
        # Check if document is assigned to customer's company
        company_ids = [c.id for c in document.assigned_companies]
        if current_user.tenant_id not in company_ids:
            raise HTTPException(status_code=403, detail="You don't have access to this document")

    # Create feedback
    feedback = Feedback(
        document_id=feedback_data.document_id,
        user_id=current_user.id,
        feedback_type=feedback_data.feedback_type,
        content=feedback_data.content,
        status=FeedbackStatus.PENDING,
    )

    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    return FeedbackResponse(
        id=feedback.id,
        document_id=feedback.document_id,
        document_title=document.title,
        feedback_type=feedback.feedback_type,
        content=feedback.content,
        status=feedback.status,
        response=None,
        responded_at=None,
        responded_by_name=None,
        created_at=feedback.created_at,
        updated_at=None,  # Feedback model doesn't have updated_at
    )


@router.get("/feedback", response_model=FeedbackListResponse)
async def list_my_feedback(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[FeedbackStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """
    List all feedback submitted by the current customer.
    """
    query = db.query(Feedback).filter(Feedback.user_id == current_user.id)

    if status:
        query = query.filter(Feedback.status == status)

    # Get total
    total = query.count()
    pages = (total + per_page - 1) // per_page
    offset = (page - 1) * per_page

    # Get feedback with documents
    feedback_list = query.order_by(Feedback.created_at.desc()).offset(offset).limit(per_page).all()

    items = []
    for fb in feedback_list:
        # Get document title
        document = db.query(Document).filter(Document.id == fb.document_id).first()
        document_title = document.title if document else "Unknown Document"

        # Get responder name if responded
        responder_name = None
        if fb.responded_by:
            responder = db.query(User).filter(User.id == fb.responded_by).first()
            responder_name = responder.full_name if responder else None

        items.append(
            FeedbackResponse(
                id=fb.id,
                document_id=fb.document_id,
                document_title=document_title,
                feedback_type=fb.feedback_type,
                content=fb.content,
                status=fb.status,
                response=fb.response,
                responded_at=fb.responded_at,
                responded_by_name=responder_name,
                created_at=fb.created_at,
                updated_at=None,  # Feedback model doesn't have updated_at
            )
        )

    return FeedbackListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/feedback/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback_detail(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """
    Get details of a specific feedback submission.
    Customer can only view their own feedback.
    """
    feedback = (
        db.query(Feedback)
        .filter(
            Feedback.id == feedback_id,
            Feedback.user_id == current_user.id,
        )
        .first()
    )

    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    # Get document title
    document = db.query(Document).filter(Document.id == feedback.document_id).first()
    document_title = document.title if document else "Unknown Document"

    # Get responder name
    responder_name = None
    if feedback.responded_by:
        responder = db.query(User).filter(User.id == feedback.responded_by).first()
        responder_name = responder.full_name if responder else None

    return FeedbackResponse(
        id=feedback.id,
        document_id=feedback.document_id,
        document_title=document_title,
        feedback_type=feedback.feedback_type,
        content=feedback.content,
        status=feedback.status,
        response=feedback.response,
        responded_at=feedback.responded_at,
        responded_by_name=responder_name,
        created_at=feedback.created_at,
        updated_at=None,  # Feedback model doesn't have updated_at
    )
