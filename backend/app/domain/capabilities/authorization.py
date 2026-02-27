"""Authorization capability objects."""

from __future__ import annotations

from dataclasses import dataclass

from app.models import UserRole


@dataclass(frozen=True)
class PermissionCapability:
    """Capability bound to a single required permission."""

    name: str
    permission: object


class CanPublish(PermissionCapability):
    """Capability to publish documents."""

    def __init__(self, permission: object):
        super().__init__(name="CanPublish", permission=permission)


class CanAssignCompanies(PermissionCapability):
    """Capability to assign document-company scopes."""

    def __init__(self, permission: object):
        super().__init__(name="CanAssignCompanies", permission=permission)


@dataclass(frozen=True)
class AnyPermissionCapability:
    """Capability satisfied by at least one permission."""

    name: str
    permissions: tuple[object, ...]


@dataclass(frozen=True)
class RoleCapability:
    """Capability satisfied by role membership."""

    name: str
    roles: tuple[UserRole, ...]


@dataclass(frozen=True)
class InternalUserCapability:
    """Capability requiring an internal (non-customer) user."""

    name: str = "CanAccessInternal"


@dataclass(frozen=True)
class CustomerUserCapability:
    """Capability requiring a customer user."""

    name: str = "CanAccessCustomerPortal"


@dataclass(frozen=True)
class DocumentAccessCapability:
    """Capability for document-level view/edit/delete/publish authorization."""

    name: str
    access_type: str
    edit_permission: object
    delete_permission: object
    publish_permission: object


@dataclass(frozen=True)
class ReviewApprovalCapability:
    """Capability for review approval authorization."""

    name: str
    approve_permission: object
    peer_approve_permission: object


@dataclass(frozen=True)
class ManageUserCapability:
    """Capability for user-management authorization."""

    name: str = "CanManageUser"
