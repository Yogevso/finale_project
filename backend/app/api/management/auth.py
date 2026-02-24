"""Authentication API Routes"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Invitation, InvitationStatus, User
from app.schemas import (
    LoginRequest,
    MessageResponse,
    PasswordChange,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from app.security import get_current_active_user, get_password_hash
from app.services.auth_rate_limit_service import AuthRateLimitService
from app.services.auth_service import AuthService
from app.services.permissions import get_user_permissions
from app.utils.request_ip import get_client_ip

router = APIRouter()


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


class AcceptInvitationRequest(BaseModel):
    """Request to accept an invitation"""

    token: str
    username: str = Field(..., min_length=3, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=100)


class ForgotPasswordRequest(BaseModel):
    """Request for password reset instructions."""

    identifier: str = Field(..., min_length=1, max_length=255, description="Username or email")


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
    """Allow bypassing auth-rate limits for explicit E2E traffic outside production."""
    if settings.APP_ENV.lower() == "production":
        return False
    return request.headers.get("x-e2e-test", "").strip() == "1"


@router.post("/auth/login", response_model=TokenResponse)
def login(credentials: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """
    Login with username and password.

    Returns JWT access token and refresh token.
    """
    client_ip = get_client_ip(request)
    username = (credentials.username or "").strip()

    if settings.RATE_LIMIT_ENABLED and not _is_e2e_bypass_request(request):
        allowed, retry_after = AuthRateLimitService.check_login_allowed(client_ip, username)
        if not allowed:
            return _rate_limited_response(
                "Too many login attempts. Please try again later.",
                retry_after,
            )

    try:
        token_response = AuthService.login(db, credentials.username, credentials.password)
    except HTTPException as exc:
        if (
            settings.RATE_LIMIT_ENABLED
            and not _is_e2e_bypass_request(request)
            and exc.status_code == status.HTTP_401_UNAUTHORIZED
        ):
            retry_after = AuthRateLimitService.record_login_failure(client_ip, username)
            if retry_after > 0:
                return _rate_limited_response(
                    "Too many login attempts. Please try again later.",
                    retry_after,
                )
        raise

    if settings.RATE_LIMIT_ENABLED and not _is_e2e_bypass_request(request):
        AuthRateLimitService.record_login_success(client_ip, username)

    return token_response


@router.post("/auth/forgot-password", response_model=MessageResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    _db: Session = Depends(get_db),
):
    """
    Request password reset instructions.

    The response is intentionally generic to avoid user enumeration.
    """
    client_ip = get_client_ip(request)
    identifier = payload.identifier.strip()

    if settings.RATE_LIMIT_ENABLED and not _is_e2e_bypass_request(request):
        allowed, retry_after = AuthRateLimitService.check_forgot_password_allowed(
            client_ip, identifier
        )
        if not allowed:
            return _rate_limited_response(
                "Too many password reset requests. Please try again later.",
                retry_after,
            )

        lock_retry_after = AuthRateLimitService.record_forgot_password_request(
            client_ip, identifier
        )
        if lock_retry_after > 0:
            return _rate_limited_response(
                "Too many password reset requests. Please try again later.",
                lock_retry_after,
            )

    return MessageResponse(
        message="If an account exists for that identifier, reset instructions will be sent."
    )


@router.post("/auth/refresh", response_model=TokenResponse)
def refresh_token(token_data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Refresh access token using refresh token.

    Returns new JWT access token.
    """
    return AuthService.refresh_access_token(db, token_data.refresh_token)


@router.post("/auth/logout", response_model=MessageResponse)
def logout(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Logout user and invalidate all refresh tokens.
    """
    AuthService.logout(db, current_user.id)
    return MessageResponse(message="Logged out successfully")


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.

    Only admins can set role other than viewer (enforced in frontend).
    """
    return AuthService.register(db, user_data)


@router.get("/auth/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    permissions = sorted((permission.value for permission in get_user_permissions(current_user)))
    return UserResponse.model_validate(current_user).model_copy(update={"permissions": permissions})


@router.post("/auth/change-password", response_model=MessageResponse)
def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Change current user's password"""
    AuthService.change_password(
        db, current_user, password_data.old_password, password_data.new_password
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
    invitation = db.query(Invitation).filter(Invitation.token == token).first()

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
    inviter = db.query(User).filter(User.id == invitation.invited_by).first()
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
def accept_invitation(request: AcceptInvitationRequest, db: Session = Depends(get_db)):
    """
    Accept an invitation and create a new user account.

    This is a public endpoint - no authentication required.
    Returns JWT tokens for immediate login after account creation.
    """
    invitation = db.query(Invitation).filter(Invitation.token == request.token).first()

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

    # Check if email is already registered
    if db.query(User).filter(User.email == invitation.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="A user with this email already exists"
        )

    # Check if username is taken
    if db.query(User).filter(User.username == request.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="This username is already taken"
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
    )
    db.add(user)
    db.flush()  # Get user ID

    # Update invitation
    invitation.status = InvitationStatus.ACCEPTED
    invitation.accepted_at = datetime.utcnow()
    invitation.created_user_id = user.id

    db.commit()
    db.refresh(user)

    # Generate tokens for immediate login
    return AuthService.login(db, request.username, request.password)


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
):
    """
    Get a collaboration token for real-time document editing.

    This token is used to authenticate with the Hocuspocus WebSocket server.
    It contains the user's permissions for the specific document.
    """
    from app.models import Document
    from app.services.collaboration_service import CollaborationService

    # Get the document
    document = db.query(Document).filter(Document.id == request.document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Check permissions
    permissions = CollaborationService.get_user_permissions(current_user, document)
    if not permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this document",
        )

    # Create the collaboration token
    token = CollaborationService.create_collab_token(
        user=current_user,
        document_id=request.document_id,
        permissions=permissions,
    )

    # Get WebSocket URL from config or default
    websocket_url = f"ws://localhost:8002/document/{request.document_id}"

    return CollabTokenResponse(
        token=token,
        document_id=request.document_id,
        permissions=permissions,
        websocket_url=websocket_url,
        expires_in=3600,  # 1 hour
    )
