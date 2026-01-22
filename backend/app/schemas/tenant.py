"""Tenant schemas"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TenantBase(BaseModel):
    """Base tenant schema"""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    is_active: bool = True


class TenantCreate(TenantBase):
    """Schema for creating a tenant"""

    pass


class TenantUpdate(BaseModel):
    """Schema for updating a tenant"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    is_active: Optional[bool] = None
    settings: Optional[str] = None


class TenantResponse(TenantBase):
    """Schema for tenant response"""

    id: int
    settings: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenantInDB(TenantResponse):
    """Schema for tenant in database"""

    pass


class TenantListResponse(BaseModel):
    """Schema for list of tenants"""

    items: list[TenantResponse]
    total: int
