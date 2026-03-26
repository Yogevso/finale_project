from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.auth_context.invitation_tokens import hash_invitation_token
from app.models import Invitation, InvitationStatus, UserRole
from app.repositories.invitation_repository import InvitationRepository


def _build_repository_with_query_chain(*, dialect_name: str):
    db = MagicMock()
    db.bind = SimpleNamespace(dialect=SimpleNamespace(name=dialect_name))

    query = MagicMock()
    filtered = MagicMock()
    locked = MagicMock()

    db.query.return_value = query
    query.filter.return_value = filtered
    filtered.with_for_update.return_value = locked

    return db, filtered, locked


def test_get_by_token_for_update_uses_row_lock_outside_sqlite():
    db, filtered, locked = _build_repository_with_query_chain(dialect_name="postgresql")
    locked.first.return_value = "locked-invitation"

    repository = InvitationRepository(db)
    invitation = repository.get_by_token_for_update("token-123")

    assert invitation == "locked-invitation"
    filtered.with_for_update.assert_called_once_with()
    locked.first.assert_called_once_with()
    filtered.first.assert_not_called()


def test_get_by_token_for_update_skips_row_lock_on_sqlite():
    db, filtered, locked = _build_repository_with_query_chain(dialect_name="sqlite")
    filtered.first.return_value = "sqlite-invitation"

    repository = InvitationRepository(db)
    invitation = repository.get_by_token_for_update("token-123")

    assert invitation == "sqlite-invitation"
    filtered.with_for_update.assert_not_called()
    filtered.first.assert_called_once_with()
    locked.first.assert_not_called()


def test_get_by_token_matches_hashed_storage(db, test_admin, default_tenant):
    repository = InvitationRepository(db)
    raw_token = "hashed-repo-token"
    invitation = Invitation(
        email="hashed-repo@example.com",
        token=hash_invitation_token(raw_token),
        role=UserRole.VIEWER,
        tenant_id=default_tenant.id,
        invited_by=test_admin.id,
        status=InvitationStatus.PENDING,
        expires_at=datetime.utcnow() + timedelta(days=1),
    )
    db.add(invitation)
    db.commit()

    loaded = repository.get_by_token(raw_token)

    assert loaded is not None
    assert loaded.id == invitation.id


def test_get_by_token_falls_back_to_legacy_plaintext_storage(db, test_admin, default_tenant):
    repository = InvitationRepository(db)
    raw_token = "legacy-plaintext-token"
    invitation = Invitation(
        email="legacy-repo@example.com",
        token=raw_token,
        role=UserRole.VIEWER,
        tenant_id=default_tenant.id,
        invited_by=test_admin.id,
        status=InvitationStatus.PENDING,
        expires_at=datetime.utcnow() + timedelta(days=1),
    )
    db.add(invitation)
    db.commit()

    loaded = repository.get_by_token(raw_token)

    assert loaded is not None
    assert loaded.id == invitation.id
