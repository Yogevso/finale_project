"""Authentication API Routes"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.schemas import (
    LoginRequest,
    MessageResponse,
    PasswordChange,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from app.security import get_current_active_user
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/auth/login", response_model=TokenResponse)
def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login with username and password.

    Returns JWT access token and refresh token.
    """
    return AuthService.login(db, credentials.username, credentials.password)


@router.post("/auth/refresh", response_model=TokenResponse)
def refresh_token(
    token_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.

    Returns new JWT access token.
    """
    return AuthService.refresh_access_token(db, token_data.refresh_token)


@router.post("/auth/logout", response_model=MessageResponse)
def logout(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Logout user and invalidate all refresh tokens.
    """
    AuthService.logout(db, current_user.id)
    return MessageResponse(message="Logged out successfully")


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user.

    Only admins can set role other than viewer (enforced in frontend).
    """
    return AuthService.register(db, user_data)


@router.get("/auth/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information"""
    return current_user


@router.post("/auth/change-password", response_model=MessageResponse)
def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change current user's password"""
    AuthService.change_password(
        db,
        current_user,
        password_data.old_password,
        password_data.new_password
    )
    return MessageResponse(message="Password changed successfully")
