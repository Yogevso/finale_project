"""Comment Service - Business logic for document comments with visibility and threading"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Set

from sqlalchemy.orm import Session

from app.config import settings
from app.domain.events import (
    CommentChatBridgeRequested,
    CommentCreated,
    InProcessDomainEventDispatcher,
)
from app.errors import NotFoundError, PermissionDeniedError, ValidationError
from app.models import Attachment, Comment, Document, NotificationType, User, UserRole
from app.repositories import (
    CommentRepository,
    DocumentRepository,
    VersionRepository,
)
from app.schemas import CommentAuthor, CommentCreate, CommentResponse, CommentUpdate
from app.services.base_service import SessionService
from app.services.chat_service import ChatService
from app.services.notification_service import NotificationService
from app.services.outbox import build_outbox_event_dispatcher


@dataclass
class PaginatedComments:
    """Paginated wrapper for comments list."""

    items: List[CommentResponse]
    total: int
    page: int
    page_size: int
    pages: int


from app.services.uow import UnitOfWork  # noqa: E402

logger = logging.getLogger(__name__)


class CommentService(SessionService):
    """Service for managing document comments with visibility controls"""

    MAX_REPLY_DEPTH = 2

    def __init__(
        self,
        db: Session,
        *,
        chat_db: Session | None = None,
        event_dispatcher: InProcessDomainEventDispatcher | None = None,
    ):
        super().__init__(db)
        self.document_repository = DocumentRepository(db)
        self.comment_repository = CommentRepository(db)
        self.version_repository = VersionRepository(db)
        self.notification_service = NotificationService(db, chat_db=chat_db)
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
        - System admins can see all comments
        - Private comments (is_private=True) are only visible to author,
          system admins, and internal staff with an elevated role
          (admin / manager / editor)
        - Non-private comments are visible to internal staff who have
          contributed to the document
        """
        # Comment author can always see their own comment
        if comment.user_id == current_user.id:
            return True

        # System admin can see all
        if current_user.role == UserRole.SYSTEM_ADMIN:
            return True

        # AD-005: enforce private-comment visibility
        if comment.is_private:
            return current_user.role in [
                UserRole.ADMIN,
                UserRole.MANAGER,
                UserRole.EDITOR,
            ]

        # Internal staff who have contributed to this document can see non-private comments
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
    def _comment_depth(comment: Comment | None, *, max_depth: int = 100) -> int:
        depth = 0
        current = comment
        seen: set[int] = set()
        while current and current.parent_id is not None:
            if depth >= max_depth or current.id in seen:
                break
            seen.add(current.id)
            depth += 1
            current = current.parent
        return depth

    def _delete_descendant_comments(self, root_comment_id: int) -> None:
        pending_parent_ids = [root_comment_id]
        descendant_ids: list[int] = []

        while pending_parent_ids:
            child_rows = (
                self.db.query(Comment.id).filter(Comment.parent_id.in_(pending_parent_ids)).all()
            )
            pending_parent_ids = [row[0] for row in child_rows]
            descendant_ids.extend(pending_parent_ids)

        if descendant_ids:
            self.db.query(Comment).filter(Comment.id.in_(descendant_ids)).delete(
                synchronize_session=False
            )

    def get_comments(
        self, document_id: int, current_user: User, *, page: int = 1, page_size: int = 50
    ) -> PaginatedComments:
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
            raise NotFoundError("Document not found")

        # Y15-016: Tenant isolation - non-system-admins can only see comments on their tenant's documents
        if current_user.role != UserRole.SYSTEM_ADMIN:
            if document.tenant_id != current_user.tenant_id:
                raise NotFoundError("Document not found")

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

        total = len(visible_comments)
        pages = max(1, (total + page_size - 1) // page_size)
        start = (page - 1) * page_size
        end = start + page_size

        return PaginatedComments(
            items=visible_comments[start:end],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    def get_comment(self, document_id: int, comment_id: int, current_user: User) -> CommentResponse:
        """Get a specific comment with its replies"""
        # Y15-016: Verify document exists and user has tenant access
        document = self.document_repository.get_by_id(document_id)
        if not document:
            raise NotFoundError("Document not found")

        # Tenant isolation: non-system-admins can only access comments on their tenant's documents
        if current_user.role != UserRole.SYSTEM_ADMIN:
            if document.tenant_id != current_user.tenant_id:
                raise NotFoundError("Document not found")

        comment = self.comment_repository.get_by_id_for_document(
            comment_id,
            document_id,
            include_replies=True,
        )

        if not comment:
            raise NotFoundError("Comment not found")

        # Check visibility using new contributor-based rules
        contributors = CommentService.get_document_contributors(self.db, document_id)
        if not CommentService.can_view_comment(self.db, comment, current_user, contributors):
            raise PermissionDeniedError("You don't have permission to view this comment")

        return CommentService._to_comment_response(comment, self.db, current_user, contributors)

    def create_comment(
        self, document_id: int, comment_data: CommentCreate, current_user: User
    ) -> Comment:
        """Create a new comment with visibility and anchor support"""
        # Check document exists
        document = self.document_repository.get_by_id(document_id)
        if not document:
            raise NotFoundError("Document not found")

        # Y15-016: Tenant isolation - non-system-admins can only create comments on their tenant's documents
        if current_user.role != UserRole.SYSTEM_ADMIN:
            if document.tenant_id != current_user.tenant_id:
                raise NotFoundError("Document not found")

        parent_id = comment_data.parent_id

        # If parent_id is provided, verify parent exists
        # Y15-018: Use row-level locking to prevent race conditions when adding concurrent replies
        parent_comment = None
        if parent_id:
            parent_comment = self.comment_repository.get_by_id_for_update(parent_id, document_id)
            if not parent_comment:
                raise NotFoundError("Parent comment not found")
            if self._comment_depth(parent_comment) >= self.MAX_REPLY_DEPTH:
                raise ValidationError("Replies are limited to two nested levels")

        # Create comment with new fields
        # AD-005: customers cannot create private comments
        is_private = comment_data.is_private
        if current_user.role == UserRole.CUSTOMER:
            is_private = False

        comment = Comment(
            document_id=document_id,
            user_id=current_user.id,
            content=comment_data.content,
            parent_id=parent_id,
            is_private=is_private,
            anchor_text=comment_data.anchor_text,
            anchor_id=comment_data.anchor_id,
        )
        commenter_name = current_user.full_name or current_user.username
        truncated_content = " ".join(comment.content.split())[:160]

        with UnitOfWork(self.db) as uow:
            self.db.add(comment)
            uow.flush()
            self._publish_comment_side_effect_events(
                document,
                comment,
                current_user,
                parent_comment,
            )
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
            watcher_message = (
                f"{document.title}: {truncated_content}" if truncated_content else document.title
            )
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
        comment.chat_id = None

        return comment

    def _bridge_comment_to_chat(
        self,
        document: Document,
        comment: Comment,
        current_user: User,
    ) -> Optional[int]:
        """Find-or-create a direct chat between the commenter and the document
        author, then send an automatic message with context about the comment.

        Returns the chat ID or None if bridging is not applicable (e.g. the
        commenter IS the document author, or the author is in another tenant).
        """
        try:
            # Skip if commenter is the document author
            if current_user.id == document.created_by:
                return None

            # Load the document author
            doc_author = self.db.query(User).filter(User.id == document.created_by).first()
            if not doc_author:
                return None

            # Skip cross-tenant (chat service enforces this too)
            if not current_user.tenant_id or current_user.tenant_id != doc_author.tenant_id:
                return None

            chat_svc = ChatService(self.db)

            # create_direct_chat deduplicates — returns existing if found
            chat = chat_svc.create_direct_chat(current_user, doc_author.id)

            # Build a contextual auto-message
            anchor_snippet = ""
            if comment.anchor_text:
                snippet = comment.anchor_text[:120]
                if len(comment.anchor_text) > 120:
                    snippet += "…"
                anchor_snippet = f'\n📌 On: "{snippet}"'

            # Build the link — when anchor text exists, encode it so the
            # document preview can scroll to and highlight the passage.
            from urllib.parse import quote

            if comment.anchor_text:
                encoded_anchor = quote(comment.anchor_text[:120], safe="")
                view_link = f"/documents/{document.id}?highlight={encoded_anchor}"
            else:
                view_link = f"/documents/{document.id}"

            content = (
                f"💬 Comment on **{document.title}**{anchor_snippet}\n\n"
                f"{comment.content}\n\n"
                f"[View in document]({view_link})"
            )

            chat_svc.send_message(chat.id, current_user, content)
            return chat.id
        except Exception:  # policy: LOSSY — chat bridge failure must not block comment creation
            # Chat bridging is best-effort — never block comment creation
            logger.debug("Chat bridging failed for comment", exc_info=True)
            return None

    def _publish_comment_side_effect_events(
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
        self.event_dispatcher.dispatch(
            CommentChatBridgeRequested(
                document_id=document.id,
                comment_id=comment.id,
                document_author_id=document.created_by,
                commenter_user_id=current_user.id,
                commenter_display_name=current_user.full_name or current_user.username,
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
        # Y15-016: Verify document exists and user has tenant access
        document = self.document_repository.get_by_id(document_id)
        if not document:
            raise NotFoundError("Document not found")

        # Tenant isolation: non-system-admins can only update comments on their tenant's documents
        if current_user.role != UserRole.SYSTEM_ADMIN:
            if document.tenant_id != current_user.tenant_id:
                raise NotFoundError("Document not found")

        comment = self.comment_repository.get_by_id_for_document(
            comment_id,
            document_id,
            include_replies=True,
        )

        if not comment:
            raise NotFoundError("Comment not found")

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
                    raise PermissionDeniedError("Only the comment author can update the content")
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
                    raise PermissionDeniedError(
                        "Only admins, managers and editors can resolve comments"
                    )
                comment.is_resolved = comment_data.is_resolved

        self.db.refresh(comment)

        comment.reply_count = len(comment.replies) if comment.replies else 0
        return comment

    def delete_comment(self, document_id: int, comment_id: int, current_user: User) -> None:
        """Delete a comment and its replies"""
        # Y15-016: Verify document exists and user has tenant access
        document = self.document_repository.get_by_id(document_id)
        if not document:
            raise NotFoundError("Document not found")

        # Tenant isolation: non-system-admins can only delete comments on their tenant's documents
        if current_user.role != UserRole.SYSTEM_ADMIN:
            if document.tenant_id != current_user.tenant_id:
                raise NotFoundError("Document not found")

        comment = self.comment_repository.get_by_id_for_document(comment_id, document_id)

        if not comment:
            raise NotFoundError("Comment not found")

        # Only the comment author or admin can delete
        is_admin = current_user.role in [UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER]
        if comment.user_id != current_user.id and not is_admin:
            raise PermissionDeniedError(
                "Only the comment author, admin or manager can delete this comment"
            )

        with UnitOfWork(self.db):
            self._delete_descendant_comments(comment_id)
            self.db.delete(comment)

    def get_comment_count(self, document_id: int, current_user: Optional[User] = None) -> dict:
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
