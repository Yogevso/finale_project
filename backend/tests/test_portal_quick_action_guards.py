"""Task 194 – Portal quick actions audience safeguards tests.

Verifies:
1. _get_scoped_document_or_404 blocks customers from INTERNAL documents.
2. _get_scoped_document_or_404 blocks customers from COMPANY documents when company doesn't match.
3. _get_scoped_document_or_404 allows customers to access PUBLIC documents.
4. _get_scoped_document_or_404 blocks customers from non-ACTIVE documents.
5. System admins bypass all audience checks.
"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models import DocumentStatus, DocumentVisibility, UserRole


class TestEngagementAudienceSafeguards:
    """Verify _get_scoped_document_or_404 enforces audience rules."""

    def _make_user(self, *, role=UserRole.CUSTOMER, tenant_id=1):
        user = MagicMock()
        user.role = role
        user.tenant_id = tenant_id
        return user

    def _make_document(self, *, status=DocumentStatus.ACTIVE, visibility=DocumentVisibility.PUBLIC, assigned_company_ids=None):
        doc = MagicMock()
        doc.status = status
        doc.visibility = visibility
        companies = []
        for cid in (assigned_company_ids or []):
            c = MagicMock()
            c.id = cid
            companies.append(c)
        doc.assigned_companies = companies
        return doc

    def _mock_db(self, document):
        db = MagicMock()
        query_mock = MagicMock()
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = document
        db.query.return_value = query_mock
        return db

    def test_customer_can_access_public_active(self):
        from app.api.management.engagement import _get_scoped_document_or_404

        user = self._make_user(role=UserRole.CUSTOMER, tenant_id=1)
        doc = self._make_document(status=DocumentStatus.ACTIVE, visibility=DocumentVisibility.PUBLIC)
        db = self._mock_db(doc)
        result = _get_scoped_document_or_404(db, 1, user)
        assert result is doc

    def test_customer_blocked_from_internal(self):
        from app.api.management.engagement import _get_scoped_document_or_404

        user = self._make_user(role=UserRole.CUSTOMER, tenant_id=1)
        doc = self._make_document(status=DocumentStatus.ACTIVE, visibility=DocumentVisibility.INTERNAL)
        db = self._mock_db(doc)
        with pytest.raises(HTTPException) as exc_info:
            _get_scoped_document_or_404(db, 1, user)
        assert exc_info.value.status_code == 403

    def test_customer_blocked_from_company_wrong_tenant(self):
        from app.api.management.engagement import _get_scoped_document_or_404

        user = self._make_user(role=UserRole.CUSTOMER, tenant_id=1)
        doc = self._make_document(
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.COMPANY,
            assigned_company_ids=[2, 3],
        )
        db = self._mock_db(doc)
        with pytest.raises(HTTPException) as exc_info:
            _get_scoped_document_or_404(db, 1, user)
        assert exc_info.value.status_code == 403

    def test_customer_allowed_company_matching_tenant(self):
        from app.api.management.engagement import _get_scoped_document_or_404

        user = self._make_user(role=UserRole.CUSTOMER, tenant_id=2)
        doc = self._make_document(
            status=DocumentStatus.ACTIVE,
            visibility=DocumentVisibility.COMPANY,
            assigned_company_ids=[2, 3],
        )
        db = self._mock_db(doc)
        result = _get_scoped_document_or_404(db, 1, user)
        assert result is doc

    def test_customer_blocked_from_non_active(self):
        from app.api.management.engagement import _get_scoped_document_or_404

        user = self._make_user(role=UserRole.CUSTOMER, tenant_id=1)
        doc = self._make_document(status=DocumentStatus.DRAFT, visibility=DocumentVisibility.PUBLIC)
        db = self._mock_db(doc)
        with pytest.raises(HTTPException) as exc_info:
            _get_scoped_document_or_404(db, 1, user)
        assert exc_info.value.status_code == 404

    def test_system_admin_bypasses_all_checks(self):
        from app.api.management.engagement import _get_scoped_document_or_404

        user = self._make_user(role=UserRole.SYSTEM_ADMIN, tenant_id=None)
        doc = self._make_document(status=DocumentStatus.DRAFT, visibility=DocumentVisibility.INTERNAL)
        db = self._mock_db(doc)
        result = _get_scoped_document_or_404(db, 1, user)
        assert result is doc

    def test_document_not_found_returns_404(self):
        from app.api.management.engagement import _get_scoped_document_or_404

        user = self._make_user(role=UserRole.CUSTOMER, tenant_id=1)
        db = self._mock_db(None)
        with pytest.raises(HTTPException) as exc_info:
            _get_scoped_document_or_404(db, 999, user)
        assert exc_info.value.status_code == 404
