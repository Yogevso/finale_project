"""Notification template objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.notifications.message import NotificationMessage
from app.utils import escape_html, sanitize_plain_text


class NotificationTemplate(Protocol):
    """Template contract that renders a delivery message."""

    def render(self, *, to_email: str) -> NotificationMessage:
        """Render a notification message for the recipient."""


def _render_base_html(title: str, body_html: str) -> str:
    return (
        "<!DOCTYPE html>"
        "<html><head><meta charset='UTF-8'></head><body>"
        "<div style='font-family:Segoe UI,Arial,sans-serif;line-height:1.5;color:#1f2937;'>"
        f"<h2>{title}</h2>"
        f"{body_html}"
        "<p style='color:#6b7280;font-size:12px;'>Documentation Platform - automated notification</p>"
        "</div></body></html>"
    )


@dataclass(frozen=True, slots=True)
class DocumentPublishedTemplate:
    """Template for document publish notifications."""

    document_title: str
    document_number: str
    document_url: str

    def render(self, *, to_email: str) -> NotificationMessage:
        body_html = (
            "<p>A document has been published and is now available.</p>"
            f"<p><strong>Title:</strong> {self.document_title}<br>"
            f"<strong>Number:</strong> {self.document_number}</p>"
            f"<p><a href='{self.document_url}'>View document</a></p>"
        )
        text = (
            f"Document Published: {self.document_title}\n\n"
            "A document has been published and is now available.\n\n"
            f"Title: {self.document_title}\n"
            f"Number: {self.document_number}\n"
            f"View document: {self.document_url}\n"
        )
        return NotificationMessage(
            to_email=to_email,
            subject=f"Document Published: {self.document_title}",
            html_content=_render_base_html("Document Published", body_html),
            text_content=text,
        )


@dataclass(frozen=True, slots=True)
class NewCommentTemplate:
    """Template for new comment notifications."""

    commenter_name: str
    document_title: str
    comment_text: str
    document_url: str

    def render(self, *, to_email: str) -> NotificationMessage:
        body_html = (
            "<p>A new comment was posted on a document you follow.</p>"
            f"<p><strong>{self.commenter_name}</strong> wrote:</p>"
            f"<blockquote>{self.comment_text}</blockquote>"
            f"<p>on <strong>{self.document_title}</strong></p>"
            f"<p><a href='{self.document_url}'>View discussion</a></p>"
        )
        text = (
            f"New Comment on: {self.document_title}\n\n"
            f"{self.commenter_name} wrote:\n"
            f"{self.comment_text}\n\n"
            f"View discussion: {self.document_url}\n"
        )
        return NotificationMessage(
            to_email=to_email,
            subject=f"New Comment on: {self.document_title}",
            html_content=_render_base_html("New Comment", body_html),
            text_content=text,
        )


@dataclass(frozen=True, slots=True)
class CommentReplyTemplate:
    """Template for comment reply notifications."""

    replier_name: str
    document_title: str
    original_comment: str
    reply_content: str
    document_url: str

    def render(self, *, to_email: str) -> NotificationMessage:
        body_html = (
            "<p>Someone replied to your comment.</p>"
            f"<p><strong>Your comment:</strong> {self.original_comment}</p>"
            f"<p><strong>{self.replier_name}</strong> replied:</p>"
            f"<blockquote>{self.reply_content}</blockquote>"
            f"<p>on <strong>{self.document_title}</strong></p>"
            f"<p><a href='{self.document_url}'>View conversation</a></p>"
        )
        text = (
            f"Reply to your comment on: {self.document_title}\n\n"
            f"Your comment: {self.original_comment}\n\n"
            f"{self.replier_name} replied:\n"
            f"{self.reply_content}\n\n"
            f"View conversation: {self.document_url}\n"
        )
        return NotificationMessage(
            to_email=to_email,
            subject=f"Reply to your comment on: {self.document_title}",
            html_content=_render_base_html("Comment Reply", body_html),
            text_content=text,
        )


@dataclass(frozen=True, slots=True)
class PasswordResetTemplate:
    """Template for password reset notifications."""

    reset_url: str
    expires_minutes: int = 60

    def render(self, *, to_email: str) -> NotificationMessage:
        body_html = (
            "<p>You requested a password reset.</p>"
            f"<p><a href='{self.reset_url}'>Reset password</a></p>"
            f"<p>This link expires in {self.expires_minutes} minutes.</p>"
        )
        text = (
            "Password Reset Request\n\n"
            f"Reset password: {self.reset_url}\n"
            f"This link expires in {self.expires_minutes} minutes.\n"
        )
        return NotificationMessage(
            to_email=to_email,
            subject="Password Reset Request",
            html_content=_render_base_html("Password Reset", body_html),
            text_content=text,
        )


@dataclass(frozen=True, slots=True)
class InvitationTemplate:
    """Template for user invitation notifications."""

    accept_url: str
    inviter_name: str
    expires_days: int = 7
    message: str | None = None

    def render(self, *, to_email: str) -> NotificationMessage:
        inviter_name = sanitize_plain_text(self.inviter_name) or "Someone"
        invitation_message = sanitize_plain_text(self.message)
        safe_inviter_name = escape_html(inviter_name)
        safe_accept_url = escape_html(self.accept_url)
        message_html = (
            f"<p>&ldquo;{escape_html(invitation_message)}&rdquo;</p>" if invitation_message else ""
        )
        body_html = (
            f"<p>{safe_inviter_name} has invited you to join Documentation Platform.</p>"
            f"{message_html}"
            f"<p><a href='{safe_accept_url}'>Accept Invitation</a></p>"
            f"<p>This invitation expires in {self.expires_days} days.</p>"
        )
        message_text = f'"{invitation_message}"\n\n' if invitation_message else ""
        text = (
            f"{inviter_name} has invited you to join Documentation Platform.\n\n"
            f"{message_text}"
            f"Accept invitation: {self.accept_url}\n"
            f"This invitation expires in {self.expires_days} days.\n"
        )
        return NotificationMessage(
            to_email=to_email,
            subject=f"{inviter_name} invited you to Documentation Platform",
            html_content=_render_base_html("You're Invited", body_html),
            text_content=text,
        )


@dataclass(frozen=True, slots=True)
class WelcomeTemplate:
    """Template for welcome notifications."""

    user_name: str
    login_url: str

    def render(self, *, to_email: str) -> NotificationMessage:
        body_html = (
            f"<p>Hi {self.user_name},</p>"
            "<p>Welcome to Documentation Platform.</p>"
            f"<p><a href='{self.login_url}'>Get started</a></p>"
        )
        text = (
            "Welcome to Documentation Platform\n\n"
            f"Hi {self.user_name},\n"
            "Your account is ready.\n"
            f"Get started: {self.login_url}\n"
        )
        return NotificationMessage(
            to_email=to_email,
            subject="Welcome to Documentation Platform!",
            html_content=_render_base_html("Welcome", body_html),
            text_content=text,
        )
