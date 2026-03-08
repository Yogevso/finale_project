"""Authentication Service"""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status

from app.auth_context import RefreshTokenService, TokenService
from app.config import settings
from app.models import PasswordReset, Tenant, User, UserRole
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

    @staticmethod
    def _is_locked(user: User, now: datetime) -> bool:
        return bool(user.locked_until and user.locked_until > now)

    def _reset_failed_attempts_if_needed(self, user: User) -> None:
        if user.failed_login_attempts != 0 or user.locked_until is not None:
            user.failed_login_attempts = 0
            user.locked_until = None
            self.db.commit()

    def _clear_expired_lock(self, user: User, now: datetime) -> None:
        if user.locked_until and user.locked_until <= now:
            self._reset_failed_attempts_if_needed(user)

    def _record_failed_login_attempt(self, user: User, now: datetime) -> None:
        user.failed_login_attempts = int(user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= settings.ACCOUNT_LOCKOUT_MAX_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=settings.ACCOUNT_LOCKOUT_DURATION_MINUTES)
        self.db.commit()

    def issue_email_verification_token(self, user: User) -> str:
        """Create and persist a one-time email verification token."""
        token = f"ev_{secrets.token_urlsafe(32)}"
        user.email_verification_token_hash = get_password_hash(token)
        user.email_verification_expires_at = datetime.utcnow() + timedelta(
            minutes=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES
        )
        user.is_email_verified = False
        self.db.commit()
        return token

    def verify_email(self, token: str) -> None:
        """Verify a user email by token and mark the account as verified."""
        if not token.startswith("ev_"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token",
            )

        now = datetime.utcnow()
        candidates = (
            self.db.query(User)
            .filter(
                User.email_verification_token_hash.is_not(None),
                User.email_verification_expires_at.is_not(None),
                User.email_verification_expires_at > now,
            )
            .all()
        )

        matched_user: User | None = None
        for candidate in candidates:
            token_hash = candidate.email_verification_token_hash
            if not token_hash:
                continue
            if verify_password(token, token_hash):
                matched_user = candidate
                break

        if matched_user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token",
            )

        matched_user.is_email_verified = True
        matched_user.email_verification_token_hash = None
        matched_user.email_verification_expires_at = None
        self.db.commit()

    def request_password_reset(self, identifier: str) -> tuple[str, str] | None:
        """
        Create a password-reset token for a user matched by email or username.

        Returns `(email, token)` when a user is found; otherwise returns None.
        """
        normalized_identifier = identifier.strip()
        if not normalized_identifier:
            return None

        user = self.user_repository.get_by_email(normalized_identifier)
        if user is None:
            user = self.user_repository.get_by_username(normalized_identifier)

        if user is None or not user.is_active:
            return None

        token = f"pr_{secrets.token_urlsafe(32)}"
        expires_at = datetime.utcnow() + timedelta(
            minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
        )
        reset_record = PasswordReset(
            user_id=user.id,
            token_hash=get_password_hash(token),
            expires_at=expires_at,
        )
        self.db.add(reset_record)
        self.db.commit()

        return user.email, token

    def reset_password(self, token: str, new_password: str) -> None:
        """Apply password reset by one-time reset token."""
        if not token.startswith("pr_"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        now = datetime.utcnow()
        reset_records = (
            self.db.query(PasswordReset)
            .filter(PasswordReset.expires_at > now, PasswordReset.used_at.is_(None))
            .all()
        )

        matched_record: PasswordReset | None = None
        for record in reset_records:
            if verify_password(token, record.token_hash):
                matched_record = record
                break

        if matched_record is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        user = self.user_repository.get_by_id(matched_record.user_id)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        user.hashed_password = get_password_hash(new_password)
        user.failed_login_attempts = 0
        user.locked_until = None

        # Invalidate all outstanding token records (refresh + reset).
        self.db.query(PasswordReset).filter(
            PasswordReset.user_id == user.id,
            PasswordReset.used_at.is_(None),
        ).update({"used_at": now})
        self.db.commit()

    def unlock_user_account(self, user_id: int) -> None:
        """Manually unlock a locked user account."""
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        user.failed_login_attempts = 0
        user.locked_until = None
        self.db.commit()

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
        user = self.user_repository.get_by_username(username)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        now = datetime.utcnow()
        self._clear_expired_lock(user, now)

        if self._is_locked(user, now):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="account_locked",
            )

        if not verify_password(password, user.hashed_password):
            self._record_failed_login_attempt(user, now)
            if self._is_locked(user, datetime.utcnow()):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="account_locked",
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        self._reset_failed_attempts_if_needed(user)

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
            )
        self._ensure_tenant_is_active(user)

        if not user.is_email_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="email_not_verified",
            )

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
            tenant_id=user_data.tenant_id,
            is_active=True,
            is_email_verified=False,
            failed_login_attempts=0,
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
