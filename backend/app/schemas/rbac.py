"""RBAC policy schemas"""

from typing import List

from pydantic import BaseModel

from app.models import UserRole
from app.services.permissions import Permission


class RbacPolicyInput(BaseModel):
    """RBAC policy input schema"""

    role: UserRole
    permissions: List[Permission]


class RbacPoliciesUpdate(BaseModel):
    """Bulk RBAC policy update request"""

    policies: List[RbacPolicyInput]
    confirm_password: str


class RbacPolicyResponse(RbacPolicyInput):
    """RBAC policy response"""

    pass


class RbacPoliciesResponse(BaseModel):
    """RBAC policies response"""

    policies: List[RbacPolicyResponse]
