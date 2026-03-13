"""Comment Service - Business logic for document comments with visibility and threading"""

from typing import List, Optional, Set

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.domain.events import CommentCreated, InProcessDomainEventDispatcher
from app.models import Attachment, Comment, Document, NotificationType, User, UserRole
from app.repositories import (
    CommentRepository,
    DocumentRepository,
    VersionRepository,
)
from app.schemas import CommentAuthor, CommentCreate, CommentResponse, CommentUpdate
from app.services.base_service import SessionService
from app.services.notification_service import NotificationService
from app.services.outbox import build_outbox_event_dispatcher
from app.services.uow import UnitOfWork


class CommentService(SessionService):
    """Service for managing document comments with visibility controls"""

    MAX_REPLY_DEPTH = 2

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
        self.notification_service = NotificationService(db)
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
        db: Session,
        current_user: User,
        contributors: Set[int],
    ) -> CommentResponse:
        """Build a detached response DTO without mutating ORM relationships."""
        reply_payload: list[CommentResponse] = []
        for reply in list(comment.replies or []):
            if CommentService.can_view_comment(db, reply, current_user, contributors):
                reply_payload.append(
                    CommentService._to_comment_response(
                        reply,
                        db,
                        current_user,
                        contributors,
                    )
                )
        author_payload = (
            CommentAuthor.model_validate(comment.user) if getattr(comment, "user", None) else None
        )
        total_reply_count = sum(1 + reply.reply_count for reply in reply_payload)
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
            reply_count=total_reply_count,
        )

    @staticmethod
    def _comment_depth(comment: Comment | None) -> int:
        depth = 0
        current = comment
        while current and current.parent_id is not None:
            depth += 1
            current = current.parent
        return depth

    def _delete_descendant_comments(self, root_comment_id: int) -> None:
        pending_parent_ids = [root_comment_id]
        descendant_ids: list[int] = []

        while pending_parent_ids:
            child_rows = (
                self.db.query(Comment.id)
                .filter(Comment.parent_id.in_(pending_parent_ids))
                .all()
            )
            pending_parent_ids = [row[0] for row in child_rows]
            descendant_ids.extend(pending_parent_ids)

        if descendant_ids:
            self.db.query(Comment).filter(Comment.id.in_(descendant_ids)).delete(
                synchronize_session=False
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
                visible_comments.append(
                    CommentService._to_comment_response(
                        comment,
                        self.db,
                        current_user,
                        contributors,
                    )
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

        return CommentService._to_comment_response(comment, self.db, current_user, contributors)

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
                self.comment_repository.get_by_id_for_document(
                    parent_id,
                    document_id,
                    include_replies=True,
                )
            )
            if not parent_comment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Parent comment not found"
                )
            if self._comment_depth(parent_comment) >= self.MAX_REPLY_DEPTH:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Replies are limited to two nested levels",
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
        commenter_name = current_user.full_name or current_user.username
        truncated_content = " ".join(comment.content.split())[:160]

        with UnitOfWork(self.db) as uow:
            self.db.add(comment)
            uow.flush()
            self._publish_comment_created_event(document, comment, current_user, parent_comment)
            comment_link = f"/documents/{document.id}?tab=comments&comment={comment.id}"
            mention_type = (
                NotificationType.COMMENT_REPLY if parent_comment else NotificationType.COMMENT_ADDED
            )
            mentioned_user_ids = self.notification_service.notify_mentions(
                content=comment.content,
                actor_user=current_user,
                document=document,
                notification_type=mention_type,
                title_builder=lambda _user: f"{commenter_name} mentioned you in a comment",
                message_builder=lambda _user: truncated_content,
                link=comment_link,
            )
            watcher_title = (
                f"{commenter_name} replied on a document you follow"
                if parent_comment
                else f"{commenter_name} commented on a document you follow"
            )
            watcher_message = f"{document.title}: {truncated_content}" if truncated_content else document.title
            self.notification_service.notify_document_watchers(
                document=document,
                actor_user=current_user,
                notification_type=mention_type,
                title=watcher_title,
                message=watcher_message,
                link=comment_link,
                exclude_user_ids=mentioned_user_ids,
            )

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
                self.notification_service.notify_mentions(
                    content=comment.content,
                    actor_user=current_user,
                    document=comment.document,
                    notification_type=NotificationType.COMMENT_ADDED,
                    title_builder=lambda _user: f"{current_user.full_name or current_user.username} mentioned you in a comment",
                    message_builder=lambda _user: " ".join(comment.content.split())[:160],
                    link=f"/documents/{document_id}?tab=comments&comment={comment.id}",
                )

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
            self._delete_descendant_comments(comment_id)
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
