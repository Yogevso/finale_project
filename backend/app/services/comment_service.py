"""Comment Service - Business logic for document comments with visibility and threading"""

from typing import List, Optional, Set

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.domain.events import CommentCreated, InProcessDomainEventDispatcher
from app.models import Attachment, Comment, Document, User, UserRole
from app.repositories import (
    CommentRepository,
    DocumentRepository,
    VersionRepository,
)
from app.schemas import CommentAuthor, CommentCreate, CommentResponse, CommentUpdate
from app.services.base_service import SessionService
from app.services.outbox import build_outbox_event_dispatcher
from app.services.uow import UnitOfWork


class CommentService(SessionService):
    """Service for managing document comments with visibility controls"""

    def __init__(
        self,
        db: Session,
        *,
        event_dispatcher: InProcessDomainEventDispatcher | None = None,
    ):
        super().__init__(db)
        self.document_repository = DocumentRepository(db)
        self.comment_repository = CommentRepository(db)
        self.version_repository = VersionRepository(db)
        self.event_dispatcher = event_dispatcher or build_outbox_event_dispatcher(db)

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
        document = DocumentRepository(db).get_by_id(document_id)
        if document:
            contributors.add(document.created_by)

        # Get version creators
        versions = VersionRepository(db).list_for_document(document_id)
        for version in versions:
            contributors.add(version.created_by)

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
        comments = CommentRepository(db).list_distinct_user_ids_for_document(document_id)
        for user_id in comments:
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

    def get_comments(self, document_id: int, current_user: User) -> List[CommentResponse]:
        """
        Get comments for a document with contributor-based visibility filtering.

        Comments are visible to:
        - The comment author
        - Internal staff who have contributed to the document
        - System admins
        """
        # Check document exists
        document = self.document_repository.get_by_id(document_id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        # Get all contributors to this document for visibility checks
        contributors = CommentService.get_document_contributors(self.db, document_id)

        # Base query - get all top-level comments
        all_comments = self.comment_repository.list_top_level_with_replies(document_id)

        # Filter comments based on visibility rules
        visible_comments = []
        for comment in all_comments:
            if CommentService.can_view_comment(self.db, comment, current_user, contributors):
                visible_replies = [
                    r
                    for r in comment.replies
                    if CommentService.can_view_comment(self.db, r, current_user, contributors)
                ]
                visible_comments.append(
                    CommentService._to_comment_response(comment, visible_replies=visible_replies)
                )

        return visible_comments

    def get_comment(
        self, document_id: int, comment_id: int, current_user: User
    ) -> CommentResponse:
        """Get a specific comment with its replies"""
        comment = self.comment_repository.get_by_id_for_document(
            comment_id,
            document_id,
            include_replies=True,
        )

        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

        # Check visibility using new contributor-based rules
        contributors = CommentService.get_document_contributors(self.db, document_id)
        if not CommentService.can_view_comment(self.db, comment, current_user, contributors):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this comment",
            )

        visible_replies = [
            r
            for r in comment.replies
            if CommentService.can_view_comment(self.db, r, current_user, contributors)
        ]
        return CommentService._to_comment_response(comment, visible_replies=visible_replies)

    def create_comment(
        self, document_id: int, comment_data: CommentCreate, current_user: User
    ) -> Comment:
        """Create a new comment with visibility and anchor support"""
        # Check document exists
        document = self.document_repository.get_by_id(document_id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        parent_id = comment_data.parent_id

        # If parent_id is provided, verify parent exists
        parent_comment = None
        if parent_id:
            parent_comment = (
                self.comment_repository.get_by_id_for_document(parent_id, document_id)
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

        with UnitOfWork(self.db) as uow:
            self.db.add(comment)
            uow.flush()
            self._publish_comment_created_event(document, comment, current_user, parent_comment)

        self.db.refresh(comment)

        # Load user relationship
        self.db.refresh(comment, ["user"])

        comment.reply_count = 0
        return comment

    def _publish_comment_created_event(
        self,
        document: Document,
        comment: Comment,
        current_user: User,
        parent_comment: Optional[Comment] = None,
    ) -> None:
        self.event_dispatcher.dispatch(
            CommentCreated(
                document_id=document.id,
                document_title=document.title,
                document_url=f"{settings.BASE_URL}/documents/{document.id}?tab=comments&comment={comment.id}",
                document_author_id=document.created_by,
                comment_id=comment.id,
                comment_content=comment.content,
                commenter_user_id=current_user.id,
                commenter_display_name=current_user.full_name or current_user.username,
                parent_comment_author_id=parent_comment.user_id if parent_comment else None,
                is_private=comment.is_private,
                has_anchor=bool(comment.anchor_text),
            )
        )

    def update_comment(
        self,
        document_id: int,
        comment_id: int,
        comment_data: CommentUpdate,
        current_user: User,
    ) -> Comment:
        """Update a comment"""
        comment = self.comment_repository.get_by_id_for_document(
            comment_id,
            document_id,
            include_replies=True,
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
        with UnitOfWork(self.db):
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

        self.db.refresh(comment)

        comment.reply_count = len(comment.replies) if comment.replies else 0
        return comment

    def delete_comment(self, document_id: int, comment_id: int, current_user: User) -> None:
        """Delete a comment and its replies"""
        comment = self.comment_repository.get_by_id_for_document(comment_id, document_id)

        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

        # Only the comment author or admin can delete
        is_admin = current_user.role in [UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER]
        if comment.user_id != current_user.id and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the comment author, admin or manager can delete this comment",
            )

        with UnitOfWork(self.db):
            # Delete replies first
            self.comment_repository.delete_replies_for_parent(comment_id)
            self.db.delete(comment)

    def get_comment_count(
        self, document_id: int, current_user: Optional[User] = None
    ) -> dict:
        """
        Get comment counts for a document.

        Returns counts of comments visible to the current user based on
        contributor visibility rules.
        """
        if not current_user:
            return {"total": 0, "threads": 0, "private": 0, "unresolved": 0}

        # Get contributors for visibility checks
        contributors = CommentService.get_document_contributors(self.db, document_id)

        # Get all comments and filter by visibility
        all_comments = self.comment_repository.list_for_document(document_id)

        visible_comments = [
            c
            for c in all_comments
            if CommentService.can_view_comment(self.db, c, current_user, contributors)
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
