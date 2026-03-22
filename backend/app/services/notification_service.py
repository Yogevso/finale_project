"""Helpers for in-app notifications such as mentions and document follows."""

from __future__ import annotations

import re
from typing import Callable

from sqlalchemy.orm import Session

from app.models import Document, DocumentWatcher, Notification, NotificationType, User, UserRole
from app.repositories import UserRepository
from app.services.base_service import SessionService

MENTION_PATTERN = re.compile(r"(?<![\w@])@([A-Za-z0-9][A-Za-z0-9._-]{1,99})")
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


class NotificationService(SessionService):
    """Create in-app notifications tied to collaboration and document activity."""

    def __init__(self, db: Session, chat_db: Session | None = None):
        super().__init__(db)
        self.chat_db = chat_db or db
        self.user_repository = UserRepository(db)

    @staticmethod
    def extract_mentions(raw_content: str | None) -> list[str]:
        if not raw_content:
            return []

        plain_text = HTML_TAG_PATTERN.sub(" ", raw_content)
        mentions = [match.group(1) for match in MENTION_PATTERN.finditer(plain_text)]
        return list(dict.fromkeys(mentions))

    def create_notification(
        self,
        *,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str | None = None,
        link: str | None = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            link=link,
        )
        self.chat_db.add(notification)
        return notification

    def notify_mentions(
        self,
        *,
        content: str | None,
        actor_user: User,
        document: Document,
        notification_type: NotificationType,
        title_builder: Callable[[User], str],
        message_builder: Callable[[User], str],
        link: str,
    ) -> set[int]:
        usernames = self.extract_mentions(content)
        mentioned_users = self.user_repository.list_active_by_usernames(
            usernames,
            tenant_id=document.tenant_id,
            exclude_user_id=actor_user.id,
        )

        notified_user_ids: set[int] = set()
        for mentioned_user in mentioned_users:
            self.create_notification(
                user_id=mentioned_user.id,
                notification_type=notification_type,
                title=title_builder(mentioned_user),
                message=message_builder(mentioned_user),
                link=link,
            )
            notified_user_ids.add(mentioned_user.id)

        return notified_user_ids

    def notify_document_watchers(
        self,
        *,
        document: Document,
        actor_user: User,
        notification_type: NotificationType,
        title: str,
        message: str | None,
        link: str,
        exclude_user_ids: set[int] | None = None,
    ) -> set[int]:
        excluded_user_ids = set(exclude_user_ids or set())
        excluded_user_ids.add(actor_user.id)

        watchers = (
            self.db.query(DocumentWatcher)
            .filter(DocumentWatcher.document_id == document.id)
            .all()
        )

        notified_user_ids: set[int] = set()
        for watcher in watchers:
            if watcher.user_id in excluded_user_ids:
                continue
            self.create_notification(
                user_id=watcher.user_id,
                notification_type=notification_type,
                title=title,
                message=message,
                link=link,
            )
            notified_user_ids.add(watcher.user_id)

        return notified_user_ids

    def list_active_users_by_roles(
        self,
        *,
        roles: list[UserRole],
        tenant_id: int | None = None,
        exclude_user_ids: set[int] | None = None,
    ) -> list[User]:
        return self.user_repository.list_active_by_roles(
            roles,
            tenant_id=tenant_id,
            exclude_user_ids=exclude_user_ids,
        )
