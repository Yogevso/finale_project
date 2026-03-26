"""Auth context service object regression tests."""

import jwt

from app.auth_context import CollaborationAuthService, RefreshTokenService, TokenService
from app.config import settings
from app.models import PasswordReset
from app.services.auth_service import AuthService


def test_token_service_creates_access_token_contract(test_user):
    service = TokenService()

    token = service.create_access_token_for_user(test_user)
    payload = service.verify_token(token)

    assert payload is not None
    assert payload["type"] == "access"
    assert payload["sub"] == str(test_user.id)
    assert payload["username"] == test_user.username
    assert payload["role"] == test_user.role.value
    assert payload["tenant_id"] == test_user.tenant_id


def test_token_service_rejects_collaboration_token(test_user):
    access_service = TokenService()
    collab_service = CollaborationAuthService()

    token = collab_service.create_collab_token(
        user=test_user,
        document_id=88,
        permissions=["read", "write"],
    )

    assert access_service.verify_token(token) is None


def test_refresh_token_service_issues_and_finds_record(db, test_user):
    service = RefreshTokenService(db)

    refresh_token, expires_at = service.issue_refresh_token(test_user.id)
    record = service.find_valid_record(refresh_token)

    assert record is not None
    assert record.user_id == test_user.id
    assert record.used_at is None
    # Compare without timezone info — SQLite stores naive datetimes
    assert record.expires_at.replace(tzinfo=None) == expires_at.replace(tzinfo=None)


def test_refresh_token_service_invalidates_user_tokens(db, test_user):
    service = RefreshTokenService(db)

    service.issue_refresh_token(test_user.id)
    service.issue_refresh_token(test_user.id)
    service.invalidate_user_tokens(test_user.id)

    records = db.query(PasswordReset).filter(PasswordReset.user_id == test_user.id).all()
    assert len(records) == 2
    assert all(record.used_at is not None for record in records)


def test_auth_service_login_defers_refresh_token_commit(db, test_user):
    class RecordingRefreshTokenService(RefreshTokenService):
        def __init__(self, db):
            super().__init__(db)
            self.commit_flags: list[bool] = []

        def issue_refresh_token(
            self,
            user_id: int,
            *,
            session_identifier: str | None = None,
            commit: bool = True,
        ):
            self.commit_flags.append(commit)
            return super().issue_refresh_token(
                user_id,
                session_identifier=session_identifier,
                commit=commit,
            )

    refresh_service = RecordingRefreshTokenService(db)
    service = AuthService(db, refresh_token_service=refresh_service)

    token_response = service.login(test_user.username, "testpass123")

    assert token_response.refresh_token
    assert refresh_service.commit_flags == [False]


def test_collaboration_auth_service_creates_token_contract(test_user):
    service = CollaborationAuthService()

    token = service.create_collab_token(
        user=test_user,
        document_id=88,
        permissions=["read", "write"],
    )
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    assert payload["type"] == "collaboration"
    assert payload["sub"] == str(test_user.id)
    assert payload["username"] == test_user.username
    assert payload["email"] == test_user.email
    assert payload["tenant_id"] == test_user.tenant_id
    assert payload["document_id"] == "88"
    assert payload["permissions"] == ["read", "write"]
    assert isinstance(payload["trace_id"], str)
    assert payload["trace_id"]


def test_collaboration_auth_service_rejects_access_token(test_user):
    access_service = TokenService()
    collab_service = CollaborationAuthService()

    token = access_service.create_access_token_for_user(test_user)

    assert collab_service.verify_collab_token(token) is None


def test_token_service_accepts_previous_secret_during_rotation(test_user):
    service = TokenService(secret_key="n" * 32, legacy_secret_key="o" * 32)
    token = jwt.encode(
        {
            "sub": str(test_user.id),
            "username": test_user.username,
            "role": test_user.role.value,
            "tenant_id": test_user.tenant_id,
            "type": "access",
        },
        "o" * 32,
        algorithm=settings.ALGORITHM,
    )

    payload = service.verify_token(token)

    assert payload is not None
    assert payload["sub"] == str(test_user.id)


def test_collaboration_auth_service_accepts_previous_secret_during_rotation(test_user):
    service = CollaborationAuthService(secret_key="n" * 32, legacy_secret_key="o" * 32)
    token = jwt.encode(
        {
            "sub": str(test_user.id),
            "username": test_user.username,
            "email": test_user.email,
            "tenant_id": test_user.tenant_id,
            "document_id": "88",
            "permissions": ["read"],
            "type": "collaboration",
        },
        "o" * 32,
        algorithm=settings.ALGORITHM,
    )

    payload = service.verify_collab_token(token)

    assert payload is not None
    assert payload["document_id"] == "88"
