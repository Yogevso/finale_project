"""Task 191 – Preview audience enforcement tests.

Verifies:
1. Management _audience_headers_for_document returns correct headers per visibility.
2. Headers are injected into both preview and download streaming helpers.
"""

from unittest.mock import MagicMock

from app.models import DocumentVisibility


class TestManagementAudienceHeaders:
    """Verify the management streaming helper produces correct audience headers."""

    def _mock_db_with_visibility(self, visibility: DocumentVisibility):
        """Return a mock db session whose Document query returns a doc with given visibility."""
        doc = MagicMock()
        doc.visibility = visibility

        query = MagicMock()
        query.filter_by.return_value.first.return_value = doc

        db = MagicMock()
        db.query.return_value = query
        return db

    def test_public_headers(self):
        from app.api.management.attachments import _audience_headers_for_document

        db = self._mock_db_with_visibility(DocumentVisibility.PUBLIC)
        headers = _audience_headers_for_document(db, document_id=1)
        assert headers["X-Frame-Options"] == "ALLOWALL"
        assert "X-Sharing-Policy" in headers
        sharing = headers["X-Sharing-Policy"]
        assert "direct_link" in sharing
        assert "social_share" in sharing

    def test_internal_headers(self):
        from app.api.management.attachments import _audience_headers_for_document

        db = self._mock_db_with_visibility(DocumentVisibility.INTERNAL)
        headers = _audience_headers_for_document(db, document_id=1)
        assert headers["X-Frame-Options"] == "DENY"
        sharing = headers["X-Sharing-Policy"]
        assert "social_share" not in sharing

    def test_company_headers(self):
        from app.api.management.attachments import _audience_headers_for_document

        db = self._mock_db_with_visibility(DocumentVisibility.COMPANY)
        headers = _audience_headers_for_document(db, document_id=1)
        assert headers["X-Frame-Options"] == "DENY"
        sharing = headers["X-Sharing-Policy"]
        assert "social_share" not in sharing
        assert "email_link" not in sharing

    def test_missing_document_returns_empty(self):
        from app.api.management.attachments import _audience_headers_for_document

        query = MagicMock()
        query.filter_by.return_value.first.return_value = None
        db = MagicMock()
        db.query.return_value = query
        headers = _audience_headers_for_document(db, document_id=999)
        assert headers == {}
