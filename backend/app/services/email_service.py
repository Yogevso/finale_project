"""Email Service for sending notifications."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Literal

import aiosmtplib

from app.notifications import (
    CommentReplyTemplate,
    DocumentPublishedTemplate,
    InvitationTemplate,
    NewCommentTemplate,
    NotificationMessage,
    PasswordResetTemplate,
    WelcomeTemplate,
)
from app.services.system_email_settings_service import SystemEmailSettingsService

logger = logging.getLogger(__name__)

# Retry config: 3 attempts with exponential backoff (60s, 300s, 900s)
EMAIL_MAX_ATTEMPTS = 3
EMAIL_RETRY_DELAYS = (60, 300, 900)  # seconds: 1m, 5m, 15m

EmailDeliveryState = Literal["sent", "failed", "suppressed"]


@dataclass(frozen=True, slots=True)
class EmailSendResult:
    status: EmailDeliveryState
    attempted_at: datetime
    attempt_count: int
    subject: str
    sender_email: str
    sender_name: str
    error_message: str | None = None
    sent_at: datetime | None = None

    @property
    def ok(self) -> bool:
        return self.status in {"sent", "suppressed"}


class EmailService:
    """SMTP-backed email delivery service with template wrappers."""

    def __init__(self):
        self.enabled = SystemEmailSettingsService.active_runtime_settings().enabled

    @staticmethod
    def _smtp_kwargs(config) -> dict[str, object]:
        kwargs: dict[str, object] = {
            "hostname": config.host,
            "port": config.port,
            "use_tls": config.security == "ssl_tls",
        }
        if config.security == "starttls":
            kwargs["start_tls"] = True
        elif config.security == "none":
            kwargs["start_tls"] = False
        return kwargs

    async def send_email_detailed(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str | None = None,
    ) -> EmailSendResult:
        """Send an email via SMTP and return delivery metadata."""
        config = SystemEmailSettingsService.active_runtime_settings()
        self.enabled = config.enabled
        attempted_at = datetime.utcnow()

        if not config.enabled or not config.host:
            logger.info("[Email] Would send to %s: %s", to_email, subject)
            return EmailSendResult(
                status="suppressed",
                attempted_at=attempted_at,
                attempt_count=0,
                subject=subject,
                sender_email=config.from_email,
                sender_name=config.from_name,
            )

        message = MIMEMultipart("alternative")
        message["From"] = f"{config.from_name} <{config.from_email}>"
        message["To"] = to_email
        message["Subject"] = subject

        if text_content:
            message.attach(MIMEText(text_content, "plain"))
        message.attach(MIMEText(html_content, "html"))

        async def _deliver() -> None:
            async with aiosmtplib.SMTP(**self._smtp_kwargs(config)) as smtp:
                if config.username and config.password:
                    await smtp.login(config.username, config.password)
                await smtp.send_message(message)

        try:
            attempt_count = 1
            await _deliver()
            sent_at = datetime.utcnow()
            logger.info("Email sent successfully to %s: %s", to_email, subject)
            return EmailSendResult(
                status="sent",
                attempted_at=attempted_at,
                attempt_count=attempt_count,
                subject=subject,
                sender_email=config.from_email,
                sender_name=config.from_name,
                sent_at=sent_at,
            )
        except (
            aiosmtplib.SMTPConnectError,
            aiosmtplib.SMTPServerDisconnected,
            aiosmtplib.SMTPResponseException,
            OSError,
        ) as exc:
            last_error = exc
            attempt_count = 1
            for retry_index in range(1, EMAIL_MAX_ATTEMPTS):
                delay = EMAIL_RETRY_DELAYS[min(retry_index - 1, len(EMAIL_RETRY_DELAYS) - 1)]
                logger.warning(
                    "Email to %s failed (attempt %d/%d), retrying in %ds: %s",
                    to_email,
                    retry_index,
                    EMAIL_MAX_ATTEMPTS,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)
                attempt_count += 1
                try:
                    await _deliver()
                    sent_at = datetime.utcnow()
                    logger.info(
                        "Email sent successfully to %s on retry %d: %s",
                        to_email,
                        retry_index + 1,
                        subject,
                    )
                    return EmailSendResult(
                        status="sent",
                        attempted_at=attempted_at,
                        attempt_count=attempt_count,
                        subject=subject,
                        sender_email=config.from_email,
                        sender_name=config.from_name,
                        sent_at=sent_at,
                    )
                except (
                    aiosmtplib.SMTPConnectError,
                    aiosmtplib.SMTPServerDisconnected,
                    aiosmtplib.SMTPResponseException,
                    OSError,
                ) as retry_exc:
                    last_error = retry_exc
                    continue

            logger.error(
                "Failed to send email to %s after %d attempts: %s",
                to_email,
                EMAIL_MAX_ATTEMPTS,
                last_error,
            )
            return EmailSendResult(
                status="failed",
                attempted_at=attempted_at,
                attempt_count=attempt_count,
                subject=subject,
                sender_email=config.from_email,
                sender_name=config.from_name,
                error_message=str(last_error),
            )
        except Exception as exc:  # policy: BOUNDARY — email failures surfaced as result
            logger.error("Failed to send email to %s: %s", to_email, exc)
            return EmailSendResult(
                status="failed",
                attempted_at=attempted_at,
                attempt_count=1,
                subject=subject,
                sender_email=config.from_email,
                sender_name=config.from_name,
                error_message=str(exc),
            )

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str | None = None,
    ) -> bool:
        """Send an email via SMTP."""
        result = await self.send_email_detailed(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )
        return result.ok

    async def send_message_detailed(self, message: NotificationMessage) -> EmailSendResult:
        """Send a pre-rendered notification message and return delivery metadata."""
        return await self.send_email_detailed(
            to_email=message.to_email,
            subject=message.subject,
            html_content=message.html_content,
            text_content=message.text_content,
        )

    async def send_message(self, message: NotificationMessage) -> bool:
        """Send a pre-rendered notification message."""
        return (await self.send_message_detailed(message)).ok

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

    def render_invitation_message(
        self,
        *,
        to_email: str,
        accept_url: str,
        inviter_name: str,
        expires_days: int = 7,
        message: str | None = None,
    ) -> NotificationMessage:
        return InvitationTemplate(
            accept_url=accept_url,
            inviter_name=inviter_name,
            expires_days=expires_days,
            message=message,
        ).render(to_email=to_email)

    async def send_invitation_detailed(
        self,
        to_email: str,
        accept_url: str,
        inviter_name: str,
        expires_days: int = 7,
        message: str | None = None,
    ) -> EmailSendResult:
        """Send invitation email to a new user and return delivery metadata."""
        notification = self.render_invitation_message(
            to_email=to_email,
            accept_url=accept_url,
            inviter_name=inviter_name,
            expires_days=expires_days,
            message=message,
        )
        return await self.send_message_detailed(notification)

    async def send_invitation(
        self,
        to_email: str,
        accept_url: str,
        inviter_name: str,
        expires_days: int = 7,
        message: str | None = None,
    ) -> bool:
        """Send invitation email to a new user."""
        return (
            await self.send_invitation_detailed(
                to_email=to_email,
                accept_url=accept_url,
                inviter_name=inviter_name,
                expires_days=expires_days,
                message=message,
            )
        ).ok

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
