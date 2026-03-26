"""Shared WebSocket authentication with tenant enforcement (FIX-014)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.auth_context.session_tokens import hash_session_identifier, revoke_session_if_inactive
from app.models import Tenant, User, UserRole, UserSession
from app.security import verify_token


def authenticate_ws(token: str, db: Session) -> User | None:
    """Validate JWT, check session revocation/inactivity, and enforce tenant rules.

    Returns the authenticated ``User`` or ``None`` if any check fails.
    Mirrors the tenant enforcement in ``get_current_active_user`` so that
    WebSocket connections are subject to the same access rules as HTTP.
    """
    payload = verify_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None

    user = db.query(User).filter(User.id == int(user_id), User.is_active.is_(True)).first()
    if not user:
        return None

    # --- Session revocation / inactivity (AD-003) ---
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
            return None
        if revoke_session_if_inactive(user_session, now=now):
            db.commit()
            return None

    # --- Tenant enforcement (FIX-014) ---
    is_customer = user.role == UserRole.CUSTOMER
    is_system_admin = user.role == UserRole.SYSTEM_ADMIN

    if is_customer:
        if user.tenant_id is None:
            return None
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
        if not tenant or not tenant.is_active:
            return None
    elif not is_system_admin and user.tenant_id is not None:
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
        if tenant and not tenant.is_active:
            return None

    return user
