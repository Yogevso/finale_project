"""Notification dispatcher facade."""

from __future__ import annotations

from collections.abc import Sequence

from app.notifications.channels import NotificationChannel
from app.notifications.message import NotificationMessage
from app.notifications.templates import (
    CommentReplyTemplate,
    DocumentPublishedTemplate,
    NewCommentTemplate,
    NotificationTemplate,
    PasswordResetTemplate,
    WelcomeTemplate,
)


class NotificationDispatcher:
    """Facade that dispatches rendered notifications across channels."""

    def __init__(self, channels: Sequence[NotificationChannel] | None = None):
        self._channels = list(channels or [])

    async def dispatch_message(self, message: NotificationMessage) -> bool:
        if not self._channels:
            return True
        results = []
        for channel in self._channels:
            results.append(await channel.deliver(message))
        return all(results)

    async def dispatch_template(
        self,
        template: NotificationTemplate,
        *,
        to_email: str,
    ) -> bool:
        return await self.dispatch_message(template.render(to_email=to_email))

    async def send_document_published(
        self,
        *,
        to_email: str,
        document_title: str,
        document_number: str,
        document_url: str,
    ) -> bool:
        return await self.dispatch_template(
            DocumentPublishedTemplate(
                document_title=document_title,
                document_number=document_number,
                document_url=document_url,
            ),
            to_email=to_email,
        )

    async def send_new_comment(
        self,
        *,
        to_email: str,
        commenter_name: str,
        document_title: str,
        comment_text: str,
        document_url: str,
    ) -> bool:
        return await self.dispatch_template(
            NewCommentTemplate(
                commenter_name=commenter_name,
                document_title=document_title,
                comment_text=comment_text,
                document_url=document_url,
            ),
            to_email=to_email,
        )

    async def send_comment_reply(
        self,
        *,
        to_email: str,
        replier_name: str,
        document_title: str,
        original_comment: str,
        reply_content: str,
        document_url: str,
    ) -> bool:
        return await self.dispatch_template(
            CommentReplyTemplate(
                replier_name=replier_name,
                document_title=document_title,
                original_comment=original_comment,
                reply_content=reply_content,
                document_url=document_url,
            ),
            to_email=to_email,
        )

    async def send_password_reset(
        self,
        *,
        to_email: str,
        reset_url: str,
        expires_minutes: int = 60,
    ) -> bool:
        return await self.dispatch_template(
            PasswordResetTemplate(
                reset_url=reset_url,
                expires_minutes=expires_minutes,
            ),
            to_email=to_email,
        )

    async def send_welcome(
        self,
        *,
        to_email: str,
        user_name: str,
        login_url: str,
    ) -> bool:
        return await self.dispatch_template(
            WelcomeTemplate(
                user_name=user_name,
                login_url=login_url,
            ),
            to_email=to_email,
        )
