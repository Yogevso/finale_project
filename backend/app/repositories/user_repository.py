"""Repository for user aggregate access patterns."""

from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from app.models import User, UserRole
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """User persistence/query access."""

    def query(self):
        return self.db.query(User)

    def query_with_tenant(self):
        return self.query().options(joinedload(User.tenant))

    def get_by_id(self, user_id: int) -> User | None:
        return self.query().filter(User.id == user_id).first()

    def get_by_id_with_tenant(self, user_id: int) -> User | None:
        return self.query_with_tenant().filter(User.id == user_id).first()

    def get_by_username(self, username: str) -> User | None:
        return self.query().filter(User.username == username).first()

    def get_by_email(self, email: str) -> User | None:
        return self.query().filter(User.email == email).first()

    def get_by_email_excluding(self, email: str, exclude_user_id: int) -> User | None:
        return self.query().filter(User.email == email, User.id != exclude_user_id).first()

    def get_by_username_excluding(self, username: str, exclude_user_id: int) -> User | None:
        return self.query().filter(User.username == username, User.id != exclude_user_id).first()

    def list_by_ids(self, user_ids: list[int]) -> list[User]:
        if not user_ids:
            return []
        return self.query().filter(User.id.in_(user_ids)).all()

    def list_for_management(
        self,
        *,
        tenant_id: int | None,
        is_system_admin: bool,
        role: UserRole | None,
        company_id: int | None,
        is_active: bool | None,
        search: str | None,
    ) -> list[User]:
        query = self.query_with_tenant()
        if not is_system_admin:
            query = query.filter(User.tenant_id == tenant_id)
        if role:
            query = query.filter(User.role == role)
        if company_id:
            query = query.filter(User.tenant_id == company_id)
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (User.full_name.ilike(search_term))
                | (User.email.ilike(search_term))
                | (User.username.ilike(search_term))
            )
        return query.order_by(User.created_at.desc()).all()

    def count_other_active_system_admins(self, *, exclude_user_id: int) -> int:
        return self.query().filter(
            User.role == UserRole.SYSTEM_ADMIN,
            User.is_active.is_(True),
            User.id != exclude_user_id,
        ).count()

    def count_other_active_company_admins(
        self,
        *,
        tenant_id: int,
        exclude_user_id: int,
    ) -> int:
        return self.query().filter(
            User.role.in_([UserRole.ADMIN, UserRole.SYSTEM_ADMIN]),
            User.tenant_id == tenant_id,
            User.is_active.is_(True),
            User.id != exclude_user_id,
        ).count()

    def list_active_by_roles(
        self,
        roles: list[UserRole],
        *,
        tenant_id: int | None = None,
        exclude_user_id: int | None = None,
        exclude_user_ids: set[int] | None = None,
    ) -> list[User]:
        query = self.query().filter(
            User.role.in_(roles),
            User.is_active == True,  # noqa: E712
        )
        if tenant_id is not None:
            query = query.filter(
                or_(User.tenant_id == tenant_id, User.role == UserRole.SYSTEM_ADMIN)
            )
        if exclude_user_id is not None:
            query = query.filter(User.id != exclude_user_id)
        if exclude_user_ids:
            query = query.filter(User.id.notin_(exclude_user_ids))
        return query.all()

    def list_active_by_usernames(
        self,
        usernames: list[str],
        *,
        tenant_id: int | None = None,
        exclude_user_id: int | None = None,
        exclude_user_ids: set[int] | None = None,
    ) -> list[User]:
        normalized_usernames = list({username.strip().lower() for username in usernames if username.strip()})
        if not normalized_usernames:
            return []

        query = self.query().filter(
            func.lower(User.username).in_(normalized_usernames),
            User.is_active == True,  # noqa: E712
        )

        if tenant_id is not None:
            query = query.filter(
                or_(User.tenant_id == tenant_id, User.role == UserRole.SYSTEM_ADMIN)
            )

        if exclude_user_id is not None:
            query = query.filter(User.id != exclude_user_id)
        if exclude_user_ids:
            query = query.filter(User.id.notin_(exclude_user_ids))

        return query.all()
