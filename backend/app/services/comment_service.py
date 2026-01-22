"""Comment Service - Business logic for document comments with visibility and threading"""

import logging
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import Comment, Document, User, UserRole
from app.schemas import CommentCreate, CommentUpdate

logger = logging.getLogger(__name__)


class CommentService:
    """Service for managing document comments with visibility controls"""

    @staticmethod
    def can_view_private_comments(user: User) -> bool:
        """Check if user can view private comments"""
        return user.role in [
            UserRole.SYSTEM_ADMIN,
            UserRole.ADMIN,
            UserRole.MANAGER,
            UserRole.EDITOR,
        ]

    @staticmethod
    def get_comments(
        db: Session, document_id: int, current_user: User, include_private: bool = True
    ) -> List[Comment]:
        """Get comments for a document with visibility filtering"""
        # Check document exists
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        # Base query - get top-level comments only (no parent)
        query = (
            db.query(Comment)
            .filter(
                Comment.document_id == document_id,
                Comment.parent_id == None,  # noqa: E711
            )
            .options(joinedload(Comment.user), joinedload(Comment.replies).joinedload(Comment.user))
        )

        # Filter private comments based on user role
        if not CommentService.can_view_private_comments(current_user):
            # Regular users can only see public comments OR their own private comments
            query = query.filter(
                (Comment.is_private == False)  # noqa: E712
                | (Comment.user_id == current_user.id)
            )

        comments = query.order_by(Comment.created_at.desc()).all()

        # Also filter replies for non-privileged users
        if not CommentService.can_view_private_comments(current_user):
            for comment in comments:
                comment.replies = [
                    r for r in comment.replies if not r.is_private or r.user_id == current_user.id
                ]

        # Add reply count to each comment
        for comment in comments:
            comment.reply_count = len(comment.replies)

        return comments

    @staticmethod
    def get_comment(db: Session, document_id: int, comment_id: int, current_user: User) -> Comment:
        """Get a specific comment with its replies"""
        comment = (
            db.query(Comment)
            .filter(Comment.id == comment_id, Comment.document_id == document_id)
            .options(joinedload(Comment.user), joinedload(Comment.replies).joinedload(Comment.user))
            .first()
        )

        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

        # Check visibility
        if comment.is_private:
            if (
                not CommentService.can_view_private_comments(current_user)
                and comment.user_id != current_user.id
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to view this comment",
                )

        comment.reply_count = len(comment.replies)
        return comment

    @staticmethod
    def create_comment(
        db: Session, document_id: int, comment_data: CommentCreate, current_user: User
    ) -> Comment:
        """Create a new comment with visibility and anchor support"""
        # Check document exists
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        parent_id = comment_data.parent_id

        # If parent_id is provided, verify parent exists
        parent_comment = None
        if parent_id:
            parent_comment = (
                db.query(Comment)
                .filter(Comment.id == parent_id, Comment.document_id == document_id)
                .first()
            )
            if not parent_comment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Parent comment not found"
                )

        # Create comment with new fields
        comment = Comment(
            document_id=document_id,
            user_id=current_user.id,
            content=comment_data.content,
            parent_id=parent_id,
            is_private=comment_data.is_private,
            anchor_text=comment_data.anchor_text,
            anchor_id=comment_data.anchor_id,
        )

        db.add(comment)
        db.commit()
        db.refresh(comment)

        # Load user relationship
        db.refresh(comment, ["user"])

        # Send notifications
        CommentService._send_comment_notifications(
            db, document, comment, current_user, parent_comment
        )

        comment.reply_count = 0
        return comment

    @staticmethod
    def _send_comment_notifications(
        db: Session,
        document: Document,
        comment: Comment,
        current_user: User,
        parent_comment: Optional[Comment] = None,
    ):
        """Send notifications for new comments"""
        try:
            if not settings.EMAIL_ENABLED:
                return

            import asyncio

            from app.services.email_service import email_service

            notified_users = set()

            # If this is a reply, notify the parent comment author
            if parent_comment and parent_comment.user_id != current_user.id:
                parent_author = db.query(User).filter(User.id == parent_comment.user_id).first()
                if parent_author and parent_author.email:
                    asyncio.create_task(
                        email_service.send_comment_reply(
                            to_email=parent_author.email,
                            replier_name=current_user.full_name or current_user.username,
                            document_title=document.title,
                            original_comment=parent_comment.content[:100],
                            reply_content=comment.content[:200],
                            document_url=f"{settings.BASE_URL}/documents/{document.id}?tab=comments&comment={comment.id}",
                        )
                    )
                    notified_users.add(parent_author.id)
                    logger.info(f"Queued reply notification to {parent_author.email}")

            # Notify document author if not already notified
            if (
                document.created_by
                and document.created_by != current_user.id
                and document.created_by not in notified_users
            ):
                author = db.query(User).filter(User.id == document.created_by).first()
                if author and author.email:
                    asyncio.create_task(
                        email_service.send_new_comment(
                            to_email=author.email,
                            commenter_name=current_user.full_name or current_user.username,
                            document_title=document.title,
                            comment_text=comment.content[:200],
                            document_url=f"{settings.BASE_URL}/documents/{document.id}?tab=comments&comment={comment.id}",
                        )
                    )
                    notified_users.add(author.id)
                    logger.info("Queued comment notification to document author")

            # For private comments or inline comments, notify all admins/editors
            if comment.is_private or comment.anchor_text:
                admins = (
                    db.query(User)
                    .filter(
                        User.role.in_(
                            [
                                UserRole.SYSTEM_ADMIN,
                                UserRole.ADMIN,
                                UserRole.MANAGER,
                                UserRole.EDITOR,
                            ]
                        ),
                        User.id != current_user.id,
                        User.id.notin_(notified_users),
                        User.is_active == True,  # noqa: E712
                    )
                    .all()
                )

                for admin in admins:
                    if admin.email:
                        comment_type = "private" if comment.is_private else "inline"
                        asyncio.create_task(
                            email_service.send_new_comment(
                                to_email=admin.email,
                                commenter_name=current_user.full_name or current_user.username,
                                document_title=document.title,
                                comment_text=f"[{comment_type.upper()}] {comment.content[:200]}",
                                document_url=f"{settings.BASE_URL}/documents/{document.id}?tab=comments&comment={comment.id}",
                            )
                        )
                        logger.info(f"Queued {comment_type} comment notification to {admin.email}")

        except Exception as e:
            # Don't fail comment creation if email fails
            logger.warning(f"Failed to send comment notification: {e}")

    @staticmethod
    def update_comment(
        db: Session,
        document_id: int,
        comment_id: int,
        comment_data: CommentUpdate,
        current_user: User,
    ) -> Comment:
        """Update a comment"""
        comment = (
            db.query(Comment)
            .filter(Comment.id == comment_id, Comment.document_id == document_id)
            .options(joinedload(Comment.user))
            .first()
        )

        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

        # Check permissions
        is_admin = current_user.role in [
            UserRole.SYSTEM_ADMIN,
            UserRole.ADMIN,
            UserRole.MANAGER,
            UserRole.EDITOR,
        ]
        is_author = comment.user_id == current_user.id

        # Only author can update content
        if comment_data.content is not None:
            if not is_author and not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the comment author can update the content",
                )
            comment.content = comment_data.content

        # Only admins/editors/managers can resolve comments
        if comment_data.is_resolved is not None:
            if not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only admins, managers and editors can resolve comments",
                )
            comment.is_resolved = comment_data.is_resolved

        db.commit()
        db.refresh(comment)

        comment.reply_count = len(comment.replies) if comment.replies else 0
        return comment

    @staticmethod
    def delete_comment(db: Session, document_id: int, comment_id: int, current_user: User) -> None:
        """Delete a comment and its replies"""
        comment = (
            db.query(Comment)
            .filter(Comment.id == comment_id, Comment.document_id == document_id)
            .first()
        )

        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

        # Only the comment author or admin can delete
        is_admin = current_user.role in [UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER]
        if comment.user_id != current_user.id and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the comment author, admin or manager can delete this comment",
            )

        # Delete replies first
        db.query(Comment).filter(Comment.parent_id == comment_id).delete()
        db.delete(comment)
        db.commit()

    @staticmethod
    def get_comment_count(
        db: Session, document_id: int, current_user: Optional[User] = None
    ) -> dict:
        """Get comment counts for a document"""
        total = db.query(Comment).filter(Comment.document_id == document_id).count()

        # Get top-level comments only
        top_level = (
            db.query(Comment)
            .filter(
                Comment.document_id == document_id,
                Comment.parent_id == None,  # noqa: E711
            )
            .count()
        )

        # Count private comments
        private_count = (
            db.query(Comment)
            .filter(
                Comment.document_id == document_id,
                Comment.is_private == True,  # noqa: E712
            )
            .count()
        )

        # Count unresolved threads
        unresolved = (
            db.query(Comment)
            .filter(
                Comment.document_id == document_id,
                Comment.parent_id == None,  # noqa: E711
                Comment.is_resolved == False,  # noqa: E712
            )
            .count()
        )

        return {
            "total": total,
            "threads": top_level,
            "private": private_count,
            "unresolved": unresolved,
        }
