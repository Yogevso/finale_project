"""Authentication Service"""

from datetime import timedelta
from typing import Optional

from fastapi import HTTPException, status

from app.auth_context import RefreshTokenService, TokenService
from app.config import settings
from app.models import Tenant, User, UserRole
from app.repositories import UserRepository
from app.schemas import TokenResponse, UserCreate
from app.security import get_password_hash, verify_password
from app.services.base_service import SessionService


class AuthService(SessionService):
    """Authentication service"""

    def __init__(
        self,
        db,
        token_service: TokenService | None = None,
        refresh_token_service: RefreshTokenService | None = None,
    ):
        super().__init__(db)
        self.user_repository = UserRepository(db)
        self.token_service = token_service or TokenService()
        self.refresh_token_service = refresh_token_service or RefreshTokenService(db)

    def _ensure_tenant_is_active(self, user: User) -> None:
        """Reject auth flows for users tied to inactive tenants."""
        if user.role == UserRole.SYSTEM_ADMIN or user.tenant_id is None:
            return
        tenant = self.db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
        if tenant and not tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Company is inactive",
            )

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user by username and password"""
        user = self.user_repository.get_by_username(username)

        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        return user

    def login(self, username: str, password: str) -> TokenResponse:
        """Login user and return JWT token with refresh token"""
        user = self.authenticate_user(username, password)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
            )
        self._ensure_tenant_is_active(user)

        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.token_service.create_access_token_for_user(
            user,
            expires_delta=access_token_expires,
        )

        # Create refresh token
        refresh_token, _ = self.refresh_token_service.issue_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token, refresh_token=refresh_token, token_type="bearer"
        )

    def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """Generate new access token using refresh token"""
        valid_record = self.refresh_token_service.find_valid_record(refresh_token)

        if not valid_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get user
        user = self.user_repository.get_by_id(valid_record.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive"
            )
        self._ensure_tenant_is_active(user)

        # Create new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.token_service.create_access_token_for_user(
            user,
            expires_delta=access_token_expires,
        )

        return TokenResponse(access_token=access_token, token_type="bearer")

    def logout(self, user_id: int) -> None:
        """Invalidate all refresh tokens for user"""
        self.refresh_token_service.invalidate_user_tokens(user_id)

    def register(self, user_data: UserCreate) -> User:
        """Register a new user"""
        # Check if username already exists
        existing_user = self.user_repository.get_by_username(user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered"
            )

        # Check if email already exists
        existing_email = self.user_repository.get_by_email(user_data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
            )

        # Create new user
        user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=get_password_hash(user_data.password),
            role=user_data.role,
            is_active=True,
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    def change_password(self, user: User, old_password: str, new_password: str) -> None:
        """Change user password"""
        # Verify old password
        if not verify_password(old_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password"
            )

        # Update password
        user.hashed_password = get_password_hash(new_password)
        self.db.commit()
