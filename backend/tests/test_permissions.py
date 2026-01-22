"""Tests for the permission system"""

from app.models import UserRole
from app.services.permissions import (
    ROLE_PERMISSIONS,
    Permission,
    can_view_document,
    has_permission,
    is_internal_user,
)


class TestPermissionMatrix:
    """Test that the permission matrix is correctly defined"""

    def test_system_admin_has_all_permissions(self):
        """System admin should have all permissions"""
        system_admin_perms = ROLE_PERMISSIONS[UserRole.SYSTEM_ADMIN]
        # Check key permissions
        assert Permission.VIEW_PUBLIC_DOCS in system_admin_perms
        assert Permission.VIEW_INTERNAL_DOCS in system_admin_perms
        assert Permission.VIEW_COMPANY_DOCS in system_admin_perms
        assert Permission.MANAGE_ADMINS in system_admin_perms
        assert Permission.SYSTEM_SETTINGS in system_admin_perms
        assert Permission.PUBLISH_DOCUMENT in system_admin_perms

    def test_admin_cannot_manage_admins(self):
        """Admin should not be able to manage other admins"""
        admin_perms = ROLE_PERMISSIONS[UserRole.ADMIN]
        assert Permission.MANAGE_ADMINS not in admin_perms
        # But should have most other permissions
        assert Permission.MANAGE_USERS in admin_perms
        assert Permission.MANAGE_COMPANIES in admin_perms
        assert Permission.SYSTEM_SETTINGS in admin_perms

    def test_manager_permissions(self):
        """Manager should have content management permissions"""
        manager_perms = ROLE_PERMISSIONS[UserRole.MANAGER]
        assert Permission.PUBLISH_DOCUMENT in manager_perms
        assert Permission.APPROVE_REVIEW in manager_perms
        assert Permission.ASSIGN_COMPANIES in manager_perms
        # But not user management or system settings
        assert Permission.MANAGE_USERS not in manager_perms
        assert Permission.SYSTEM_SETTINGS not in manager_perms
        # Can manage editors though
        assert Permission.MANAGE_EDITORS in manager_perms

    def test_editor_permissions(self):
        """Editor should have content creation permissions"""
        editor_perms = ROLE_PERMISSIONS[UserRole.EDITOR]
        assert Permission.CREATE_DOCUMENT in editor_perms
        assert Permission.EDIT_DOCUMENT in editor_perms
        assert Permission.SUBMIT_REVIEW in editor_perms
        assert Permission.APPROVE_PEER_REVIEW in editor_perms
        # But not publishing or management
        assert Permission.PUBLISH_DOCUMENT not in editor_perms
        assert Permission.DELETE_DOCUMENT not in editor_perms
        assert Permission.MANAGE_USERS not in editor_perms

    def test_viewer_permissions(self):
        """Viewer should only have read permissions"""
        viewer_perms = ROLE_PERMISSIONS[UserRole.VIEWER]
        assert Permission.VIEW_PUBLIC_DOCS in viewer_perms
        assert Permission.VIEW_INTERNAL_DOCS in viewer_perms
        assert Permission.ADD_COMMENTS in viewer_perms
        assert Permission.DOWNLOAD_ATTACHMENTS in viewer_perms
        # No content creation
        assert Permission.CREATE_DOCUMENT not in viewer_perms
        assert Permission.EDIT_DOCUMENT not in viewer_perms

    def test_customer_permissions(self):
        """Customer should have limited permissions"""
        customer_perms = ROLE_PERMISSIONS[UserRole.CUSTOMER]
        assert Permission.VIEW_PUBLIC_DOCS in customer_perms
        assert Permission.VIEW_COMPANY_DOCS in customer_perms
        assert Permission.SUBMIT_FEEDBACK in customer_perms
        assert Permission.DOWNLOAD_ATTACHMENTS in customer_perms
        # No internal docs or content management
        assert Permission.VIEW_INTERNAL_DOCS not in customer_perms
        assert Permission.CREATE_DOCUMENT not in customer_perms
        assert Permission.ADD_COMMENTS not in customer_perms


class TestHasPermission:
    """Test the has_permission function"""

    def test_has_permission_with_valid_permission(self, db, test_admin):
        """User with permission should return True"""
        assert has_permission(test_admin, Permission.VIEW_PUBLIC_DOCS) is True
        assert has_permission(test_admin, Permission.MANAGE_USERS) is True

    def test_has_permission_without_permission(self, db, test_user):
        """User without permission should return False"""
        # test_user is an editor
        assert has_permission(test_user, Permission.PUBLISH_DOCUMENT) is False
        assert has_permission(test_user, Permission.MANAGE_USERS) is False

    def test_has_permission_none_user(self):
        """None user should return False"""
        assert has_permission(None, Permission.VIEW_PUBLIC_DOCS) is False


class TestIsInternalUser:
    """Test the is_internal_user function"""

    def test_admin_is_internal(self, db, test_admin):
        """Admin should be internal"""
        assert is_internal_user(test_admin) is True

    def test_editor_is_internal(self, db, test_user):
        """Editor should be internal"""
        assert is_internal_user(test_user) is True

    def test_viewer_is_internal(self, db, test_viewer):
        """Viewer should be internal"""
        assert is_internal_user(test_viewer) is True

    def test_customer_is_not_internal(self, db, test_customer):
        """Customer should not be internal"""
        assert is_internal_user(test_customer) is False


class TestCanViewDocument:
    """Test document visibility checks"""

    def test_public_document_visible_to_all(
        self, db, public_document, test_admin, test_user, test_viewer, test_customer
    ):
        """Public documents should be visible to all users"""
        assert can_view_document(test_admin, public_document) is True
        assert can_view_document(test_user, public_document) is True
        assert can_view_document(test_viewer, public_document) is True
        assert can_view_document(test_customer, public_document) is True

    def test_internal_document_visible_to_staff(
        self, db, internal_document, test_admin, test_user, test_viewer
    ):
        """Internal documents should be visible to internal staff"""
        assert can_view_document(test_admin, internal_document) is True
        assert can_view_document(test_user, internal_document) is True
        assert can_view_document(test_viewer, internal_document) is True

    def test_internal_document_hidden_from_customer(self, db, internal_document, test_customer):
        """Internal documents should be hidden from customers"""
        assert can_view_document(test_customer, internal_document) is False

    def test_company_document_visible_to_assigned_customer(
        self, db, company_document, test_customer
    ):
        """Company documents should be visible to assigned customers"""
        # test_customer belongs to test_tenant, which is assigned to company_document
        assert can_view_document(test_customer, company_document) is True

    def test_company_document_hidden_from_other_customer(
        self, db, company_document, test_customer_2
    ):
        """Company documents should be hidden from non-assigned customers"""
        # test_customer_2 belongs to test_tenant_2, which is not assigned
        assert can_view_document(test_customer_2, company_document) is False

    def test_company_document_visible_to_staff(self, db, company_document, test_admin, test_user):
        """Company documents should be visible to internal staff"""
        assert can_view_document(test_admin, company_document) is True
        assert can_view_document(test_user, company_document) is True


class TestRoleHierarchy:
    """Test role hierarchy behavior"""

    def test_higher_roles_have_more_permissions(self):
        """Higher roles should have more or equal permissions"""
        system_admin_count = len(ROLE_PERMISSIONS[UserRole.SYSTEM_ADMIN])
        admin_count = len(ROLE_PERMISSIONS[UserRole.ADMIN])
        manager_count = len(ROLE_PERMISSIONS[UserRole.MANAGER])
        editor_count = len(ROLE_PERMISSIONS[UserRole.EDITOR])
        viewer_count = len(ROLE_PERMISSIONS[UserRole.VIEWER])
        customer_count = len(ROLE_PERMISSIONS[UserRole.CUSTOMER])

        assert system_admin_count >= admin_count
        assert admin_count >= manager_count
        assert manager_count >= editor_count
        assert editor_count >= viewer_count
        # Customer is separate path, may have more or less than viewer
        assert customer_count >= 0  # Just ensure it's defined
