"""Authentication API Routes"""

import asyncio
import json
from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.dependencies.services import (
    get_auth_service,
    get_collaboration_service,
)
from app.errors import DomainError
from app.models import ActionType, InvitationStatus, Tenant, User, UserRole
from app.repositories import InvitationRepository, UserRepository
from app.schemas import (
    LoginRequest,
    MessageResponse,
    PasswordChange,
    PublicRegistrationRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from app.security import get_current_active_user, get_password_hash
from app.services.auth_rate_limit_service import AuthRateLimitService
from app.services.auth_service import AuthService
from app.services.collaboration_service import CollaborationService
from app.services.email_service import email_service
from app.services.permissions import get_user_permissions
from app.services.permissions import ROLE_PERMISSIONS as _STATIC_ROLE_PERMISSIONS
from app.services.audit_helper import write_audit_log
from app.utils.request_ip import get_client_ip

router = APIRouter()
_INVITATION_ACCEPT_CONFLICT_DETAIL = (
    "Unable to accept invitation with the provided account details"
)


# ========== Invitation Acceptance Schemas ==========
class InvitationValidateResponse(BaseModel):
    """Response for validating an invitation token"""

    valid: bool
    email: str | None = None
    role: str | None = None
    company_name: str | None = None
    inviter_name: str | None = None
    message: str | None = None
    expires_at: datetime | None = None


def _validate_password_complexity(v: str) -> str:
    """AD-011: reusable password complexity check."""
    import re

    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", v):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", v):
        raise ValueError("Password must contain at least one digit")
    if not re.search(r"[^A-Za-z0-9]", v):
        raise ValueError("Password must contain at least one special character")
    return v


class AcceptInvitationRequest(BaseModel):
    """Request to accept an invitation"""

    token: str
    username: str = Field(..., min_length=3, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=100)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return _validate_password_complexity(v)


class ForgotPasswordRequest(BaseModel):
    """Request for password reset instructions."""

    identifier: str = Field(..., min_length=1, max_length=255, description="Username or email")


class ResetPasswordRequest(BaseModel):
    """Request body for completing a password reset."""

    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return _validate_password_complexity(v)


def _run_async_email(coro):
    """Execute async email calls from sync endpoints/background tasks."""
    try:
        asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(coro)
        finally:
            loop.close()


def _send_password_reset_email_task(to_email: str, reset_url: str, expires_minutes: int) -> None:
    _run_async_email(
        email_service.send_password_reset(
            to_email=to_email,
            reset_url=reset_url,
            expires_minutes=expires_minutes,
        )
    )


def _send_email_verification_task(
    to_email: str, verification_url: str, expires_minutes: int
) -> None:
    _run_async_email(
        email_service.send_email_verification(
            to_email=to_email,
            verification_url=verification_url,
            expires_minutes=expires_minutes,
        )
    )


def _rate_limited_response(detail: str, retry_after: int) -> JSONResponse:
    """Standardized auth rate-limit response payload."""
    safe_retry_after = max(int(retry_after), 1)
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": detail,
            "error_code": "RATE_LIMITED",
            "retry_after": safe_retry_after,
        },
        headers={"Retry-After": str(safe_retry_after)},
    )


def _is_e2e_bypass_request(request: Request) -> bool:
    """Allow bypassing auth-rate limits for explicit E2E traffic only in test environments."""
    # AD-014: restrict to explicit test/development envs
    if settings.APP_ENV.lower() not in ("test", "testing", "development"):
        return False
    return request.headers.get("x-e2e-test", "").strip() == "1"


def _set_refresh_cookie(response: JSONResponse, refresh_token: str | None) -> None:
    """AD-004: Set httpOnly refresh-token cookie for cookie-based session persistence."""
    if refresh_token:
        is_prod = settings.APP_ENV.lower() == "production"
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=is_prod,
            samesite="lax",
            path="/api/v1/auth/refresh",
            max_age=7 * 24 * 60 * 60,  # 7 days
        )
    else:
        response.delete_cookie(key="refresh_token", path="/api/v1/auth/refresh")


def _token_json_response(token_response: TokenResponse) -> JSONResponse:
    """Return token JSON with httpOnly refresh cookie set."""
    body = token_response.model_dump()
    resp = JSONResponse(content=body)
    _set_refresh_cookie(resp, token_response.refresh_token)
    return resp


@router.post("/auth/login", response_model=TokenResponse)
def login(
    credentials: LoginRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Login with username and password.

    Returns JWT access token and refresh token.
    """
    client_ip = get_client_ip(request)
    username = (credentials.username or "").strip()

    if settings.RATE_LIMIT_ENABLED and not _is_e2e_bypass_request(request):
        allowed, retry_after = AuthRateLimitService.check_and_record_login(client_ip, username)
        if not allowed:
            return _rate_limited_response(
                "Too many login attempts. Please try again later.",
                retry_after,
            )

    try:
        token_response = auth_service.login(
            credentials.username,
            credentials.password,
            client_ip=client_ip,
            user_agent=request.headers.get("user-agent"),
        )
    except DomainError as exc:
        if (
            settings.RATE_LIMIT_ENABLED
            and not _is_e2e_bypass_request(request)
            and exc.status_code == status.HTTP_401_UNAUTHORIZED
        ):
            retry_after = AuthRateLimitService.finalize_failed_login_attempt(client_ip, username)
            if retry_after > 0:
                return _rate_limited_response(
                    "Too many login attempts. Please try again later.",
                    retry_after,
                )
        raise

    if settings.RATE_LIMIT_ENABLED and not _is_e2e_bypass_request(request):
        AuthRateLimitService.record_login_success(client_ip, username)

    # AD-004: set httpOnly refresh cookie alongside JSON response
    return _token_json_response(token_response)


@router.post("/auth/forgot-password", response_model=MessageResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    auth_service: AuthService = Depends(get_auth_service),
    _db: Session = Depends(get_db),
):
    """
    Request password reset instructions.

    The response is intentionally generic to avoid user enumeration.
    """
    client_ip = get_client_ip(request)
    identifier = payload.identifier.strip()

    if settings.RATE_LIMIT_ENABLED and not _is_e2e_bypass_request(request):
        allowed, retry_after = AuthRateLimitService.check_and_record_forgot_password(
            client_ip, identifier
        )
        if not allowed:
            return _rate_limited_response(
                "Too many password reset requests. Please try again later.",
                retry_after,
            )
        retry_after = AuthRateLimitService.finalize_forgot_password_attempt(
            client_ip, identifier
        )
        if retry_after > 0:
            return _rate_limited_response(
                "Too many password reset requests. Please try again later.",
                retry_after,
            )

    reset_payload = auth_service.request_password_reset(identifier)
    if reset_payload is not None:
        recipient_email, reset_token = reset_payload
        reset_url = f"{settings.BASE_URL}/reset-password?token={quote(reset_token)}"
        background_tasks.add_task(
            _send_password_reset_email_task,
            recipient_email,
            reset_url,
            settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
        )

    return MessageResponse(
        message="If an account exists for that identifier, reset instructions will be sent."
    )


@router.post("/auth/reset-password", response_model=MessageResponse)
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Complete password reset using a one-time token."""
    client_ip = get_client_ip(request)

    if settings.RATE_LIMIT_ENABLED and not _is_e2e_bypass_request(request):
        allowed, retry_after = AuthRateLimitService.check_and_record_reset_password(client_ip)
        if not allowed:
            return _rate_limited_response(
                "Too many password reset attempts. Please try again later.",
                retry_after,
            )

    try:
        auth_service.reset_password(payload.token, payload.new_password)
    except DomainError:
        if settings.RATE_LIMIT_ENABLED and not _is_e2e_bypass_request(request):
            retry_after = AuthRateLimitService.finalize_reset_password_attempt(client_ip)
            if retry_after > 0:
                return _rate_limited_response(
                    "Too many password reset attempts. Please try again later.",
                    retry_after,
                )
        raise

    if settings.RATE_LIMIT_ENABLED and not _is_e2e_bypass_request(request):
        AuthRateLimitService.record_reset_password_success(client_ip)

    return MessageResponse(message="Password has been reset successfully")


@router.post("/auth/refresh", response_model=TokenResponse)
def refresh_token(
    token_data: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
    refresh_token_cookie: str | None = Cookie(None, alias="refresh_token"),
):
    """
    Refresh access token using refresh token.

    The refresh token can be provided in the request body or via an httpOnly cookie.
    Returns new JWT access token (with httpOnly cookie updated).
    """
    # AD-004 / M-06: prefer httpOnly cookie over body (cookie is immune to XSS)
    rt = refresh_token_cookie or token_data.refresh_token
    if not rt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )
    result = auth_service.refresh_access_token(rt)
    return _token_json_response(result)


@router.post("/auth/logout", response_model=MessageResponse)
def logout(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Logout the current session and clear the refresh cookie.
    """
    auth_service.logout(current_user.id, session_id=getattr(request.state, "current_session_id", None))
    resp = JSONResponse(content={"message": "Logged out successfully"})
    # AD-004: clear httpOnly refresh cookie
    resp.delete_cookie(key="refresh_token", path="/api/v1/auth/refresh")
    return resp


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: PublicRegistrationRequest,
    background_tasks: BackgroundTasks,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Register a new user (public self-registration).

    All self-registered users are assigned the ``customer`` role
    regardless of the payload.  Staff accounts are created through
    invitation acceptance or admin user-management flows only.
    """
    user = auth_service.register(user_data)
    verification_token = auth_service.issue_email_verification_token(user)
    verification_url = (
        f"{settings.BASE_URL}{settings.API_PREFIX}/auth/verify-email?token={quote(verification_token)}"
    )
    background_tasks.add_task(
        _send_email_verification_task,
        user.email,
        verification_url,
        settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES,
    )
    return user


@router.get("/auth/verify-email", response_model=MessageResponse)
def verify_email(
    token: str,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Verify account email using token sent at registration."""
    auth_service.verify_email(token)
    return MessageResponse(message="Email verified successfully")


@router.get("/auth/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    permissions = sorted((permission.value for permission in get_user_permissions(current_user)))
    return UserResponse.model_validate(current_user).model_copy(update={"permissions": permissions})


@router.get("/auth/permissions-matrix")
def get_permissions_matrix(current_user: User = Depends(get_current_active_user)):
    """Return the role→permissions matrix so the frontend can align UI guards."""
    return {
        role.value: sorted(p.value for p in perms)
        for role, perms in _STATIC_ROLE_PERMISSIONS.items()
    }


@router.post("/auth/change-password", response_model=MessageResponse)
def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Change current user's password"""
    auth_service.change_password(
        current_user,
        password_data.old_password,
        password_data.new_password,
    )
    return MessageResponse(message="Password changed successfully")


# ========== Invitation Endpoints (Public - No Auth) ==========


@router.get("/auth/invitation/{token}", response_model=InvitationValidateResponse)
def validate_invitation(token: str, db: Session = Depends(get_db)):
    """
    Validate an invitation token.

    This is a public endpoint - no authentication required.
    Returns invitation details if valid.
    """
    invitation_repository = InvitationRepository(db)
    user_repository = UserRepository(db)

    invitation = invitation_repository.get_by_token(token)

    if not invitation:
        return InvitationValidateResponse(valid=False)

    # Check if expired
    if invitation.expires_at < datetime.utcnow():
        invitation.status = InvitationStatus.EXPIRED
        db.commit()
        return InvitationValidateResponse(valid=False)

    # Check if already accepted or cancelled
    if invitation.status != InvitationStatus.PENDING:
        return InvitationValidateResponse(valid=False)

    # Get inviter info
    inviter = user_repository.get_by_id(invitation.invited_by)
    inviter_name = inviter.full_name if inviter else "Unknown"

    # Get company name
    company_name = None
    if invitation.tenant_id:
        from app.models import Tenant

        tenant = db.query(Tenant).filter(Tenant.id == invitation.tenant_id).first()
        if tenant:
            company_name = tenant.name

    return InvitationValidateResponse(
        valid=True,
        email=invitation.email,
        role=invitation.role.value,
        company_name=company_name,
        inviter_name=inviter_name,
        message=invitation.message,
        expires_at=invitation.expires_at,
    )


@router.post("/auth/invitation/accept", response_model=TokenResponse)
def accept_invitation(
    request: AcceptInvitationRequest,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Accept an invitation and create a new user account.

    This is a public endpoint - no authentication required.
    Returns JWT tokens for immediate login after account creation.
    """
    invitation_repository = InvitationRepository(db)
    user_repository = UserRepository(db)

    # C-09: Lock the invitation row during acceptance so two concurrent
    # accept requests cannot both consume the same pending invitation.
    invitation = invitation_repository.get_by_token_for_update(request.token)

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invitation token"
        )

    # Check if expired
    if invitation.expires_at < datetime.utcnow():
        invitation.status = InvitationStatus.EXPIRED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="This invitation has expired"
        )

    # Check if already accepted
    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invitation has already been used or cancelled",
        )

    # Check for company drift - company may have been deactivated since invitation
    if invitation.role == UserRole.CUSTOMER and invitation.tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == invitation.tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The company for this invitation no longer exists",
                headers={"X-Error-Code": "invitation_company_deleted"},
            )
        if not tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The company for this invitation has been deactivated",
                headers={"X-Error-Code": "invitation_company_inactive"},
            )

    # Check if email is already registered
    if user_repository.get_by_email(invitation.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_INVITATION_ACCEPT_CONFLICT_DETAIL,
        )

    # Check if username is taken
    if user_repository.get_by_username(request.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_INVITATION_ACCEPT_CONFLICT_DETAIL,
        )

    # Create user
    user = User(
        email=invitation.email,
        username=request.username,
        full_name=request.full_name,
        hashed_password=get_password_hash(request.password),
        role=invitation.role,
        tenant_id=invitation.tenant_id,
        is_active=True,
        is_email_verified=True,
    )
    db.add(user)
    db.flush()  # Get user ID

    # Update invitation
    invitation.status = InvitationStatus.ACCEPTED
    invitation.accepted_at = datetime.utcnow()
    invitation.created_user_id = user.id

    db.commit()
    db.refresh(user)
    write_audit_log(
        user_id=user.id,
        action=ActionType.CREATE,
        details=json.dumps(
            {
                "event": "invitation_accepted",
                "invitation_id": invitation.id,
                "email": invitation.email,
                "role": invitation.role.value,
                "tenant_id": invitation.tenant_id,
                "created_user_id": user.id,
            }
        ),
    )

    # Generate tokens for immediate login
    # AD-004: use _token_json_response to set httpOnly refresh cookie (FIX-015)
    token_response = auth_service.login(request.username, request.password)
    return _token_json_response(token_response)


# ========== Collaboration Token Endpoint ==========


class CollabTokenRequest(BaseModel):
    """Request for a collaboration token"""

    document_id: int


class CollabTokenResponse(BaseModel):
    """Response containing the collaboration token"""

    token: str
    document_id: int
    permissions: list[str]
    websocket_url: str
    expires_in: int  # seconds


@router.post("/auth/collab-token", response_model=CollabTokenResponse)
def get_collab_token(
    request: CollabTokenRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    collab_service: CollaborationService = Depends(get_collaboration_service),
):
    """
    Get a collaboration token for real-time document editing.

    This token is used to authenticate with the Hocuspocus WebSocket server.
    It contains the user's permissions for the specific document.
    """
    from app.models import Document

    # Get the document
    document = db.query(Document).filter(Document.id == request.document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Check permissions — require at least read access
    permissions = collab_service.get_user_permissions_for_document(current_user, document)
    if not permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this document",
        )

    # Create the collaboration token
    token = collab_service.issue_collab_token(
        user=current_user,
        document_id=request.document_id,
        permissions=permissions,
    )

    # Get WebSocket URL from config — convert http(s) to ws(s)
    collab_base = settings.COLLAB_SERVER_URL
    if collab_base.startswith("https://"):
        ws_base = "wss://" + collab_base[len("https://"):]
    elif collab_base.startswith("http://"):
        ws_base = "ws://" + collab_base[len("http://"):]
    else:
        ws_base = collab_base
    websocket_url = f"{ws_base.rstrip('/')}/document/{request.document_id}"

    return CollabTokenResponse(
        token=token,
        document_id=request.document_id,
        permissions=permissions,
        websocket_url=websocket_url,
        expires_in=3600,  # 1 hour
    )
