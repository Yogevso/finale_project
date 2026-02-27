"""Email delivery port."""

from __future__ import annotations

from typing import Protocol


class EmailPort(Protocol):
    """Abstract email transport contract."""

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str | None = None,
    ) -> bool:
        """Send an email through the configured transport."""

