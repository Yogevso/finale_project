"""Pydantic Schemas - API Contracts"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import ActionType, DocumentStatus, UserRole


# ========== User Schemas ==========
class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=255)


class UserCreate(UserBase):
    """User creation schema"""
    password: str = Field(..., min_length=8, max_length=100)
    role: UserRole = UserRole.VIEWER


class UserUpdate(BaseModel):
    """User update schema"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """User response schema"""
    id: int
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ========== Authentication Schemas ==========
class LoginRequest(BaseModel):
    """Login request schema"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema"""
    refresh_token: str


class PasswordChange(BaseModel):
    """Password change schema"""
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


# ========== Document Schemas ==========
class DocumentBase(BaseModel):
    """Base document schema"""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[str] = None


class DocumentCreate(DocumentBase):
    """Document creation schema"""
    status: DocumentStatus = DocumentStatus.DRAFT


class DocumentUpdate(BaseModel):
    """Document update schema"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[DocumentStatus] = None
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[str] = None


class DocumentResponse(DocumentBase):
    """Document response schema"""
    id: int
    document_number: str
    status: DocumentStatus
    created_by: int
    created_at: datetime
    updated_at: datetime

    # Optional related data
    created_by_user: Optional["UserResponse"] = None
    versions_count: Optional[int] = None
    attachments_count: Optional[int] = None
    comments_count: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    """Document list response schema"""
    items: List[DocumentResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ========== Version Schemas ==========
class VersionBase(BaseModel):
    """Base version schema"""
    content: Optional[str] = None
    changes_summary: Optional[str] = None


class VersionCreate(VersionBase):
    """Version creation schema"""
    pass


class VersionUpdate(BaseModel):
    """Version update schema (only unpublished versions)"""
    content: Optional[str] = None
    changes_summary: Optional[str] = None


class VersionResponse(VersionBase):
    """Version response schema"""
    id: int
    document_id: int
    version_number: int
    is_published: bool = False
    published_at: Optional[datetime] = None
    created_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VersionListResponse(BaseModel):
    """Version list response"""
    items: List[VersionResponse]
    total: int


# ========== Attachment Schemas ==========
class AttachmentResponse(BaseModel):
    """Attachment response schema"""
    id: int
    document_id: int
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    uploaded_by: int
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttachmentUploadResponse(BaseModel):
    """Attachment upload response"""
    id: int
    filename: str
    url: Optional[str] = None
    message: str = "File uploaded successfully"


# ========== Comment Schemas ==========
class CommentBase(BaseModel):
    """Base comment schema"""
    content: str = Field(..., min_length=1, max_length=5000)


class CommentCreate(CommentBase):
    """Comment creation schema"""
    is_private: bool = False  # Private = only admins/editors can see
    anchor_text: Optional[str] = None  # The text that was selected for inline comment
    anchor_id: Optional[str] = None  # Reference to heading/section ID
    parent_id: Optional[int] = None  # For replies to create threads


class CommentUpdate(BaseModel):
    """Comment update schema"""
    content: Optional[str] = Field(None, min_length=1, max_length=5000)
    is_resolved: Optional[bool] = None  # Mark thread as resolved


class CommentAuthor(BaseModel):
    """Minimal author info for comments"""
    id: int
    username: str
    full_name: Optional[str] = None
    role: str

    model_config = ConfigDict(from_attributes=True)


class CommentResponse(CommentBase):
    """Comment response schema"""
    id: int
    document_id: int
    user_id: int
    parent_id: Optional[int] = None
    is_private: bool = False
    anchor_text: Optional[str] = None
    anchor_id: Optional[str] = None
    is_resolved: bool = False
    created_at: datetime
    updated_at: datetime
    user: Optional[CommentAuthor] = None
    replies: list["CommentResponse"] = []
    reply_count: int = 0

    model_config = ConfigDict(from_attributes=True)


# Forward reference for nested replies
CommentResponse.model_rebuild()


# ========== Audit Log Schemas ==========
class AuditLogResponse(BaseModel):
    """Audit log response schema"""
    id: int
    user_id: Optional[int]
    document_id: Optional[int]
    action: ActionType
    details: Optional[str]
    ip_address: Optional[str]
    created_at: datetime
    user: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ========== General Schemas ==========
class MessageResponse(BaseModel):
    """Generic message response"""
    message: str


class ErrorResponse(BaseModel):
    """Error response schema"""
    detail: str


# Export all schemas
__all__ = [
    # User
    "UserBase", "UserCreate", "UserUpdate", "UserResponse",
    # Auth
    "LoginRequest", "TokenResponse", "RefreshTokenRequest", "PasswordChange",
    # Document
    "DocumentBase", "DocumentCreate", "DocumentUpdate", "DocumentResponse", "DocumentListResponse",
    # Version
    "VersionBase", "VersionCreate", "VersionUpdate", "VersionResponse", "VersionListResponse",
    # Attachment
    "AttachmentResponse", "AttachmentUploadResponse",
    # Comment
    "CommentBase", "CommentCreate", "CommentUpdate", "CommentResponse",
    # Audit
    "AuditLogResponse",
    # General
    "MessageResponse", "ErrorResponse",
]
