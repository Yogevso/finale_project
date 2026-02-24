"""Comment Service - Business logic for document comments with visibility and threading"""

import logging
from typing import List, Optional, Set

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import Attachment, Comment, Document, User, UserRole, Version
from app.schemas import CommentAuthor, CommentCreate, CommentResponse, CommentUpdate
from app.utils.async_tasks import run_async_task

logger = logging.getLogger(__name__)


class CommentService:
    """Service for managing document comments with visibility controls"""

    @staticmethod
    def is_internal_staff(user: User) -> bool:
        """Check if user is internal staff (not a customer)"""
        return user.role in [
            UserRole.SYSTEM_ADMIN,
            UserRole.ADMIN,
            UserRole.MANAGER,
            UserRole.EDITOR,
            UserRole.VIEWER,
        ]

    @staticmethod
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
        versions = (
            db.query(Version.created_by).filter(Version.document_id == document_id).distinct().all()
        )
        for (user_id,) in versions:
            contributors.add(user_id)

        # Get attachment uploaders
        attachments = (
            db.query(Attachment.uploaded_by)
            .filter(Attachment.document_id == document_id)
            .distinct()
            .all()
        )
        for (user_id,) in attachments:
            contributors.add(user_id)

        # Get commenters (they've also engaged with the document)
        comments = (
            db.query(Comment.user_id).filter(Comment.document_id == document_id).distinct().all()
        )
        for (user_id,) in comments:
            contributors.add(user_id)

        return contributors

    @staticmethod
    def can_view_comment(
        db: Session, comment: Comment, current_user: User, contributors: Set[int] = None
    ) -> bool:
        """
        Check if a user can view a specific comment.
        Rules:
        - Comment author can always see their own comments
        - Internal staff who have contributed to the document can see all comments
        - System admins can see all comments
        """
        # Comment author can always see their own comment
        if comment.user_id == current_user.id:
            return True

        # System admin can see all
        if current_user.role == UserRole.SYSTEM_ADMIN:
            return True

        # Internal staff who have contributed to this document can see comments
        if CommentService.is_internal_staff(current_user):
            if contributors is None:
                contributors = CommentService.get_document_contributors(db, comment.document_id)
            if current_user.id in contributors:
                return True

        return False

    @staticmethod
    def can_view_private_comments(user: User) -> bool:
        """Check if user can view private comments (legacy - kept for compatibility)"""
        return user.role in [
            UserRole.SYSTEM_ADMIN,
            UserRole.ADMIN,
            UserRole.MANAGER,
            UserRole.EDITOR,
        ]

    @staticmethod
    def _to_comment_response(
        comment: Comment,
        *,
        visible_replies: Optional[List[Comment]] = None,
    ) -> CommentResponse:
        """Build a detached response DTO without mutating ORM relationships."""
        replies_source = visible_replies if visible_replies is not None else list(comment.replies or [])
        reply_payload = [
            CommentService._to_comment_response(reply, visible_replies=[])
            for reply in replies_source
        ]
        author_payload = (
            CommentAuthor.model_validate(comment.user) if getattr(comment, "user", None) else None
        )
        return CommentResponse(
            id=comment.id,
            document_id=comment.document_id,
            user_id=comment.user_id,
            parent_id=comment.parent_id,
            content=comment.content,
            is_private=comment.is_private,
            anchor_text=comment.anchor_text,
            anchor_id=comment.anchor_id,
            is_resolved=comment.is_resolved,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            user=author_payload,
            replies=reply_payload,
            reply_count=len(reply_payload),
        )

    @staticmethod
    def get_comments(
        db: Session, document_id: int, current_user: User, include_private: bool = True
    ) -> List[CommentResponse]:
        """
        Get comments for a document with contributor-based visibility filtering.

        Comments are visible to:
        - The comment author
        - Internal staff who have contributed to the document
        - System admins
        """
        # Check document exists
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        # Get all contributors to this document for visibility checks
        contributors = CommentService.get_document_contributors(db, document_id)

        # Base query - get all top-level comments
        all_comments = (
            db.query(Comment)
            .filter(
                Comment.document_id == document_id,
                Comment.parent_id == None,  # noqa: E711
            )
            .options(joinedload(Comment.user), joinedload(Comment.replies).joinedload(Comment.user))
            .order_by(Comment.created_at.desc())
            .all()
        )

        # Filter comments based on visibility rules
        visible_comments = []
        for comment in all_comments:
            if CommentService.can_view_comment(db, comment, current_user, contributors):
                visible_replies = [
                    r
                    for r in comment.replies
                    if CommentService.can_view_comment(db, r, current_user, contributors)
                ]
                visible_comments.append(
                    CommentService._to_comment_response(comment, visible_replies=visible_replies)
                )

        return visible_comments

    @staticmethod
    def get_comment(
        db: Session, document_id: int, comment_id: int, current_user: User
    ) -> CommentResponse:
        """Get a specific comment with its replies"""
        comment = (
            db.query(Comment)
            .filter(Comment.id == comment_id, Comment.document_id == document_id)
            .options(joinedload(Comment.user), joinedload(Comment.replies).joinedload(Comment.user))
            .first()
        )

        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

        # Check visibility using new contributor-based rules
        contributors = CommentService.get_document_contributors(db, document_id)
        if not CommentService.can_view_comment(db, comment, current_user, contributors):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this comment",
            )

        visible_replies = [
            r
            for r in comment.replies
            if CommentService.can_view_comment(db, r, current_user, contributors)
        ]
        return CommentService._to_comment_response(comment, visible_replies=visible_replies)

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

            from app.services.email_service import email_service

            notified_users = set()

            # If this is a reply, notify the parent comment author
            if parent_comment and parent_comment.user_id != current_user.id:
                parent_author = db.query(User).filter(User.id == parent_comment.user_id).first()
                if parent_author and parent_author.email:
                    run_async_task(
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
                    run_async_task(
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
                        run_async_task(
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
        """
        Get comment counts for a document.

        Returns counts of comments visible to the current user based on
        contributor visibility rules.
        """
        if not current_user:
            return {"total": 0, "threads": 0, "private": 0, "unresolved": 0}

        # Get contributors for visibility checks
        contributors = CommentService.get_document_contributors(db, document_id)

        # Get all comments and filter by visibility
        all_comments = db.query(Comment).filter(Comment.document_id == document_id).all()

        visible_comments = [
            c
            for c in all_comments
            if CommentService.can_view_comment(db, c, current_user, contributors)
        ]

        # Calculate counts from visible comments
        total = len(visible_comments)
        top_level = len([c for c in visible_comments if c.parent_id is None])
        private_count = len([c for c in visible_comments if c.is_private])
        unresolved = len([c for c in visible_comments if c.parent_id is None and not c.is_resolved])

        return {
            "total": total,
            "threads": top_level,
            "private": private_count,
            "unresolved": unresolved,
        }
