"""Notification message objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NotificationMessage:
    """Canonical delivery message shared across channels."""

    to_email: str
    subject: str
    html_content: str
    text_content: str | None = None
