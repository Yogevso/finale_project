"""Authentication Service"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status

from app.config import settings
from app.models import PasswordReset, Tenant, User, UserRole
from app.repositories import UserRepository
from app.schemas import TokenResponse, UserCreate
from app.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from app.services.base_service import SessionService


class AuthService(SessionService):
    """Authentication service"""

    def __init__(self, db):
        super().__init__(db)
        self.user_repository = UserRepository(db)

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
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "username": user.username,
                "role": user.role.value,
                "tenant_id": user.tenant_id,
            },
            expires_delta=access_token_expires,
        )

        # Create refresh token
        refresh_token, expires_at = create_refresh_token(user.id)

        # Store refresh token hash in password_resets table (repurposed for refresh tokens)
        token_hash = get_password_hash(refresh_token)
        refresh_record = PasswordReset(
            user_id=user.id, token_hash=token_hash, expires_at=expires_at
        )
        self.db.add(refresh_record)
        self.db.commit()

        return TokenResponse(
            access_token=access_token, refresh_token=refresh_token, token_type="bearer"
        )

    def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """Generate new access token using refresh token"""
        # Find all non-expired refresh tokens
        now = datetime.utcnow()
        refresh_records = (
            self.db.query(PasswordReset)
            .filter(PasswordReset.expires_at > now, PasswordReset.used_at.is_(None))
            .all()
        )

        # Verify refresh token against stored hashes
        valid_record = None
        for record in refresh_records:
            if verify_password(refresh_token, record.token_hash):
                valid_record = record
                break

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
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "username": user.username,
                "role": user.role.value,
                "tenant_id": user.tenant_id,
            },
            expires_delta=access_token_expires,
        )

        return TokenResponse(access_token=access_token, token_type="bearer")

    def logout(self, user_id: int) -> None:
        """Invalidate all refresh tokens for user"""
        now = datetime.utcnow()
        self.db.query(PasswordReset).filter(
            PasswordReset.user_id == user_id, PasswordReset.used_at.is_(None)
        ).update({"used_at": now})
        self.db.commit()

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
