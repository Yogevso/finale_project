"""
Company schemas for admin management
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class CompanyCreate(BaseModel):
    """Schema for creating a new company"""

    name: str = Field(..., min_length=2, max_length=100)
    slug: Optional[str] = Field(None, min_length=2, max_length=50, pattern=r"^[a-z0-9-]+$")
    contact_email: Optional[EmailStr] = None
    company_type: str = Field(default="customer", pattern=r"^(customer|partner|internal)$")
    company_logo: Optional[str] = None
    is_active: bool = True


class CompanyUpdate(BaseModel):
    """Schema for updating a company"""

    name: Optional[str] = Field(None, min_length=2, max_length=100)
    slug: Optional[str] = Field(None, min_length=2, max_length=50, pattern=r"^[a-z0-9-]+$")
    contact_email: Optional[EmailStr] = None
    company_type: Optional[str] = Field(None, pattern=r"^(customer|partner|internal)$")
    company_logo: Optional[str] = None
    is_active: Optional[bool] = None


class CompanyUserInfo(BaseModel):
    """User info within a company context"""

    id: int
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CompanyResponse(BaseModel):
    """Full company details response"""

    id: int
    name: str
    slug: str
    contact_email: Optional[str] = None
    company_type: str
    company_logo: Optional[str] = None
    is_active: bool
    user_count: int = 0
    owned_document_count: int = 0
    assigned_document_count: int = 0
    customer_visible_document_count: int = 0
    # Backward-compatible alias; mirrors `assigned_document_count`.
    document_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompanyListResponse(BaseModel):
    """Paginated company list response"""

    items: List[CompanyResponse]
    total: int
    page: int
    per_page: int
    pages: int


class CompanyDetailResponse(BaseModel):
    """Detailed company response with users"""

    id: int
    name: str
    slug: str
    contact_email: Optional[str] = None
    company_type: str
    company_logo: Optional[str] = None
    is_active: bool
    user_count: int = 0
    owned_document_count: int = 0
    assigned_document_count: int = 0
    customer_visible_document_count: int = 0
    # Backward-compatible alias; mirrors `assigned_document_count`.
    document_count: int = 0
    users: List[CompanyUserInfo] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompanyUserAdd(BaseModel):
    """Schema for adding a user to a company"""

    user_id: Optional[int] = None
    email: Optional[EmailStr] = None

    class Config:
        # At least one of user_id or email must be provided
        pass


class CompanyUserRemove(BaseModel):
    """Schema for removing a user from a company"""

    user_id: int
