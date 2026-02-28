"""Tests for notification templates, channels, and dispatcher."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.notifications import (
    DocumentPublishedTemplate,
    EmailNotificationChannel,
    NotificationDispatcher,
    NotificationMessage,
)


def run_async(coro):
    """Helper to run async code in synchronous tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


@dataclass
class RecordingEmailPort:
    """Test double for email delivery port."""

    calls: list[dict] | None = None

    def __post_init__(self):
        if self.calls is None:
            self.calls = []

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str | None = None,
    ) -> bool:
        self.calls.append(
            {
                "to_email": to_email,
                "subject": subject,
                "html_content": html_content,
                "text_content": text_content,
            }
        )
        return True


@dataclass
class RecordingChannel:
    """Test double for generic notification channel."""

    messages: list[NotificationMessage] | None = None

    def __post_init__(self):
        if self.messages is None:
            self.messages = []

    async def deliver(self, message: NotificationMessage) -> bool:
        self.messages.append(message)
        return True


def test_document_published_template_renders_expected_message():
    template = DocumentPublishedTemplate(
        document_title="Release Notes",
        document_number="DOC-100",
        document_url="http://localhost/docs/100",
    )

    message = template.render(to_email="author@example.com")

    assert message.to_email == "author@example.com"
    assert message.subject == "Document Published: Release Notes"
    assert "DOC-100" in message.html_content
    assert "http://localhost/docs/100" in message.text_content


def test_email_notification_channel_delegates_to_email_port():
    email_port = RecordingEmailPort()
    channel = EmailNotificationChannel(email_port)
    message = NotificationMessage(
        to_email="recipient@example.com",
        subject="Test Subject",
        html_content="<p>hello</p>",
        text_content="hello",
    )

    result = run_async(channel.deliver(message))

    assert result is True
    assert len(email_port.calls) == 1
    assert email_port.calls[0]["to_email"] == "recipient@example.com"
    assert email_port.calls[0]["subject"] == "Test Subject"


def test_notification_dispatcher_sends_messages_to_registered_channels():
    channel_a = RecordingChannel()
    channel_b = RecordingChannel()
    dispatcher = NotificationDispatcher(channels=[channel_a, channel_b])
    message = NotificationMessage(
        to_email="recipient@example.com",
        subject="Dispatch Test",
        html_content="<p>dispatch</p>",
        text_content="dispatch",
    )

    result = run_async(dispatcher.dispatch_message(message))

    assert result is True
    assert channel_a.messages == [message]
    assert channel_b.messages == [message]
