"""Domain event handlers for notification/email side effects."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.domain.events import (
    CommentCreated,
    CompanyAssignmentsUpdated,
    DocumentPublished,
    InProcessDomainEventDispatcher,
)
from app.models import UserRole
from app.notifications import (
    NotificationDispatcher,
)
from app.plugins.notifications import get_notification_channel_plugin_registry
from app.repositories import UserRepository
from app.utils.async_tasks import run_async_task

logger = logging.getLogger(__name__)


class NotificationEmailEventHandlers:
    """Notification/email side effects for write-path domain events."""

    def __init__(
        self,
        db: Session,
        notification_dispatcher: NotificationDispatcher | None = None,
    ):
        self.user_repository = UserRepository(db)
        if notification_dispatcher is not None:
            self.notification_dispatcher = notification_dispatcher
        else:
            channel_registry = get_notification_channel_plugin_registry()
            self.notification_dispatcher = NotificationDispatcher(
                channels=channel_registry.build_channels()
            )

    @staticmethod
    def _should_send_notifications() -> bool:
        return settings.EMAIL_ENABLED

    def handle_document_published(self, event: DocumentPublished) -> None:
        if (
            not self._should_send_notifications()
            or not event.document_author_id
            or event.document_author_id == event.published_by_user_id
        ):
            return

        author = self.user_repository.get_by_id(event.document_author_id)
        if not author or not author.email:
            return

        run_async_task(
            self.notification_dispatcher.send_document_published(
                to_email=author.email,
                document_title=event.document_title,
                document_number=event.document_number,
                document_url=event.document_url,
            )
        )
        logger.info("Queued publish notification for document %s", event.document_id)

    def handle_comment_created(self, event: CommentCreated) -> None:
        if not self._should_send_notifications():
            return

        notified_users: set[int] = set()

        self._notify_parent_comment_author(event, notified_users)
        self._notify_document_author(event, notified_users)
        self._notify_admin_reviewers_if_needed(event, notified_users)

    def _notify_parent_comment_author(
        self,
        event: CommentCreated,
        notified_users: set[int],
    ) -> None:
        parent_author_id = event.parent_comment_author_id
        if not parent_author_id or parent_author_id == event.commenter_user_id:
            return

        parent_author = self.user_repository.get_by_id(parent_author_id)
        if not parent_author or not parent_author.email:
            return

        run_async_task(
            self.notification_dispatcher.send_comment_reply(
                to_email=parent_author.email,
                replier_name=event.commenter_display_name,
                document_title=event.document_title,
                original_comment=event.comment_content[:100],
                reply_content=event.comment_content[:200],
                document_url=event.document_url,
            )
        )
        notified_users.add(parent_author_id)
        logger.info("Queued reply notification to %s", parent_author.email)

    def _notify_document_author(
        self,
        event: CommentCreated,
        notified_users: set[int],
    ) -> None:
        author_id = event.document_author_id
        if (
            not author_id
            or author_id == event.commenter_user_id
            or author_id in notified_users
        ):
            return

        author = self.user_repository.get_by_id(author_id)
        if not author or not author.email:
            return

        run_async_task(
            self.notification_dispatcher.send_new_comment(
                to_email=author.email,
                commenter_name=event.commenter_display_name,
                document_title=event.document_title,
                comment_text=event.comment_content[:200],
                document_url=event.document_url,
            )
        )
        notified_users.add(author_id)
        logger.info("Queued comment notification to document author")

    def _notify_admin_reviewers_if_needed(
        self,
        event: CommentCreated,
        notified_users: set[int],
    ) -> None:
        if not (event.is_private or event.has_anchor):
            return

        admins = self.user_repository.list_active_by_roles(
            [
                UserRole.SYSTEM_ADMIN,
                UserRole.ADMIN,
                UserRole.MANAGER,
                UserRole.EDITOR,
            ],
            exclude_user_id=event.commenter_user_id,
            exclude_user_ids=notified_users,
        )

        comment_type = "private" if event.is_private else "inline"
        for admin in admins:
            if not admin.email:
                continue
            run_async_task(
                self.notification_dispatcher.send_new_comment(
                    to_email=admin.email,
                    commenter_name=event.commenter_display_name,
                    document_title=event.document_title,
                    comment_text=f"[{comment_type.upper()}] {event.comment_content[:200]}",
                    document_url=event.document_url,
                )
            )
            logger.info(
                "Queued %s comment notification to %s",
                comment_type,
                admin.email,
            )

    def handle_company_assignments_updated(self, event: CompanyAssignmentsUpdated) -> None:
        logger.info(
            "Processed company assignment update event for document=%s row_version=%s companies=%s",
            event.document_id,
            event.document_row_version,
            list(event.assigned_company_ids),
        )


def build_domain_event_dispatcher(
    db: Session,
    *,
    suppress_handler_exceptions: bool = True,
) -> InProcessDomainEventDispatcher:
    """Create a dispatcher with default in-process handlers."""

    dispatcher = InProcessDomainEventDispatcher(
        suppress_handler_exceptions=suppress_handler_exceptions
    )
    handlers = NotificationEmailEventHandlers(db)
    dispatcher.register(DocumentPublished, handlers.handle_document_published)
    dispatcher.register(CommentCreated, handlers.handle_comment_created)
    dispatcher.register(CompanyAssignmentsUpdated, handlers.handle_company_assignments_updated)
    return dispatcher
