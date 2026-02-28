"""Notification templates, channels, and dispatcher facade."""

from app.notifications.channels import EmailNotificationChannel, NotificationChannel
from app.notifications.dispatcher import NotificationDispatcher
from app.notifications.message import NotificationMessage
from app.notifications.templates import (
    CommentReplyTemplate,
    DocumentPublishedTemplate,
    NewCommentTemplate,
    NotificationTemplate,
    PasswordResetTemplate,
    WelcomeTemplate,
)

__all__ = [
    "CommentReplyTemplate",
    "DocumentPublishedTemplate",
    "EmailNotificationChannel",
    "NewCommentTemplate",
    "NotificationChannel",
    "NotificationDispatcher",
    "NotificationMessage",
    "NotificationTemplate",
    "PasswordResetTemplate",
    "WelcomeTemplate",
]
