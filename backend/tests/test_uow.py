"""Unit tests for UnitOfWork transaction helper."""

import pytest

from app.models import User, UserRole
from app.security import get_password_hash
from app.services.uow import UnitOfWork


def _build_user(username: str, email: str) -> User:
    return User(
        username=username,
        email=email,
        full_name=f"User {username}",
        hashed_password=get_password_hash("password123"),
        role=UserRole.EDITOR,
        is_active=True,
    )


def test_uow_commits_on_context_exit(db):
    with UnitOfWork(db):
        db.add(_build_user("uow_commit", "uow_commit@example.com"))

    persisted = db.query(User).filter(User.username == "uow_commit").first()
    assert persisted is not None


def test_uow_rolls_back_on_exception(db):
    with pytest.raises(RuntimeError):
        with UnitOfWork(db):
            db.add(_build_user("uow_rollback_exc", "uow_rollback_exc@example.com"))
            raise RuntimeError("boom")

    persisted = db.query(User).filter(User.username == "uow_rollback_exc").first()
    assert persisted is None


def test_uow_allows_explicit_rollback(db):
    with UnitOfWork(db) as uow:
        db.add(_build_user("uow_manual_rb", "uow_manual_rb@example.com"))
        uow.rollback()

    persisted = db.query(User).filter(User.username == "uow_manual_rb").first()
    assert persisted is None

