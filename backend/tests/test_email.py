"""Tests for Email Service"""

import asyncio
from unittest.mock import patch

from app.config import settings
from app.services.email_service import EmailService


def run_async(coro):
    """Helper to run async functions in sync tests"""
    return asyncio.get_event_loop().run_until_complete(coro)


class TestEmailService:
    """Test email service functionality"""

    def test_email_service_initialization(self):
        """Test email service initializes correctly"""
        service = EmailService()
        assert service is not None

    def test_send_email_dev_mode(self):
        """Test send_email in dev mode (EMAIL_ENABLED=False)"""
        with patch.object(settings, "EMAIL_ENABLED", False):
            service = EmailService()
            service.enabled = False  # Also update instance
            result = run_async(
                service.send_email(
                    to_email="test@example.com",
                    subject="Test Subject",
                    html_content="<p>Test content</p>",
                    text_content="Test content",
                )
            )
            # In dev mode, should log but return True
            assert result is True

    def test_send_document_published_dev_mode(self):
        """Test send_document_published in dev mode"""
        with patch.object(settings, "EMAIL_ENABLED", False):
            service = EmailService()
            service.enabled = False
            result = run_async(
                service.send_document_published(
                    to_email="author@example.com",
                    document_title="Test Document",
                    document_number="DOC-001",
                    document_url="http://localhost/doc/1",
                )
            )
            assert result is True

    def test_send_new_comment_dev_mode(self):
        """Test send_new_comment in dev mode"""
        with patch.object(settings, "EMAIL_ENABLED", False):
            service = EmailService()
            service.enabled = False
            result = run_async(
                service.send_new_comment(
                    to_email="author@example.com",
                    commenter_name="John Doe",
                    document_title="Test Document",
                    comment_text="This is a great document!",
                    document_url="http://localhost/doc/1",
                )
            )
            assert result is True

    def test_send_password_reset_dev_mode(self):
        """Test send_password_reset in dev mode"""
        with patch.object(settings, "EMAIL_ENABLED", False):
            service = EmailService()
            service.enabled = False
            result = run_async(
                service.send_password_reset(
                    to_email="user@example.com", reset_url="http://localhost/reset/token123"
                )
            )
            assert result is True

    def test_send_welcome_dev_mode(self):
        """Test send_welcome in dev mode"""
        with patch.object(settings, "EMAIL_ENABLED", False):
            service = EmailService()
            service.enabled = False
            result = run_async(
                service.send_welcome(
                    to_email="newuser@example.com",
                    user_name="newuser",
                    login_url="http://localhost/login",
                )
            )
            assert result is True


class TestEmailServiceSingleton:
    """Test email service singleton pattern"""

    def test_singleton_instance_available(self):
        """Test that singleton instance is available"""
        from app.services.email_service import email_service

        assert email_service is not None
        assert isinstance(email_service, EmailService)
