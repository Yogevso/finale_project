"""Email Service for sending notifications"""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import aiosmtplib

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email notifications"""

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
        text_content: Optional[str] = None,
    ) -> bool:
        """Send an email via SMTP"""
        if not self.enabled or not self.host:
            logger.info(f"[Email] Would send to {to_email}: {subject}")
            return True  # Skip in dev mode

        message = MIMEMultipart("alternative")
        message["From"] = f"{self.from_name} <{self.from_email}>"
        message["To"] = to_email
        message["Subject"] = subject

        # Add text version if provided
        if text_content:
            text_part = MIMEText(text_content, "plain")
            message.attach(text_part)

        # Add HTML version
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)

        try:
            async with aiosmtplib.SMTP(
                hostname=self.host,
                port=self.port,
                use_tls=True,
            ) as smtp:
                if self.user and self.password:
                    await smtp.login(self.user, self.password)
                await smtp.send_message(message)

            logger.info(f"Email sent successfully to {to_email}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    async def send_document_published(
        self,
        to_email: str,
        document_title: str,
        document_number: str,
        document_url: str,
    ) -> bool:
        """Notify when a document is published"""
        subject = f"📄 Document Published: {document_title}"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; }}
                .header {{ background: linear-gradient(135deg, #3B82F6, #1D4ED8); color: white; padding: 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 30px; background: #f9fafb; }}
                .document-card {{ background: white; border-radius: 8px; padding: 20px; margin: 20px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
                .document-title {{ font-size: 18px; font-weight: 600; color: #1f2937; margin-bottom: 8px; }}
                .document-number {{ font-size: 14px; color: #6b7280; }}
                .button {{ display: inline-block; padding: 12px 28px; background: #3B82F6; color: white; text-decoration: none; border-radius: 6px; font-weight: 600; }}
                .button:hover {{ background: #2563EB; }}
                .footer {{ padding: 20px; text-align: center; color: #9ca3af; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📄 Document Published</h1>
                </div>
                <div class="content">
                    <p>Great news! A document has been published and is now available for viewing.</p>

                    <div class="document-card">
                        <div class="document-title">{document_title}</div>
                        <div class="document-number">{document_number}</div>
                    </div>

                    <p style="text-align: center; margin: 30px 0;">
                        <a href="{document_url}" class="button">View Document →</a>
                    </p>
                </div>
                <div class="footer">
                    <p>Document Portal V2 • This is an automated notification</p>
                </div>
            </div>
        </body>
        </html>
        """

        text = f"""
Document Published: {document_title}

A document has been published and is now available.

Title: {document_title}
Number: {document_number}

View the document: {document_url}

---
Document Portal V2
        """

        return await self.send_email(to_email, subject, html, text)

    async def send_new_comment(
        self,
        to_email: str,
        commenter_name: str,
        document_title: str,
        comment_text: str,
        document_url: str,
    ) -> bool:
        """Notify when someone comments on a document"""
        subject = f"💬 New Comment on: {document_title}"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; }}
                .header {{ background: linear-gradient(135deg, #10B981, #059669); color: white; padding: 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 30px; background: #f9fafb; }}
                .comment-card {{ background: white; border-left: 4px solid #10B981; padding: 20px; margin: 20px 0; border-radius: 0 8px 8px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
                .commenter {{ font-weight: 600; color: #059669; margin-bottom: 8px; }}
                .comment-text {{ color: #374151; }}
                .document-name {{ font-size: 14px; color: #6b7280; margin-top: 12px; }}
                .button {{ display: inline-block; padding: 12px 28px; background: #10B981; color: white; text-decoration: none; border-radius: 6px; font-weight: 600; }}
                .footer {{ padding: 20px; text-align: center; color: #9ca3af; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>💬 New Comment</h1>
                </div>
                <div class="content">
                    <p>Someone left a comment on a document you're following.</p>

                    <div class="comment-card">
                        <div class="commenter">{commenter_name} wrote:</div>
                        <div class="comment-text">"{comment_text}"</div>
                        <div class="document-name">on {document_title}</div>
                    </div>

                    <p style="text-align: center; margin: 30px 0;">
                        <a href="{document_url}" class="button">View Document →</a>
                    </p>
                </div>
                <div class="footer">
                    <p>Document Portal V2 • This is an automated notification</p>
                </div>
            </div>
        </body>
        </html>
        """

        text = f"""
New Comment on: {document_title}

{commenter_name} wrote:
"{comment_text}"

View the document: {document_url}

---
Document Portal V2
        """

        return await self.send_email(to_email, subject, html, text)

    async def send_comment_reply(
        self,
        to_email: str,
        replier_name: str,
        document_title: str,
        original_comment: str,
        reply_content: str,
        document_url: str,
    ) -> bool:
        """Notify when someone replies to your comment"""
        subject = f"↩️ Reply to your comment on: {document_title}"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; }}
                .header {{ background: linear-gradient(135deg, #8B5CF6, #7C3AED); color: white; padding: 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 30px; background: #f9fafb; }}
                .original-comment {{ background: #f3f4f6; border-left: 3px solid #9ca3af; padding: 15px; margin: 15px 0; border-radius: 0 8px 8px 0; color: #6b7280; font-style: italic; }}
                .reply-card {{ background: white; border-left: 4px solid #8B5CF6; padding: 20px; margin: 20px 0; border-radius: 0 8px 8px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
                .replier {{ font-weight: 600; color: #7C3AED; margin-bottom: 8px; }}
                .reply-text {{ color: #374151; }}
                .document-name {{ font-size: 14px; color: #6b7280; margin-top: 12px; }}
                .button {{ display: inline-block; padding: 12px 28px; background: #8B5CF6; color: white; text-decoration: none; border-radius: 6px; font-weight: 600; }}
                .footer {{ padding: 20px; text-align: center; color: #9ca3af; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>↩️ New Reply</h1>
                </div>
                <div class="content">
                    <p>Someone replied to your comment!</p>

                    <div class="original-comment">
                        <strong>Your comment:</strong><br>
                        "{original_comment}..."
                    </div>

                    <div class="reply-card">
                        <div class="replier">{replier_name} replied:</div>
                        <div class="reply-text">"{reply_content}"</div>
                        <div class="document-name">on {document_title}</div>
                    </div>

                    <p style="text-align: center; margin: 30px 0;">
                        <a href="{document_url}" class="button">View Conversation →</a>
                    </p>
                </div>
                <div class="footer">
                    <p>Document Portal V2 • This is an automated notification</p>
                </div>
            </div>
        </body>
        </html>
        """

        text = f"""
Reply to your comment on: {document_title}

Your comment:
"{original_comment}..."

{replier_name} replied:
"{reply_content}"

View the conversation: {document_url}

---
Document Portal V2
        """

        return await self.send_email(to_email, subject, html, text)

    async def send_password_reset(
        self,
        to_email: str,
        reset_url: str,
        expires_minutes: int = 60,
    ) -> bool:
        """Send password reset link"""
        subject = "🔐 Password Reset Request"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; }}
                .header {{ background: linear-gradient(135deg, #EF4444, #DC2626); color: white; padding: 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 30px; background: #f9fafb; }}
                .button {{ display: inline-block; padding: 12px 28px; background: #EF4444; color: white; text-decoration: none; border-radius: 6px; font-weight: 600; }}
                .warning {{ background: #FEF3C7; border: 1px solid #F59E0B; padding: 15px; border-radius: 6px; margin: 20px 0; }}
                .footer {{ padding: 20px; text-align: center; color: #9ca3af; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Password Reset</h1>
                </div>
                <div class="content">
                    <p>You requested to reset your password. Click the button below to set a new password.</p>

                    <p style="text-align: center; margin: 30px 0;">
                        <a href="{reset_url}" class="button">Reset Password →</a>
                    </p>

                    <div class="warning">
                        <strong>⚠️ This link expires in {expires_minutes} minutes.</strong><br>
                        If you didn't request this, please ignore this email.
                    </div>
                </div>
                <div class="footer">
                    <p>Document Portal V2 • This is an automated notification</p>
                </div>
            </div>
        </body>
        </html>
        """

        text = f"""
Password Reset Request

You requested to reset your password. Click the link below:

{reset_url}

This link expires in {expires_minutes} minutes.

If you didn't request this, please ignore this email.

---
Document Portal V2
        """

        return await self.send_email(to_email, subject, html, text)

    async def send_welcome(
        self,
        to_email: str,
        user_name: str,
        login_url: str,
    ) -> bool:
        """Send welcome email to new users"""
        subject = "🎉 Welcome to Document Portal!"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; }}
                .header {{ background: linear-gradient(135deg, #8B5CF6, #7C3AED); color: white; padding: 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 30px; background: #f9fafb; }}
                .button {{ display: inline-block; padding: 12px 28px; background: #8B5CF6; color: white; text-decoration: none; border-radius: 6px; font-weight: 600; }}
                .features {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .feature {{ padding: 10px 0; border-bottom: 1px solid #f3f4f6; }}
                .feature:last-child {{ border-bottom: none; }}
                .footer {{ padding: 20px; text-align: center; color: #9ca3af; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Welcome!</h1>
                </div>
                <div class="content">
                    <p>Hi {user_name},</p>
                    <p>Welcome to Document Portal! Your account has been created successfully.</p>

                    <div class="features">
                        <div class="feature">📄 Browse and search documents</div>
                        <div class="feature">💬 Leave comments and feedback</div>
                        <div class="feature">📌 Bookmark your favorites</div>
                        <div class="feature">📊 Track your reading progress</div>
                    </div>

                    <p style="text-align: center; margin: 30px 0;">
                        <a href="{login_url}" class="button">Get Started →</a>
                    </p>
                </div>
                <div class="footer">
                    <p>Document Portal V2 • This is an automated notification</p>
                </div>
            </div>
        </body>
        </html>
        """

        text = f"""
Welcome to Document Portal!

Hi {user_name},

Your account has been created successfully.

With Document Portal you can:
- Browse and search documents
- Leave comments and feedback
- Bookmark your favorites
- Track your reading progress

Get started: {login_url}

---
Document Portal V2
        """

        return await self.send_email(to_email, subject, html, text)


# Singleton instance
email_service = EmailService()
