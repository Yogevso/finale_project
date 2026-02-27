"""SMTP-backed email adapter."""

from __future__ import annotations

from app.domain.ports import EmailPort
from app.services.email_service import EmailService


class SmtpEmailAdapter(EmailPort):
    """Adapter that delegates to the existing EmailService."""

    def __init__(self, service: EmailService | None = None):
        self._service = service or EmailService()

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str | None = None,
    ) -> bool:
        return await self._service.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

