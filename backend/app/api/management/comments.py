"""Comments API Routes"""

from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.schemas import (
    CommentCreate,
    CommentResponse,
    CommentUpdate,
    MessageResponse,
)
from app.security import get_current_active_user
from app.services.comment_service import CommentService

router = APIRouter()


@router.get("/documents/{document_id}/comments", response_model=List[CommentResponse])
def list_comments(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    List comments for a document.

    Returns top-level comments with their replies.
    Private comments are only visible to admins/editors or the comment author.
    """
    return CommentService.get_comments(db, document_id, current_user)


@router.get("/documents/{document_id}/comments/stats")
def get_comment_stats(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get comment statistics for a document.
    """
    return CommentService.get_comment_count(db, document_id, current_user)


@router.get("/documents/{document_id}/comments/{comment_id}", response_model=CommentResponse)
def get_comment(
    document_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a specific comment with its replies.
    """
    return CommentService.get_comment(db, document_id, comment_id, current_user)


@router.post(
    "/documents/{document_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    document_id: int,
    comment_data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new comment.

    - Use `parent_id` in the request body to create a reply
    - Use `is_private` to make a private comment (only visible to admins/editors)
    - Use `anchor_text` and `anchor_id` for inline comments on specific content
    """
    return CommentService.create_comment(db, document_id, comment_data, current_user)


@router.patch("/documents/{document_id}/comments/{comment_id}", response_model=CommentResponse)
def update_comment(
    document_id: int,
    comment_id: int,
    comment_data: CommentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update a comment.

    - Only the comment author can update content
    - Only admins/editors can resolve comments
    """
    return CommentService.update_comment(db, document_id, comment_id, comment_data, current_user)


@router.post(
    "/documents/{document_id}/comments/{comment_id}/resolve", response_model=CommentResponse
)
def resolve_comment(
    document_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Mark a comment thread as resolved.
    Only admins and editors can resolve comments.
    """
    return CommentService.update_comment(
        db, document_id, comment_id, CommentUpdate(is_resolved=True), current_user
    )


@router.delete("/documents/{document_id}/comments/{comment_id}", response_model=MessageResponse)
def delete_comment(
    document_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a comment and its replies.

    Only the comment author or admin can delete.
    """
    CommentService.delete_comment(db, document_id, comment_id, current_user)
    return MessageResponse(message="Comment deleted successfully")
