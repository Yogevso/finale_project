"""Domain authorization capability objects."""

from app.domain.capabilities.authorization import (
    AnyPermissionCapability,
    CanAssignCompanies,
    CanPublish,
    CustomerUserCapability,
    DocumentAccessCapability,
    InternalUserCapability,
    ManageUserCapability,
    PermissionCapability,
    ReviewApprovalCapability,
    RoleCapability,
)

__all__ = [
    "AnyPermissionCapability",
    "CanAssignCompanies",
    "CanPublish",
    "CustomerUserCapability",
    "DocumentAccessCapability",
    "InternalUserCapability",
    "ManageUserCapability",
    "PermissionCapability",
    "ReviewApprovalCapability",
    "RoleCapability",
]
