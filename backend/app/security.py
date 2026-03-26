"""Security & Authentication Utilities"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth_context.passwords import (
    get_password_hash as _get_password_hash,
)
from app.auth_context.passwords import (
    verify_password as _verify_password,
)
from app.auth_context.refresh_token_service import (
    REFRESH_TOKEN_EXPIRE_DAYS,
    RefreshTokenService,
)
from app.auth_context.session_tokens import hash_session_identifier, revoke_session_if_inactive
from app.auth_context import ACCESS_TOKEN_TYPE
from app.auth_context.token_service import TokenService
from app.config import settings
from app.db import get_db

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/login")

_token_service = TokenService()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return _verify_password(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return _get_password_hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    return _token_service.create_access_token(data, expires_delta=expires_delta)


def create_refresh_token(user_id: int) -> tuple[str, datetime]:
    """Create refresh token - returns (token, expiry)"""
    _ = user_id  # Compatibility argument; refresh token values are user-agnostic.
    return RefreshTokenService.build_refresh_token(
        refresh_token_expire_days=REFRESH_TOKEN_EXPIRE_DAYS
    )


def verify_token(token: str, *, expected_type: str = ACCESS_TOKEN_TYPE) -> Optional[dict]:
    """Verify and decode JWT token"""
    return _token_service.verify_token(token, expected_type=expected_type)


async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Dependency to get current authenticated user"""
    from app.models import User, UserSession  # Import here to avoid circular dependency

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = verify_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception

    session_identifier = payload.get("sid")
    if isinstance(session_identifier, str) and session_identifier.strip():
        now = datetime.utcnow()
        session_hash = hash_session_identifier(session_identifier)
        user_session = (
            db.query(UserSession)
            .filter(
                UserSession.user_id == user.id,
                UserSession.session_token_hash == session_hash,
            )
            .first()
        )
        if user_session is None or user_session.revoked_at is not None:
            raise credentials_exception
        if revoke_session_if_inactive(user_session, now=now):
            db.commit()
            raise credentials_exception

        user_session.last_active_at = now
        db.commit()
        request.state.current_session_hash = session_hash
        request.state.current_session_id = user_session.id
    else:
        request.state.current_session_hash = None
        request.state.current_session_id = None

    # Store user/tenant context for structured logging (Y15-027)
    request.state.user_id = user.id
    request.state.tenant_id = getattr(user, "tenant_id", None)

    return user


async def get_current_active_user(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Dependency to get current active user"""
    from app.models import Tenant, UserRole
    from app.services.permissions import evaluate_role_membership

    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    is_system_admin = evaluate_role_membership(current_user, [UserRole.SYSTEM_ADMIN]).allowed
    is_customer = current_user.role == UserRole.CUSTOMER

    # Customer users MUST have a valid, active company
    if is_customer:
        if current_user.tenant_id is None:
            raise HTTPException(
                status_code=403,
                detail="Customer user must be bound to a company",
                headers={"X-Error-Code": "customer_company_binding_required"},
            )
        tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=403,
                detail="Customer's company no longer exists",
                headers={"X-Error-Code": "customer_company_not_found"},
            )
        if not tenant.is_active:
            raise HTTPException(
                status_code=403,
                detail="Company is inactive",
                headers={"X-Error-Code": "customer_company_inactive"},
            )
    elif not is_system_admin and current_user.tenant_id is not None:
        # Non-customer internal users with inactive company
        tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
        if tenant and not tenant.is_active:
            raise HTTPException(status_code=403, detail="Company is inactive")
    elif not is_system_admin and current_user.tenant_id is None:
        # Non-SYSTEM_ADMIN users must be bound to a tenant
        raise HTTPException(
            status_code=403,
            detail="User must be assigned to a company",
            headers={"X-Error-Code": "tenant_binding_required"},
        )

    # Inject tenant context for request-scoped tenant isolation
    from app.middleware.tenant_context import inject_tenant_context
    inject_tenant_context(current_user)
    
    return current_user


# Re-export permission dependencies for convenience
