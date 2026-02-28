"""Regression tests for class-based web controllers."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.dependencies.tenant import TenantContext
from app.web.controllers.management import UsersController
from app.web.controllers.portal import PortalDocumentsController


def test_users_controller_rejects_non_admin_list(db, test_user):
    controller = UsersController()
    tenant_ctx = TenantContext(
        tenant_id=test_user.tenant_id,
        user_id=test_user.id,
        user_role=test_user.role,
        is_system_admin=False,
    )

    with pytest.raises(HTTPException) as exc_info:
        controller.list_users(
            role=None,
            company_id=None,
            is_active=None,
            search=None,
            current_user=test_user,
            tenant_ctx=tenant_ctx,
            db=db,
        )

    assert exc_info.value.status_code == 403
    assert "Admin access required" in str(exc_info.value.detail)


def test_portal_documents_controller_requires_customer(test_user, test_customer):
    controller = PortalDocumentsController()

    assert controller.require_customer(current_user=test_customer) == test_customer

    with pytest.raises(HTTPException) as exc_info:
        controller.require_customer(current_user=test_user)

    assert exc_info.value.status_code == 403
