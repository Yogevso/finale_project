"""Schemas for Wave AA — GDPR data export/deletion and compliance."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DataRequestType(str, Enum):
    EXPORT = "export"
    DELETION = "deletion"


class DataRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"


# ── AA-001: Data Export ───────────────────────────────────────────


class DataExportRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


class DataExportResponse(BaseModel):
    id: int
    user_id: int
    request_type: str = "export"
    status: str
    reason: str
    requested_at: datetime
    completed_at: Optional[datetime] = None
    download_url: Optional[str] = None

    class Config:
        from_attributes = True


# ── AA-002: Data Deletion ────────────────────────────────────────


class DataDeletionRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)
    confirm_deletion: bool = Field(..., description="Must be true to proceed")


class DataDeletionResponse(BaseModel):
    id: int
    user_id: int
    request_type: str = "deletion"
    status: str
    reason: str
    requested_at: datetime
    approved_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DataDeletionApproval(BaseModel):
    approved: bool
    comment: Optional[str] = None


# ── Admin views ──────────────────────────────────────────────────


class DataRequestListItem(BaseModel):
    id: int
    user_id: int
    user_email: str
    request_type: str
    status: str
    reason: str
    requested_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── AA-004: Audit integrity check ────────────────────────────────


class AuditIntegrityResult(BaseModel):
    total_signed: int
    valid: int
    invalid: int
    unsigned: int
    integrity_ok: bool
