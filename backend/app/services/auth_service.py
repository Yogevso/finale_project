"""Authentication Service"""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status

from app.auth_context import RefreshTokenService, TokenService
from app.auth_context.session_tokens import hash_session_identifier
from app.config import settings
from app.models import PasswordReset, SecurityEvent, Tenant, User, UserRole, UserSession
from app.repositories import UserRepository
from app.schemas import PublicRegistrationRequest, TokenResponse, UserCreate
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
            # H-08: Perform dummy work to prevent timing-based user enumeration
            get_password_hash(f"dummy_{secrets.token_urlsafe(16)}")
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
        self.db.add(SecurityEvent(user_id=user.id, event_type="password_reset"))
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

    @staticmethod
    def _normalize_user_agent(user_agent: str | None) -> str | None:
        if user_agent is None:
            return None
        normalized = user_agent.strip()
        if not normalized:
            return None
        return normalized[:512]

    def _record_login_context(
        self,
        *,
        user: User,
        client_ip: str | None,
        user_agent: str | None,
    ) -> None:
        normalized_ip = (client_ip or "").strip() or None
        normalized_user_agent = self._normalize_user_agent(user_agent)

        has_prior_login = bool(user.last_login_ip or user.last_login_user_agent)
        ip_changed = user.last_login_ip != normalized_ip
        user_agent_changed = user.last_login_user_agent != normalized_user_agent

        self.db.add(
            SecurityEvent(
                user_id=user.id,
                event_type="login",
                ip_address=normalized_ip,
                user_agent=normalized_user_agent,
            )
        )

        if has_prior_login and (ip_changed or user_agent_changed):
            self.db.add(
                SecurityEvent(
                    user_id=user.id,
                    event_type="new_device_login",
                    ip_address=normalized_ip,
                    user_agent=normalized_user_agent,
                )
            )

        user.last_login_ip = normalized_ip
        user.last_login_user_agent = normalized_user_agent

    def login(
        self,
        username: str,
        password: str,
        *,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> TokenResponse:
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
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not verify_password(password, user.hashed_password):
            self._record_failed_login_attempt(user, now)
            if self._is_locked(user, datetime.utcnow()):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password",
                    headers={"WWW-Authenticate": "Bearer"},
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

        self._record_login_context(user=user, client_ip=client_ip, user_agent=user_agent)
        session_identifier = secrets.token_urlsafe(32)
        now = datetime.utcnow()

        # AD-013: enforce concurrent session limit — revoke oldest sessions
        max_sessions = settings.MAX_CONCURRENT_SESSIONS
        active_sessions = (
            self.db.query(UserSession)
            .filter(
                UserSession.user_id == user.id,
                UserSession.revoked_at.is_(None),
            )
            .order_by(UserSession.last_active_at.desc())
            .all()
        )
        if len(active_sessions) >= max_sessions:
            # revoke oldest sessions to stay within the limit
            for old_session in active_sessions[max_sessions - 1:]:
                old_session.revoked_at = now

        self.db.add(
            UserSession(
                user_id=user.id,
                session_token_hash=hash_session_identifier(session_identifier),
                ip_address=(client_ip or "").strip() or None,
                user_agent=self._normalize_user_agent(user_agent),
                created_at=now,
                last_active_at=now,
            )
        )

        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.token_service.create_access_token_for_user(
            user,
            expires_delta=access_token_expires,
            session_identifier=session_identifier,
        )

        # Create refresh token
        refresh_token, _ = self.refresh_token_service.issue_refresh_token(
            user.id,
            session_identifier=session_identifier,
        )

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

        # Check if the session associated with this refresh token has been revoked
        session_identifier = self.refresh_token_service.parse_session_identifier(refresh_token)
        if session_identifier:
            session_hash = hash_session_identifier(session_identifier)
            user_session = (
                self.db.query(UserSession)
                .filter(
                    UserSession.user_id == user.id,
                    UserSession.session_token_hash == session_hash,
                )
                .first()
            )
            if user_session is None or user_session.revoked_at is not None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session has been revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        # Create new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.token_service.create_access_token_for_user(
            user,
            expires_delta=access_token_expires,
            session_identifier=session_identifier,
        )

        # M-10: Rotate refresh token — invalidate old, issue new
        valid_record.used_at = datetime.utcnow()
        new_refresh_token, _ = self.refresh_token_service.issue_refresh_token(
            user.id,
            session_identifier=session_identifier,
        )

        return TokenResponse(access_token=access_token, refresh_token=new_refresh_token, token_type="bearer")

    def logout(self, user_id: int) -> None:
        """Invalidate all refresh tokens and revoke all active sessions for user."""
        self.refresh_token_service.invalidate_user_tokens(user_id)
        # AD-020: also revoke all UserSession records so JWTs are rejected
        now = datetime.utcnow()
        active_sessions = (
            self.db.query(UserSession)
            .filter(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
            )
            .all()
        )
        for session in active_sessions:
            session.revoked_at = now
        self.db.commit()

    def register(self, user_data: UserCreate | PublicRegistrationRequest) -> User:
        """Register a new user via public self-registration.

        AF-009: Accepts ``PublicRegistrationRequest`` (no role/tenant_id) or
        legacy ``UserCreate`` — either way, role and tenant_id are ignored.
        All self-registered users land as ``customer`` with no tenant.
        Staff creation goes through admin/invitation flows only.
        """
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

        # AD-001: Force customer role — ignore caller-supplied role/tenant_id
        # Staff users are created via invitation acceptance or admin flows.
        user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=get_password_hash(user_data.password),
            role=UserRole.CUSTOMER,
            tenant_id=None,
            is_active=True,
            is_email_verified=False,
            failed_login_attempts=0,
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    def change_password(self, user: User, old_password: str, new_password: str) -> None:
        """Change user password and invalidate all existing sessions."""
        # Verify old password
        if not verify_password(old_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password"
            )

        # M-11: atomic password change + session revocation in single transaction
        now = datetime.utcnow()

        # Update password
        user.hashed_password = get_password_hash(new_password)
        self.db.add(SecurityEvent(user_id=user.id, event_type="password_changed"))

        # Invalidate all refresh tokens (inline to avoid separate commit)
        self.db.query(PasswordReset).filter(
            PasswordReset.user_id == user.id,
            PasswordReset.used_at.is_(None),
        ).update({"used_at": now})

        # Revoke all active sessions
        self.db.query(UserSession).filter(
            UserSession.user_id == user.id,
            UserSession.revoked_at.is_(None),
        ).update({"revoked_at": now})

        # Single atomic commit
        self.db.commit()
