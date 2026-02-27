"""Repository for user aggregate access patterns."""

from __future__ import annotations

from app.models import User, UserRole
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """User persistence/query access."""

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_username(self, username: str) -> User | None:
        return self.db.query(User).filter(User.username == username).first()

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

    def list_by_ids(self, user_ids: list[int]) -> list[User]:
        if not user_ids:
            return []
        return self.db.query(User).filter(User.id.in_(user_ids)).all()

    def list_active_by_roles(
        self,
        roles: list[UserRole],
        exclude_user_id: int | None = None,
        exclude_user_ids: set[int] | None = None,
    ) -> list[User]:
        query = self.db.query(User).filter(
            User.role.in_(roles),
            User.is_active == True,  # noqa: E712
        )
        if exclude_user_id is not None:
            query = query.filter(User.id != exclude_user_id)
        if exclude_user_ids:
            query = query.filter(User.id.notin_(exclude_user_ids))
        return query.all()
