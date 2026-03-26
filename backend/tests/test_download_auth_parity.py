"""Task 189 – Download auth parity tests.

Verifies:
1. Anonymous callers are blocked from non-PUBLIC documents via _enforce_attachment_access.
2. Viewer streaming responses carry audience policy headers (X-Frame-Options, X-Sharing-Policy).
"""

from unittest.mock import MagicMock

import pytest

from app.errors import DomainError
from app.models import DocumentVisibility

# ---------------------------------------------------------------------------
# 1. _enforce_attachment_access – anonymous defence-in-depth
# ---------------------------------------------------------------------------


class TestEnforceAttachmentAccessAnonymous:
    """Verify anonymous short-circuit now checks visibility."""

    def _make_document(self, visibility: DocumentVisibility):
        doc = MagicMock()
        doc.visibility = visibility
        return doc

    def test_anonymous_public_allowed(self):
        from app.services.attachment_service.common import AttachmentServiceCommonMixin

        doc = self._make_document(DocumentVisibility.PUBLIC)
        # Should not raise
        AttachmentServiceCommonMixin._enforce_attachment_access(doc, current_user=None)

    def test_anonymous_internal_blocked(self):
        from app.services.attachment_service.common import AttachmentServiceCommonMixin

        doc = self._make_document(DocumentVisibility.INTERNAL)
        with pytest.raises(DomainError) as exc_info:
            AttachmentServiceCommonMixin._enforce_attachment_access(doc, current_user=None)
        assert exc_info.value.status_code == 403

    def test_anonymous_company_blocked(self):
        from app.services.attachment_service.common import AttachmentServiceCommonMixin

        doc = self._make_document(DocumentVisibility.COMPANY)
        with pytest.raises(DomainError) as exc_info:
            AttachmentServiceCommonMixin._enforce_attachment_access(doc, current_user=None)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# 2. Viewer download/preview headers carry audience policy
# ---------------------------------------------------------------------------


class TestViewerStreamingHeaders:
    """Ensure audience policy headers appear in viewer streaming helpers."""

    def test_audience_policy_headers_public(self):
        from app.api.viewer.documents import _audience_policy_headers

        headers = _audience_policy_headers(DocumentVisibility.PUBLIC)
        # PUBLIC docs: embed allowed everywhere → X-Frame-Options = ALLOWALL
        assert headers["X-Frame-Options"] == "ALLOWALL"
        assert headers["Content-Security-Policy"] == "frame-ancestors *"
        # Sharing should list all actions
        assert "X-Sharing-Policy" in headers
        sharing = headers["X-Sharing-Policy"]
        assert "direct_link" in sharing
        assert "social_share" in sharing
        assert "email_link" in sharing
        assert "copy_link" in sharing

    def test_audience_policy_headers_internal(self):
        from app.api.viewer.documents import _audience_policy_headers

        headers = _audience_policy_headers(DocumentVisibility.INTERNAL)
        # INTERNAL: no IFRAME embed → DENY
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["Content-Security-Policy"] == "frame-ancestors 'none'"
        # No social sharing
        sharing = headers["X-Sharing-Policy"]
        assert "social_share" not in sharing
        assert "direct_link" in sharing
        assert "email_link" in sharing
        assert "copy_link" in sharing

    def test_audience_policy_headers_company(self):
        from app.api.viewer.documents import _audience_policy_headers

        headers = _audience_policy_headers(DocumentVisibility.COMPANY)
        # COMPANY: no embed → DENY
        assert headers["X-Frame-Options"] == "DENY"
        # Only direct_link and copy_link
        sharing = headers["X-Sharing-Policy"]
        assert "social_share" not in sharing
        assert "email_link" not in sharing
        assert "direct_link" in sharing
        assert "copy_link" in sharing
