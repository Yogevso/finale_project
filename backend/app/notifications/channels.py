"""Notification delivery channels."""

from __future__ import annotations

from typing import Protocol

from app.domain.ports import EmailPort
from app.notifications.message import NotificationMessage


class NotificationChannel(Protocol):
    """Channel contract for delivering rendered messages."""

    async def deliver(self, message: NotificationMessage) -> bool:
        """Deliver a rendered notification message."""


class EmailNotificationChannel:
    """Email delivery channel backed by an email port."""

    def __init__(self, email_port: EmailPort):
        self._email_port = email_port

    async def deliver(self, message: NotificationMessage) -> bool:
        return await self._email_port.send_email(
            to_email=message.to_email,
            subject=message.subject,
            html_content=message.html_content,
            text_content=message.text_content,
        )
