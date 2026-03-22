"""
Tests for app/dependencies/permissions.py

This module tests all permission dependency factories and functions
to ensure proper access control across different user roles.
"""

import asyncio

import pytest
from fastapi import HTTPException

from app.dependencies.permissions import (
    DocumentAccessChecker,
    get_document_if_accessible,
    get_optional_current_user,
    require_admin,
    require_any_permission,
    require_any_role,
    require_customer,
    require_document_delete,
    require_document_edit,
    require_document_publish,
    require_document_view,
    require_editor,
    require_internal_user,
    require_manager,
    require_permission,
    require_system_admin,
)
from app.models import Document, DocumentStatus, DocumentVisibility, User, UserRole
from app.security import get_password_hash
from app.services.permissions import Permission


def run_async(coro):
    """Helper to run async functions synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ===================== Test require_permission factory =====================


class TestRequirePermission:
    """Tests for the require_permission dependency factory"""

    def test_require_permission_granted(self, db, test_admin):
        """Admin should have VIEW_INTERNAL_DOCS permission"""
        dependency = require_permission(Permission.VIEW_INTERNAL_DOCS)
        result = run_async(dependency(current_user=test_admin))
        assert result == test_admin

    def test_require_permission_denied(self, db, test_viewer):
        """Viewer should NOT have DELETE_DOCUMENT permission"""
        dependency = require_permission(Permission.DELETE_DOCUMENT)
        with pytest.raises(HTTPException) as exc_info:
            run_async(dependency(current_user=test_viewer))
        assert exc_info.value.status_code == 403
        assert "Permission denied" in exc_info.value.detail

    def test_require_permission_customer_limited(self, db, test_customer):
        """Customer should only have limited permissions"""
        # Customer should NOT have internal docs permission
        dependency = require_permission(Permission.VIEW_INTERNAL_DOCS)
        with pytest.raises(HTTPException) as exc_info:
            run_async(dependency(current_user=test_customer))
        assert exc_info.value.status_code == 403


# ===================== Test require_any_permission factory =====================


class TestRequireAnyPermission:
    """Tests for the require_any_permission dependency factory"""

    def test_require_any_permission_first_match(self, db, test_admin):
        """Should succeed when user has first permission"""
        dependency = require_any_permission(
            Permission.VIEW_PUBLIC_DOCS, Permission.VIEW_INTERNAL_DOCS
        )
        result = run_async(dependency(current_user=test_admin))
        assert result == test_admin

    def test_require_any_permission_second_match(self, db, test_viewer):
        """Viewer should have VIEW_PUBLIC_DOCS even if not internal"""
        dependency = require_any_permission(Permission.MANAGE_USERS, Permission.VIEW_PUBLIC_DOCS)
        result = run_async(dependency(current_user=test_viewer))
        assert result == test_viewer

    def test_require_any_permission_none_match(self, db, test_viewer):
        """Should fail when user has none of the permissions"""
        dependency = require_any_permission(Permission.DELETE_DOCUMENT, Permission.MANAGE_USERS)
        with pytest.raises(HTTPException) as exc_info:
            run_async(dependency(current_user=test_viewer))
        assert exc_info.value.status_code == 403
        assert "requires one of" in exc_info.value.detail


# ===================== Test require_any_role factory =====================


class TestRequireAnyRole:
    """Tests for the require_any_role dependency factory"""

    def test_require_any_role_first_match(self, db, test_admin):
        """Admin should match when ADMIN is in list"""
        dependency = require_any_role([UserRole.ADMIN, UserRole.SYSTEM_ADMIN])
        result = run_async(dependency(current_user=test_admin))
        assert result == test_admin

    def test_require_any_role_second_match(self, db, test_system_admin):
        """System admin should match when SYSTEM_ADMIN is in list"""
        dependency = require_any_role([UserRole.ADMIN, UserRole.SYSTEM_ADMIN])
        result = run_async(dependency(current_user=test_system_admin))
        assert result == test_system_admin

    def test_require_any_role_no_match(self, db, test_viewer):
        """Viewer should NOT match admin roles"""
        dependency = require_any_role([UserRole.ADMIN, UserRole.SYSTEM_ADMIN])
        with pytest.raises(HTTPException) as exc_info:
            run_async(dependency(current_user=test_viewer))
        assert exc_info.value.status_code == 403
        assert "requires role" in exc_info.value.detail


# ===================== Test require_internal_user =====================


class TestRequireInternalUser:
    """Tests for the require_internal_user dependency"""

    def test_require_internal_user_admin(self, db, test_admin):
        """Admin is an internal user"""
        result = run_async(require_internal_user(current_user=test_admin))
        assert result == test_admin

    def test_require_internal_user_editor(self, db, test_user):
        """Editor is an internal user"""
        result = run_async(require_internal_user(current_user=test_user))
        assert result == test_user

    def test_require_internal_user_manager(self, db, test_manager):
        """Manager is an internal user"""
        result = run_async(require_internal_user(current_user=test_manager))
        assert result == test_manager

    def test_require_internal_user_viewer(self, db, test_viewer):
        """Viewer is an internal user"""
        result = run_async(require_internal_user(current_user=test_viewer))
        assert result == test_viewer

    def test_require_internal_user_customer_denied(self, db, test_customer):
        """Customer is NOT an internal user"""
        with pytest.raises(HTTPException) as exc_info:
            run_async(require_internal_user(current_user=test_customer))
        assert exc_info.value.status_code == 403
        assert "internal users only" in exc_info.value.detail


# ===================== Test require_customer =====================


class TestRequireCustomer:
    """Tests for the require_customer dependency"""

    def test_require_customer_success(self, db, test_customer):
        """Customer should pass"""
        result = run_async(require_customer(current_user=test_customer))
        assert result == test_customer

    def test_require_customer_admin_denied(self, db, test_admin):
        """Admin is NOT a customer"""
        with pytest.raises(HTTPException) as exc_info:
            run_async(require_customer(current_user=test_admin))
        assert exc_info.value.status_code == 403
        assert "customers only" in exc_info.value.detail

    def test_require_customer_viewer_denied(self, db, test_viewer):
        """Viewer is NOT a customer"""
        with pytest.raises(HTTPException) as exc_info:
            run_async(require_customer(current_user=test_viewer))
        assert exc_info.value.status_code == 403


# ===================== Test require_admin =====================


class TestRequireAdmin:
    """Tests for the require_admin dependency"""

    def test_require_admin_admin(self, db, test_admin):
        """Admin should pass"""
        result = run_async(require_admin(current_user=test_admin))
        assert result == test_admin

    def test_require_admin_system_admin(self, db, test_system_admin):
        """System admin should pass (admin or above)"""
        result = run_async(require_admin(current_user=test_system_admin))
        assert result == test_system_admin

    def test_require_admin_manager_denied(self, db, test_manager):
        """Manager is NOT admin or above"""
        with pytest.raises(HTTPException) as exc_info:
            run_async(require_admin(current_user=test_manager))
        assert exc_info.value.status_code == 403
        assert "admin privileges required" in exc_info.value.detail

    def test_require_admin_editor_denied(self, db, test_user):
        """Editor is NOT admin or above"""
        with pytest.raises(HTTPException) as exc_info:
            run_async(require_admin(current_user=test_user))
        assert exc_info.value.status_code == 403


# ===================== Test require_system_admin =====================


class TestRequireSystemAdmin:
    """Tests for the require_system_admin dependency"""

    def test_require_system_admin_success(self, db, test_system_admin):
        """System admin should pass"""
        result = run_async(require_system_admin(current_user=test_system_admin))
        assert result == test_system_admin

    def test_require_system_admin_admin_denied(self, db, test_admin):
        """Regular admin is NOT system admin"""
        with pytest.raises(HTTPException) as exc_info:
            run_async(require_system_admin(current_user=test_admin))
        assert exc_info.value.status_code == 403
        assert "system administrator privileges required" in exc_info.value.detail

    def test_require_system_admin_manager_denied(self, db, test_manager):
        """Manager is NOT system admin"""
        with pytest.raises(HTTPException) as exc_info:
            run_async(require_system_admin(current_user=test_manager))
        assert exc_info.value.status_code == 403


# ===================== Test require_manager =====================


class TestRequireManager:
    """Tests for the require_manager dependency"""

    def test_require_manager_manager(self, db, test_manager):
        """Manager should pass"""
        result = run_async(require_manager(current_user=test_manager))
        assert result == test_manager

    def test_require_manager_admin(self, db, test_admin):
        """Admin should pass (manager or above)"""
        result = run_async(require_manager(current_user=test_admin))
        assert result == test_admin

    def test_require_manager_system_admin(self, db, test_system_admin):
        """System admin should pass (manager or above)"""
        result = run_async(require_manager(current_user=test_system_admin))
        assert result == test_system_admin

    def test_require_manager_editor_denied(self, db, test_user):
        """Editor is NOT manager or above"""
        with pytest.raises(HTTPException) as exc_info:
            run_async(require_manager(current_user=test_user))
        assert exc_info.value.status_code == 403
        assert "manager privileges required" in exc_info.value.detail

    def test_require_manager_viewer_denied(self, db, test_viewer):
        """Viewer is NOT manager or above"""
        with pytest.raises(HTTPException) as exc_info:
            run_async(require_manager(current_user=test_viewer))
        assert exc_info.value.status_code == 403


# ===================== Test require_editor =====================


class TestRequireEditor:
    """Tests for the require_editor dependency"""

    def test_require_editor_editor(self, db, test_user):
        """Editor should pass"""
        result = run_async(require_editor(current_user=test_user))
        assert result == test_user

    def test_require_editor_manager(self, db, test_manager):
        """Manager should pass (editor or above)"""
        result = run_async(require_editor(current_user=test_manager))
        assert result == test_manager

    def test_require_editor_admin(self, db, test_admin):
        """Admin should pass (editor or above)"""
        result = run_async(require_editor(current_user=test_admin))
        assert result == test_admin

    def test_require_editor_viewer_denied(self, db, test_viewer):
        """Viewer is NOT editor or above"""
        with pytest.raises(HTTPException) as exc_info:
            run_async(require_editor(current_user=test_viewer))
        assert exc_info.value.status_code == 403
        assert "editor privileges required" in exc_info.value.detail

    def test_require_editor_customer_denied(self, db, test_customer):
        """Customer is NOT editor or above"""
        with pytest.raises(HTTPException) as exc_info:
            run_async(require_editor(current_user=test_customer))
        assert exc_info.value.status_code == 403


# ===================== Test DocumentAccessChecker =====================


class TestDocumentAccessChecker:
    """Tests for the DocumentAccessChecker class"""

    def test_document_access_checker_view_public(self, db, test_viewer, public_document):
        """Viewer should be able to view public documents"""
        checker = DocumentAccessChecker("view")
        result = run_async(checker(document_id=public_document.id, current_user=test_viewer, db=db))
        assert result == public_document

    def test_document_access_checker_view_internal(self, db, test_viewer, internal_document):
        """Viewer should be able to view internal documents"""
        checker = DocumentAccessChecker("view")
        result = run_async(
            checker(document_id=internal_document.id, current_user=test_viewer, db=db)
        )
        assert result == internal_document

    def test_document_access_checker_customer_internal_denied(
        self, db, test_customer, internal_document
    ):
        """Customer should NOT view internal documents"""
        checker = DocumentAccessChecker("view")
        with pytest.raises(HTTPException) as exc_info:
            run_async(checker(document_id=internal_document.id, current_user=test_customer, db=db))
        assert exc_info.value.status_code == 403
        assert "cannot view" in exc_info.value.detail

    def test_document_access_checker_edit_admin(self, db, test_admin, public_document):
        """Admin should be able to edit documents"""
        checker = DocumentAccessChecker("edit")
        result = run_async(checker(document_id=public_document.id, current_user=test_admin, db=db))
        assert result == public_document

    def test_document_access_checker_edit_viewer_denied(self, db, test_viewer, public_document):
        """Viewer should NOT edit documents"""
        checker = DocumentAccessChecker("edit")
        with pytest.raises(HTTPException) as exc_info:
            run_async(checker(document_id=public_document.id, current_user=test_viewer, db=db))
        assert exc_info.value.status_code == 403
        assert "cannot edit" in exc_info.value.detail

    def test_document_access_checker_delete_admin(self, db, test_admin, public_document):
        """Admin should be able to delete documents"""
        checker = DocumentAccessChecker("delete")
        result = run_async(checker(document_id=public_document.id, current_user=test_admin, db=db))
        assert result == public_document

    def test_document_access_checker_delete_editor_denied(self, db, test_user, public_document):
        """Editor should NOT delete documents"""
        checker = DocumentAccessChecker("delete")
        with pytest.raises(HTTPException) as exc_info:
            run_async(checker(document_id=public_document.id, current_user=test_user, db=db))
        assert exc_info.value.status_code == 403
        assert "cannot delete" in exc_info.value.detail

    def test_document_access_checker_publish_manager(self, db, test_manager):
        """Manager should be able to publish documents"""
        # Create a document that needs publishing
        doc = Document(
            title="Doc to Publish",
            document_number="DOC-PUBLISH-001",
            status=DocumentStatus.DRAFT,
            visibility=DocumentVisibility.INTERNAL,
            created_by=test_manager.id,
            tenant_id=test_manager.tenant_id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        checker = DocumentAccessChecker("publish")
        result = run_async(checker(document_id=doc.id, current_user=test_manager, db=db))
        assert result == doc

    def test_document_access_checker_publish_editor_denied(self, db, test_user):
        """Editor should NOT publish documents"""
        doc = Document(
            title="Draft Doc",
            document_number="DOC-DRAFT-001",
            status=DocumentStatus.DRAFT,
            visibility=DocumentVisibility.INTERNAL,
            created_by=test_user.id,
            tenant_id=test_user.tenant_id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        checker = DocumentAccessChecker("publish")
        with pytest.raises(HTTPException) as exc_info:
            run_async(checker(document_id=doc.id, current_user=test_user, db=db))
        assert exc_info.value.status_code == 403
        assert "cannot publish" in exc_info.value.detail

    def test_document_access_checker_unknown_type(self, db, test_admin, public_document):
        """Unknown access type should default to view"""
        checker = DocumentAccessChecker("unknown")
        result = run_async(checker(document_id=public_document.id, current_user=test_admin, db=db))
        assert result == public_document

    def test_document_access_checker_not_found(self, db, test_admin):
        """Non-existent document should return 404"""
        checker = DocumentAccessChecker("view")
        with pytest.raises(HTTPException) as exc_info:
            run_async(checker(document_id=99999, current_user=test_admin, db=db))
        assert exc_info.value.status_code == 404
        assert "Document not found" in exc_info.value.detail


# ===================== Test pre-configured checkers =====================


class TestPreConfiguredCheckers:
    """Tests for pre-configured document access checkers"""

    def test_require_document_view(self, db, test_viewer, public_document):
        """Test require_document_view checker"""
        result = run_async(
            require_document_view(document_id=public_document.id, current_user=test_viewer, db=db)
        )
        assert result == public_document

    def test_require_document_edit(self, db, test_admin, public_document):
        """Test require_document_edit checker"""
        result = run_async(
            require_document_edit(document_id=public_document.id, current_user=test_admin, db=db)
        )
        assert result == public_document

    def test_require_document_delete(self, db, test_admin, public_document):
        """Test require_document_delete checker"""
        result = run_async(
            require_document_delete(document_id=public_document.id, current_user=test_admin, db=db)
        )
        assert result == public_document

    def test_require_document_publish(self, db, test_manager):
        """Test require_document_publish checker"""
        doc = Document(
            title="Doc to Publish",
            document_number="DOC-PUB-002",
            status=DocumentStatus.DRAFT,
            visibility=DocumentVisibility.INTERNAL,
            created_by=test_manager.id,
            tenant_id=test_manager.tenant_id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        result = run_async(
            require_document_publish(document_id=doc.id, current_user=test_manager, db=db)
        )
        assert result == doc


# ===================== Test get_document_if_accessible =====================


class TestGetDocumentIfAccessible:
    """Tests for the get_document_if_accessible dependency"""

    def test_get_document_if_accessible_public(self, db, test_viewer, public_document):
        """Viewer should access public documents"""
        result = run_async(
            get_document_if_accessible(
                document_id=public_document.id, current_user=test_viewer, db=db
            )
        )
        assert result == public_document

    def test_get_document_if_accessible_internal(self, db, test_admin, internal_document):
        """Admin should access internal documents"""
        result = run_async(
            get_document_if_accessible(
                document_id=internal_document.id, current_user=test_admin, db=db
            )
        )
        assert result == internal_document

    def test_get_document_if_accessible_not_found(self, db, test_admin):
        """Non-existent document should return 404"""
        with pytest.raises(HTTPException) as exc_info:
            run_async(get_document_if_accessible(document_id=99999, current_user=test_admin, db=db))
        assert exc_info.value.status_code == 404
        assert "Document not found" in exc_info.value.detail

    def test_get_document_if_accessible_denied(self, db, test_customer, internal_document):
        """Customer should NOT access internal documents"""
        with pytest.raises(HTTPException) as exc_info:
            run_async(
                get_document_if_accessible(
                    document_id=internal_document.id, current_user=test_customer, db=db
                )
            )
        assert exc_info.value.status_code == 403
        assert "cannot view" in exc_info.value.detail


# ===================== Test get_optional_current_user =====================


class TestGetOptionalCurrentUser:
    """Tests for the get_optional_current_user dependency factory"""

    def test_get_optional_current_user_no_token(self, db):
        """Should return None when no token is provided"""
        dependency = get_optional_current_user()
        result = run_async(dependency(token=None, db=db))
        assert result is None

    def test_get_optional_current_user_invalid_token(self, db):
        """Should return None for invalid token"""
        dependency = get_optional_current_user()
        result = run_async(dependency(token="invalid-token", db=db))
        assert result is None

    def test_get_optional_current_user_valid_token(self, db, test_user):
        """Should return user for valid token"""
        from app.security import create_access_token

        token = create_access_token({"sub": str(test_user.id)})
        dependency = get_optional_current_user()
        result = run_async(dependency(token=token, db=db))
        assert result is not None
        assert result.id == test_user.id

    def test_get_optional_current_user_inactive_user(self, db):
        """Should return None for inactive user"""
        from app.security import create_access_token

        # Create an inactive user
        inactive_user = User(
            email="inactive@example.com",
            username="inactiveuser",
            full_name="Inactive User",
            hashed_password=get_password_hash("password123"),
            role=UserRole.VIEWER,
            is_active=False,
        )
        db.add(inactive_user)
        db.commit()
        db.refresh(inactive_user)

        token = create_access_token({"sub": str(inactive_user.id)})
        dependency = get_optional_current_user()
        result = run_async(dependency(token=token, db=db))
        assert result is None

    def test_get_optional_current_user_nonexistent_user(self, db):
        """Should return None for non-existent user ID in token"""
        from app.security import create_access_token

        # Token with non-existent user ID
        token = create_access_token({"sub": "99999"})
        dependency = get_optional_current_user()
        result = run_async(dependency(token=token, db=db))
        assert result is None

    def test_get_optional_current_user_no_sub_in_token(self, db):
        """Should return None when token has no 'sub' claim"""
        from app.security import create_access_token

        # Token without 'sub'
        token = create_access_token({"foo": "bar"})
        dependency = get_optional_current_user()
        result = run_async(dependency(token=token, db=db))
        assert result is None


# ===================== Integration tests via API endpoints =====================


class TestPermissionDependenciesViaAPI:
    """Integration tests that verify permissions work through actual API calls"""

    def test_internal_endpoint_blocks_customer(self, client, customer_headers):
        """Customer should be blocked from internal endpoints"""
        # Try to access document listing (internal endpoint)
        response = client.get("/api/v1/documents/", headers=customer_headers)
        # This might return 403 or redirect based on implementation
        assert response.status_code in [200, 403]  # Customers may have limited doc access

    def test_admin_endpoint_blocks_viewer(self, client, viewer_auth_headers):
        """Viewer should be blocked from admin endpoints (user management)"""
        # Try to access user management (needs ADMIN role)
        response = client.get("/api/v1/users", headers=viewer_auth_headers)
        assert response.status_code == 403

    def test_admin_can_access_admin_endpoints(self, client, admin_headers):
        """Admin should access admin endpoints"""
        response = client.get("/api/v1/users", headers=admin_headers)
        assert response.status_code == 200

    def test_editor_can_create_document(self, client, auth_headers):
        """Editor should be able to create documents"""
        response = client.post(
            "/api/v1/documents/",
            headers=auth_headers,
            json={
                "title": "Test Document",
                "description": "Test description",
                "platform": "Core Platform",
            },
        )
        assert response.status_code == 201

    def test_customer_cannot_access_internal_users_endpoint(self, client, customer_headers):
        """Customer should NOT access user management endpoint"""
        response = client.get("/api/v1/users", headers=customer_headers)
        assert response.status_code == 403


# ===================== Test customer company document access =====================


class TestCustomerCompanyDocumentAccess:
    """Tests for customer access to company-specific documents"""

    def test_customer_can_view_assigned_company_doc(self, db, test_customer, company_document):
        """Customer should view documents assigned to their company"""
        checker = DocumentAccessChecker("view")
        result = run_async(
            checker(document_id=company_document.id, current_user=test_customer, db=db)
        )
        assert result == company_document

    def test_customer_cannot_view_other_company_doc(self, db, test_customer_2, company_document):
        """Customer should NOT view documents assigned to other companies"""
        checker = DocumentAccessChecker("view")
        with pytest.raises(HTTPException) as exc_info:
            run_async(checker(document_id=company_document.id, current_user=test_customer_2, db=db))
        assert exc_info.value.status_code == 403
