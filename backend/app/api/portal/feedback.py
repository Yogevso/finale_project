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
    if document.status != DocumentStatus.ACTIVE:
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
        total_pages=pages,
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


# ---------------------------------------------------------------------------
# AH-010/011: Customer chat routing — customers can discuss documents
# with internal users via the portal.
# ---------------------------------------------------------------------------


@router.get("/documents/{document_id}/chat")
async def get_or_create_document_chat(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """AH-011: Get or create a chat thread for a document.

    Customers can chat with internal users related to the document they
    are viewing.  If no chat exists, one is created with the document author.
    """
    from app.models import Chat, ChatParticipant, ChatParticipantRole, ChatType, ChatMessageType, ChatMessage

    document = db.query(Document).filter(Document.id == document_id).first()
    if not document or document.status != DocumentStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="Document not found")

    # Find existing document chat the customer participates in
    existing = (
        db.query(Chat)
        .join(ChatParticipant, Chat.id == ChatParticipant.chat_id)
        .filter(
            Chat.document_id == document_id,
            ChatParticipant.user_id == current_user.id,
        )
        .first()
    )
    if existing:
        return {"chat_id": existing.id, "name": existing.name, "created": False}

    # Create a new chat with the document author
    chat = Chat(
        type=ChatType.GROUP,
        name=f"Chat: {document.title[:100]}",
        document_id=document_id,
        created_by=current_user.id,
        tenant_id=current_user.tenant_id,
    )
    db.add(chat)
    db.flush()

    # Add customer as owner
    db.add(ChatParticipant(chat_id=chat.id, user_id=current_user.id, role=ChatParticipantRole.OWNER))
    # Add document author as member
    if document.created_by and document.created_by != current_user.id:
        db.add(ChatParticipant(chat_id=chat.id, user_id=document.created_by, role=ChatParticipantRole.MEMBER))

    db.add(ChatMessage(
        chat_id=chat.id,
        sender_id=current_user.id,
        content=f"Customer started a conversation about \"{document.title}\"",
        message_type=ChatMessageType.SYSTEM,
    ))

    db.commit()
    db.refresh(chat)
    return {"chat_id": chat.id, "name": chat.name, "created": True}


@router.get("/chats/{chat_id}/messages")
async def list_chat_messages(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """Return messages for a chat the customer participates in."""
    from app.models import Chat, ChatParticipant, ChatMessage

    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    is_participant = (
        db.query(ChatParticipant)
        .filter(ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == current_user.id)
        .first()
    )
    if not is_participant:
        raise HTTPException(status_code=403, detail="Not a participant")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.chat_id == chat_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [
        {
            "id": m.id,
            "sender_id": m.sender_id,
            "content": m.content,
            "message_type": m.message_type.value if m.message_type else "user",
            "context_json": m.context_json,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]


@router.post("/chats/{chat_id}/messages")
async def send_chat_message(
    chat_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """Customer sends a message in a document chat."""
    from app.models import Chat, ChatParticipant, ChatMessage, ChatMessageType

    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    is_participant = (
        db.query(ChatParticipant)
        .filter(ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == current_user.id)
        .first()
    )
    if not is_participant:
        raise HTTPException(status_code=403, detail="Not a participant")

    content = (body.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=422, detail="Content required")

    msg = ChatMessage(
        chat_id=chat_id,
        sender_id=current_user.id,
        content=content,
        message_type=ChatMessageType.USER,
        context_json=body.get("context_json"),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {
        "id": msg.id,
        "sender_id": msg.sender_id,
        "content": msg.content,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }


@router.post("/feedback/{feedback_id}/chat")
async def create_chat_from_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """AH-010: Convert a feedback thread into a live chat.

    If the feedback already has a linked chat, returns it. Otherwise creates
    a new document-scoped chat with the feedback content as the first message.
    """
    from app.models import Chat, ChatParticipant, ChatParticipantRole, ChatType, ChatMessageType, ChatMessage

    feedback = db.query(Feedback).filter(
        Feedback.id == feedback_id,
        Feedback.user_id == current_user.id,
    ).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    # Check if a document chat already exists for this customer + document
    existing = (
        db.query(Chat)
        .join(ChatParticipant, Chat.id == ChatParticipant.chat_id)
        .filter(
            Chat.document_id == feedback.document_id,
            ChatParticipant.user_id == current_user.id,
        )
        .first()
    )
    if existing:
        return {"chat_id": existing.id, "name": existing.name, "created": False}

    document = db.query(Document).filter(Document.id == feedback.document_id).first()
    doc_title = document.title if document else "Unknown"

    chat = Chat(
        type=ChatType.GROUP,
        name=f"Feedback: {doc_title[:100]}",
        document_id=feedback.document_id,
        created_by=current_user.id,
        tenant_id=current_user.tenant_id,
    )
    db.add(chat)
    db.flush()

    db.add(ChatParticipant(chat_id=chat.id, user_id=current_user.id, role=ChatParticipantRole.OWNER))
    if feedback.responded_by and feedback.responded_by != current_user.id:
        db.add(ChatParticipant(chat_id=chat.id, user_id=feedback.responded_by, role=ChatParticipantRole.MEMBER))
    elif document and document.created_by and document.created_by != current_user.id:
        db.add(ChatParticipant(chat_id=chat.id, user_id=document.created_by, role=ChatParticipantRole.MEMBER))

    # Seed chat with original feedback content
    db.add(ChatMessage(
        chat_id=chat.id,
        sender_id=current_user.id,
        content=feedback.content,
        message_type=ChatMessageType.USER,
    ))
    # If there was a response, add it too
    if feedback.response:
        db.add(ChatMessage(
            chat_id=chat.id,
            sender_id=feedback.responded_by,
            content=feedback.response,
            message_type=ChatMessageType.USER,
        ))

    db.commit()
    db.refresh(chat)
    return {"chat_id": chat.id, "name": chat.name, "created": True}
