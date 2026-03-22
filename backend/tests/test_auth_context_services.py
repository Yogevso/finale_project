"""Auth context service object regression tests."""

import jwt

from app.auth_context import CollaborationAuthService, RefreshTokenService, TokenService
from app.config import settings
from app.models import PasswordReset


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
    assert payload["document_id"] == "88"
    assert payload["permissions"] == ["read", "write"]
