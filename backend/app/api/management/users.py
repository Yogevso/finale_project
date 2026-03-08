"""User Management API Routes."""

from __future__ import annotations

import io
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from PIL import Image, ImageOps
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.dependencies.permissions import require_admin
from app.dependencies.services import get_auth_service
from app.dependencies.tenant import TenantContext, get_tenant_context
from app.models import SecurityEvent, User, UserRole, UserSession
from app.schemas import MessageResponse, UserCreate, UserUpdate, UserWithCompanyResponse
from app.security import get_current_active_user
from app.services.auth_service import AuthService
from app.services.storage_service import get_storage_backend
from app.web.controllers.management import UsersController

router = APIRouter()
users_controller = UsersController()
storage_backend = get_storage_backend()
AVATAR_SIZE = (200, 200)
ALLOWED_AVATAR_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    timezone: Optional[str] = Field(None, min_length=1, max_length=64)
    locale: Optional[str] = Field(None, min_length=1, max_length=10)


class NotificationPreferencesUpdateRequest(BaseModel):
    notification_preferences: dict[str, bool]


class NotificationPreferencesResponse(BaseModel):
    notification_preferences: dict[str, bool]


class AvatarUploadResponse(BaseModel):
    avatar_url: str
    message: str


class UserSessionResponse(BaseModel):
    id: int
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    last_active_at: datetime
    is_current: bool


class UserSessionListResponse(BaseModel):
    items: list[UserSessionResponse]
    total: int


class SessionBulkRevokeResponse(BaseModel):
    message: str
    revoked_count: int


class SecurityEventResponse(BaseModel):
    id: int
    event_type: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime


class SecurityEventListResponse(BaseModel):
    items: list[SecurityEventResponse]
    total: int
    page: int
    page_size: int
    pages: int


@router.get("/users", response_model=list[UserWithCompanyResponse])
def list_users(
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    company_id: Optional[int] = Query(None, description="Filter by company"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    return users_controller.list_users(
        role=role,
        company_id=company_id,
        is_active=is_active,
        search=search,
        current_user=current_user,
        tenant_ctx=tenant_ctx,
        db=db,
    )


@router.post("/users", response_model=UserWithCompanyResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    return users_controller.create_user(
        user_data=user_data,
        current_user=current_user,
        tenant_ctx=tenant_ctx,
        db=db,
    )


@router.patch("/users/me", response_model=UserWithCompanyResponse)
def update_my_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update current user profile fields."""
    if payload.full_name is None and payload.timezone is None and payload.locale is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No profile fields provided",
        )

    if payload.full_name is not None:
        current_user.full_name = payload.full_name.strip()

    if payload.timezone is not None:
        normalized_timezone = payload.timezone.strip()
        if not normalized_timezone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="timezone must not be empty",
            )
        current_user.timezone = normalized_timezone

    if payload.locale is not None:
        normalized_locale = payload.locale.strip()
        if not normalized_locale:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="locale must not be empty",
            )
        current_user.locale = normalized_locale

    db.commit()
    db.refresh(current_user)
    return users_controller._serialize_user(current_user, db)


@router.patch(
    "/users/me/notification-preferences",
    response_model=NotificationPreferencesResponse,
)
def update_my_notification_preferences(
    payload: NotificationPreferencesUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update notification preference toggles for current user."""
    current_user.notification_preferences = payload.notification_preferences
    db.commit()
    return NotificationPreferencesResponse(
        notification_preferences=current_user.notification_preferences or {}
    )


@router.post("/users/me/avatar", response_model=AvatarUploadResponse)
def upload_my_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Upload and resize user avatar to a 200x200 image."""
    if file.content_type not in ALLOWED_AVATAR_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported avatar format",
        )

    file_bytes = file.file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avatar file is empty",
        )

    try:
        with Image.open(io.BytesIO(file_bytes)) as image:
            normalized = image.convert("RGB")
            resized = ImageOps.fit(normalized, AVATAR_SIZE, method=Image.Resampling.LANCZOS)
            output_stream = io.BytesIO()
            resized.save(output_stream, format="JPEG", quality=90)
            output_stream.seek(0)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid avatar image",
        ) from exc

    storage_key = storage_backend.upload(
        output_stream,
        filename=f"avatar_{current_user.id}.jpg",
        content_type="image/jpeg",
    )
    avatar_url = storage_backend.get_url(storage_key)

    current_user.avatar_url = avatar_url
    db.commit()

    return AvatarUploadResponse(
        avatar_url=avatar_url,
        message="Avatar uploaded successfully",
    )


@router.get("/users/me/sessions", response_model=UserSessionListResponse)
def list_my_sessions(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List active, non-revoked user sessions ordered by latest activity."""
    inactivity_cutoff = datetime.utcnow() - timedelta(days=settings.SESSION_INACTIVITY_DAYS)
    sessions = (
        db.query(UserSession)
        .filter(
            UserSession.user_id == current_user.id,
            UserSession.revoked_at.is_(None),
            UserSession.last_active_at >= inactivity_cutoff,
        )
        .order_by(UserSession.last_active_at.desc())
        .all()
    )
    current_session_id = getattr(request.state, "current_session_id", None)
    return UserSessionListResponse(
        items=[
            UserSessionResponse(
                id=session.id,
                ip_address=session.ip_address,
                user_agent=session.user_agent,
                created_at=session.created_at,
                last_active_at=session.last_active_at,
                is_current=session.id == current_session_id,
            )
            for session in sessions
        ],
        total=len(sessions),
    )


@router.delete("/users/me/sessions/{session_id}", response_model=MessageResponse)
def revoke_my_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Revoke a single active session by id for the current user."""
    user_session = (
        db.query(UserSession)
        .filter(
            UserSession.id == session_id,
            UserSession.user_id == current_user.id,
            UserSession.revoked_at.is_(None),
        )
        .first()
    )
    if user_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    user_session.revoked_at = datetime.utcnow()
    db.add(
        SecurityEvent(
            user_id=current_user.id,
            event_type="session_revoked",
            ip_address=user_session.ip_address,
            user_agent=user_session.user_agent,
        )
    )
    db.commit()
    return MessageResponse(message="Session revoked")


@router.delete("/users/me/sessions", response_model=SessionBulkRevokeResponse)
def revoke_all_other_sessions(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Revoke all active sessions for the current user except current session."""
    now = datetime.utcnow()
    current_session_id = getattr(request.state, "current_session_id", None)
    query = db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.revoked_at.is_(None),
    )
    if current_session_id is not None:
        query = query.filter(UserSession.id != current_session_id)

    revoked_count = query.update({UserSession.revoked_at: now}, synchronize_session=False)
    if revoked_count > 0:
        db.add(
            SecurityEvent(
                user_id=current_user.id,
                event_type="sessions_revoked_all",
            )
        )
    db.commit()
    return SessionBulkRevokeResponse(
        message="All other sessions revoked",
        revoked_count=revoked_count,
    )


@router.get("/users/me/security-events", response_model=SecurityEventListResponse)
def list_my_security_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List paginated security events for the current user (newest first)."""
    query = db.query(SecurityEvent).filter(SecurityEvent.user_id == current_user.id)
    total = query.count()
    pages = (total + page_size - 1) // page_size if total > 0 else 0
    events = (
        query.order_by(SecurityEvent.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return SecurityEventListResponse(
        items=[
            SecurityEventResponse(
                id=event.id,
                event_type=event.event_type,
                ip_address=event.ip_address,
                user_agent=event.user_agent,
                created_at=event.created_at,
            )
            for event in events
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/users/{user_id}", response_model=UserWithCompanyResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    return users_controller.get_user(
        user_id=user_id,
        current_user=current_user,
        tenant_ctx=tenant_ctx,
        db=db,
    )


@router.put("/users/{user_id}", response_model=UserWithCompanyResponse)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    return users_controller.update_user(
        user_id=user_id,
        user_data=user_data,
        current_user=current_user,
        tenant_ctx=tenant_ctx,
        db=db,
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    users_controller.delete_user(
        user_id=user_id,
        current_user=current_user,
        tenant_ctx=tenant_ctx,
        db=db,
    )
    return None


@router.get("/users/{user_id}/company-binding")
def check_company_binding(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Check a user's company binding status.
    Returns validation info about the user-company relationship.
    Admin+ or self access required.
    """
    return users_controller.check_company_binding(
        user_id=user_id,
        current_user=current_user,
        tenant_ctx=tenant_ctx,
        db=db,
    )


@router.post("/admin/users/{user_id}/unlock", response_model=MessageResponse)
def unlock_user_account(
    user_id: int,
    current_user: User = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Admin unlock endpoint for account lockout recovery."""
    _ = current_user
    auth_service.unlock_user_account(user_id)
    return MessageResponse(message="User account unlocked")
