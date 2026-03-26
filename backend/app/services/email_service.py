"""Email Service for sending notifications."""

from __future__ import annotations

import asyncio
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.config import settings
from app.notifications import (
    CommentReplyTemplate,
    DocumentPublishedTemplate,
    InvitationTemplate,
    NewCommentTemplate,
    NotificationMessage,
    PasswordResetTemplate,
    WelcomeTemplate,
)

logger = logging.getLogger(__name__)

# Retry config: 3 attempts with exponential backoff (60s, 300s, 900s)
EMAIL_MAX_ATTEMPTS = 3
EMAIL_RETRY_DELAYS = (60, 300, 900)  # seconds: 1m, 5m, 15m


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
        except (aiosmtplib.SMTPConnectError, aiosmtplib.SMTPServerDisconnected,
                aiosmtplib.SMTPResponseException, OSError) as exc:
            # Transient SMTP failures — retry with exponential backoff
            last_error = exc
            for attempt in range(1, EMAIL_MAX_ATTEMPTS):
                delay = EMAIL_RETRY_DELAYS[min(attempt, len(EMAIL_RETRY_DELAYS) - 1)]
                logger.warning(
                    "Email to %s failed (attempt %d/%d), retrying in %ds: %s",
                    to_email, attempt, EMAIL_MAX_ATTEMPTS, delay, exc,
                )
                await asyncio.sleep(delay)
                try:
                    async with aiosmtplib.SMTP(
                        hostname=self.host,
                        port=self.port,
                        use_tls=True,
                    ) as smtp:
                        if self.user and self.password:
                            await smtp.login(self.user, self.password)
                        await smtp.send_message(message)
                    logger.info("Email sent successfully to %s on retry %d: %s", to_email, attempt + 1, subject)
                    return True
                except (aiosmtplib.SMTPConnectError, aiosmtplib.SMTPServerDisconnected,
                        aiosmtplib.SMTPResponseException, OSError) as retry_exc:
                    last_error = retry_exc
                    continue
            logger.error(  # policy: RETRYABLE — exhausted all %d attempts
                "Failed to send email to %s after %d attempts: %s",
                to_email, EMAIL_MAX_ATTEMPTS, last_error,
            )
            return False
        except Exception as exc:  # policy: FAIL_FAST — unexpected error (auth, config)
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

    async def send_invitation(
        self,
        to_email: str,
        accept_url: str,
        inviter_name: str,
        expires_days: int = 7,
        message: str | None = None,
    ) -> bool:
        """Send invitation email to a new user."""
        msg = InvitationTemplate(
            accept_url=accept_url,
            inviter_name=inviter_name,
            expires_days=expires_days,
            message=message,
        ).render(to_email=to_email)
        return await self.send_message(msg)

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

    async def send_email_verification(
        self,
        to_email: str,
        verification_url: str,
        expires_minutes: int = 24 * 60,
    ) -> bool:
        """Send email-verification link."""
        subject = "Verify your email address"
        text_content = (
            "Please verify your email address by opening the following link:\n"
            f"{verification_url}\n\n"
            f"This link expires in {expires_minutes} minutes."
        )
        html_content = (
            "<p>Please verify your email address by opening the link below:</p>"
            f'<p><a href="{verification_url}">{verification_url}</a></p>'
            f"<p>This link expires in {expires_minutes} minutes.</p>"
        )
        return await self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

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
