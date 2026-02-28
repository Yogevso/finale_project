"""Email Service for sending notifications."""

from __future__ import annotations

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.config import settings
from app.notifications import (
    CommentReplyTemplate,
    DocumentPublishedTemplate,
    NewCommentTemplate,
    NotificationMessage,
    PasswordResetTemplate,
    WelcomeTemplate,
)

logger = logging.getLogger(__name__)


class EmailService:
    """SMTP-backed email delivery service with template wrappers."""

    def __init__(self):
        self.enabled = settings.EMAIL_ENABLED
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.EMAIL_FROM
        self.from_name = settings.EMAIL_FROM_NAME

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str | None = None,
    ) -> bool:
        """Send an email via SMTP."""
        if not self.enabled or not self.host:
            logger.info("[Email] Would send to %s: %s", to_email, subject)
            return True

        message = MIMEMultipart("alternative")
        message["From"] = f"{self.from_name} <{self.from_email}>"
        message["To"] = to_email
        message["Subject"] = subject

        if text_content:
            message.attach(MIMEText(text_content, "plain"))
        message.attach(MIMEText(html_content, "html"))

        try:
            async with aiosmtplib.SMTP(
                hostname=self.host,
                port=self.port,
                use_tls=True,
            ) as smtp:
                if self.user and self.password:
                    await smtp.login(self.user, self.password)
                await smtp.send_message(message)

            logger.info("Email sent successfully to %s: %s", to_email, subject)
            return True
        except Exception as exc:
            logger.error("Failed to send email to %s: %s", to_email, exc)
            return False

    async def send_message(self, message: NotificationMessage) -> bool:
        """Send a pre-rendered notification message."""
        return await self.send_email(
            to_email=message.to_email,
            subject=message.subject,
            html_content=message.html_content,
            text_content=message.text_content,
        )

    async def send_document_published(
        self,
        to_email: str,
        document_title: str,
        document_number: str,
        document_url: str,
    ) -> bool:
        """Notify when a document is published."""
        message = DocumentPublishedTemplate(
            document_title=document_title,
            document_number=document_number,
            document_url=document_url,
        ).render(to_email=to_email)
        return await self.send_message(message)

    async def send_new_comment(
        self,
        to_email: str,
        commenter_name: str,
        document_title: str,
        comment_text: str,
        document_url: str,
    ) -> bool:
        """Notify when someone comments on a document."""
        message = NewCommentTemplate(
            commenter_name=commenter_name,
            document_title=document_title,
            comment_text=comment_text,
            document_url=document_url,
        ).render(to_email=to_email)
        return await self.send_message(message)

    async def send_comment_reply(
        self,
        to_email: str,
        replier_name: str,
        document_title: str,
        original_comment: str,
        reply_content: str,
        document_url: str,
    ) -> bool:
        """Notify when someone replies to a comment."""
        message = CommentReplyTemplate(
            replier_name=replier_name,
            document_title=document_title,
            original_comment=original_comment,
            reply_content=reply_content,
            document_url=document_url,
        ).render(to_email=to_email)
        return await self.send_message(message)

    async def send_password_reset(
        self,
        to_email: str,
        reset_url: str,
        expires_minutes: int = 60,
    ) -> bool:
        """Send password reset link."""
        message = PasswordResetTemplate(
            reset_url=reset_url,
            expires_minutes=expires_minutes,
        ).render(to_email=to_email)
        return await self.send_message(message)

    async def send_welcome(
        self,
        to_email: str,
        user_name: str,
        login_url: str,
    ) -> bool:
        """Send welcome email to new users."""
        message = WelcomeTemplate(
            user_name=user_name,
            login_url=login_url,
        ).render(to_email=to_email)
        return await self.send_message(message)


# Singleton instance
email_service = EmailService()
