"""Class-based user management controller."""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies.tenant import TenantContext
from app.models import Invitation, InvitationStatus, Tenant, User, UserRole
from app.schemas import UserCreate, UserUpdate
from app.security import get_password_hash


class UsersController:
    """HTTP-facing orchestration for user management endpoints."""

    ROLE_HIERARCHY = {
        UserRole.SYSTEM_ADMIN: 6,
        UserRole.ADMIN: 5,
        UserRole.MANAGER: 4,
        UserRole.EDITOR: 3,
        UserRole.VIEWER: 2,
        UserRole.CUSTOMER: 1,
    }

    def list_users(
        self,
        *,
        role: Optional[UserRole],
        company_id: Optional[int],
        is_active: Optional[bool],
        search: Optional[str],
        current_user: User,
        tenant_ctx: TenantContext,
        db: Session,
    ) -> list[dict[str, object]]:
        if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.SYSTEM_ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

        query = db.query(User)
        if not tenant_ctx.is_system_admin:
            query = query.filter(User.tenant_id == tenant_ctx.tenant_id)

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

        users = query.order_by(User.created_at.desc()).all()
        return [self._serialize_user(user, db) for user in users]

    def create_user(
        self,
        *,
        user_data: UserCreate,
        current_user: User,
        tenant_ctx: TenantContext,
        db: Session,
    ) -> dict[str, object]:
        if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.SYSTEM_ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

        if not self._can_manage_role(current_user.role, user_data.role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You cannot create users with role '{user_data.role.value}'",
            )

        target_tenant_id = user_data.tenant_id if user_data.tenant_id is not None else tenant_ctx.tenant_id

        if user_data.role == UserRole.CUSTOMER and not target_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customers must be assigned to a company",
            )

        if target_tenant_id is not None:
            tenant = db.query(Tenant).filter(Tenant.id == target_tenant_id).first()
            if not tenant:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
            if not tenant_ctx.is_system_admin and tenant.id != tenant_ctx.tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot assign users to other companies",
                )

        if db.query(User).filter(User.email == user_data.email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
            )
        if db.query(User).filter(User.username == user_data.username).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
            )

        user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=get_password_hash(user_data.password),
            role=user_data.role,
            tenant_id=target_tenant_id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return self._serialize_user(user, db)

    def get_user(
        self,
        *,
        user_id: int,
        current_user: User,
        tenant_ctx: TenantContext,
        db: Session,
    ) -> dict[str, object]:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if user.id != current_user.id:
            if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.SYSTEM_ADMIN]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
                )
            if not tenant_ctx.is_system_admin and user.tenant_id != tenant_ctx.tenant_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        return self._serialize_user(user, db)

    def update_user(
        self,
        *,
        user_id: int,
        user_data: UserUpdate,
        current_user: User,
        tenant_ctx: TenantContext,
        db: Session,
    ) -> dict[str, object]:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        is_self = user.id == current_user.id
        is_admin = current_user.role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.SYSTEM_ADMIN]
        tenant_id_provided = "tenant_id" in user_data.model_fields_set
        has_privileged_update = (
            user_data.role is not None
            or user_data.is_active is not None
            or tenant_id_provided
        )

        if not is_self and not is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
        if has_privileged_update and not is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

        if not is_self and not tenant_ctx.is_system_admin and user.tenant_id != tenant_ctx.tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if is_admin and not is_self and not self._can_manage_role(current_user.role, user.role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify users with higher roles",
            )

        if user_data.email is not None:
            existing = db.query(User).filter(User.email == user_data.email, User.id != user_id).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
                )
            user.email = user_data.email

        if user_data.full_name is not None:
            user.full_name = user_data.full_name

        if user_data.role is not None:
            if not self._can_manage_role(current_user.role, user_data.role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"You cannot assign role '{user_data.role.value}'",
                )
            if is_self and self.ROLE_HIERARCHY.get(user_data.role, 0) < self.ROLE_HIERARCHY.get(
                user.role, 0
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot demote yourself"
                )

            # Role downgrade protection: prevent orphaning admin capabilities
            is_downgrade = self.ROLE_HIERARCHY.get(user_data.role, 0) < self.ROLE_HIERARCHY.get(
                user.role, 0
            )
            if is_downgrade:
                # Prevent downgrading the last system_admin
                if user.role == UserRole.SYSTEM_ADMIN:
                    system_admin_count = db.query(User).filter(
                        User.role == UserRole.SYSTEM_ADMIN,
                        User.is_active.is_(True),
                        User.id != user.id,
                    ).count()
                    if system_admin_count == 0:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Cannot downgrade the last active system admin",
                            headers={"X-Error-Code": "last_system_admin"},
                        )
                # Prevent downgrading the last admin in a tenant (if not a system_admin in the system)
                elif user.role == UserRole.ADMIN and user.tenant_id:
                    # Check if there are other admins or system_admins in the same tenant
                    admin_count = db.query(User).filter(
                        User.role.in_([UserRole.ADMIN, UserRole.SYSTEM_ADMIN]),
                        User.tenant_id == user.tenant_id,
                        User.is_active.is_(True),
                        User.id != user.id,
                    ).count()
                    if admin_count == 0:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Cannot downgrade the last admin for this company",
                            headers={"X-Error-Code": "last_company_admin"},
                        )

            user.role = user_data.role

        if user_data.is_active is not None:
            if is_self and not user_data.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot deactivate yourself"
                )

            # User deactivation cascade: check if last admin and cancel their invitations
            was_active = user.is_active
            is_deactivating = not user_data.is_active and was_active

            if is_deactivating:
                # Prevent deactivating the last system_admin
                if user.role == UserRole.SYSTEM_ADMIN:
                    system_admin_count = db.query(User).filter(
                        User.role == UserRole.SYSTEM_ADMIN,
                        User.is_active.is_(True),
                        User.id != user.id,
                    ).count()
                    if system_admin_count == 0:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Cannot deactivate the last active system admin",
                            headers={"X-Error-Code": "last_system_admin"},
                        )
                # Prevent deactivating the last admin in a tenant
                elif user.role == UserRole.ADMIN and user.tenant_id:
                    admin_count = db.query(User).filter(
                        User.role.in_([UserRole.ADMIN, UserRole.SYSTEM_ADMIN]),
                        User.tenant_id == user.tenant_id,
                        User.is_active.is_(True),
                        User.id != user.id,
                    ).count()
                    if admin_count == 0:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Cannot deactivate the last admin for this company",
                            headers={"X-Error-Code": "last_company_admin"},
                        )

                # Cascade: cancel pending invitations created by this user
                db.query(Invitation).filter(
                    Invitation.invited_by == user.id,
                    Invitation.status == InvitationStatus.PENDING,
                ).update({"status": InvitationStatus.CANCELLED})

            # User reactivation checks
            is_reactivating = user_data.is_active and not was_active
            if is_reactivating:
                # Customer users can only be reactivated if their company is still active
                if user.role == UserRole.CUSTOMER and user.tenant_id:
                    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
                    if not tenant:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Cannot reactivate user: their company no longer exists",
                            headers={"X-Error-Code": "user_company_deleted"},
                        )
                    if not tenant.is_active:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Cannot reactivate user: their company is deactivated",
                            headers={"X-Error-Code": "user_company_inactive"},
                        )

            user.is_active = user_data.is_active

        if tenant_id_provided:
            requested_tenant_id = user_data.tenant_id
            if user.role == UserRole.CUSTOMER and not requested_tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Customers must be assigned to a company",
                )
            if requested_tenant_id:
                tenant = db.query(Tenant).filter(Tenant.id == requested_tenant_id).first()
                if not tenant:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, detail="Company not found"
                    )
                if not tenant.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot assign user to a deactivated company",
                        headers={"X-Error-Code": "company_inactive"},
                    )
                if not tenant_ctx.is_system_admin and requested_tenant_id != tenant_ctx.tenant_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cannot assign users to other companies",
                    )
            elif not tenant_ctx.is_system_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot remove company assignment in this tenant scope",
                )
            user.tenant_id = requested_tenant_id

        if user.role == UserRole.CUSTOMER and not user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customers must be assigned to a company",
            )

        # Role change lifecycle validation: customer role requires active company
        # Only check when user will be active (inactive users don't need this validation)
        if user.is_active and user.role == UserRole.CUSTOMER and user.tenant_id:
            tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot assign customer role: company no longer exists",
                    headers={"X-Error-Code": "role_change_company_deleted"},
                )
            if not tenant.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot assign customer role: company is deactivated",
                    headers={"X-Error-Code": "role_change_company_inactive"},
                )

        db.commit()
        db.refresh(user)
        return self._serialize_user(user, db)

    def delete_user(
        self,
        *,
        user_id: int,
        current_user: User,
        tenant_ctx: TenantContext,
        db: Session,
    ) -> None:
        if current_user.role not in [UserRole.ADMIN, UserRole.SYSTEM_ADMIN]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if not tenant_ctx.is_system_admin and user.tenant_id != tenant_ctx.tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if user.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete yourself"
            )

        if not self._can_manage_role(current_user.role, user.role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete users with higher roles"
            )

        user.is_active = False
        db.commit()

    def check_company_binding(
        self,
        *,
        user_id: int,
        current_user: User,
        tenant_ctx: TenantContext,
        db: Session,
    ) -> dict[str, object]:
        """Check a user's company binding status."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Allow self-access or admin access
        is_self = user.id == current_user.id
        is_admin = current_user.role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.SYSTEM_ADMIN]
        if not is_self and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

        if not tenant_ctx.is_system_admin and user.tenant_id != tenant_ctx.tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        is_customer = user.role == UserRole.CUSTOMER
        requires_company = is_customer  # Customers must have a company

        result: dict[str, object] = {
            "user_id": user.id,
            "role": user.role.value,
            "is_customer": is_customer,
            "requires_company": requires_company,
            "has_company": user.tenant_id is not None,
            "company_id": user.tenant_id,
            "company_name": None,
            "company_slug": None,
            "company_is_active": None,
            "binding_valid": True,
            "binding_issues": [],
        }

        issues = []

        if user.tenant_id:
            tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
            if tenant:
                result["company_name"] = tenant.name
                result["company_slug"] = tenant.slug
                result["company_is_active"] = tenant.is_active
                if not tenant.is_active:
                    issues.append("Company is deactivated")
            else:
                result["company_is_active"] = False
                issues.append("Company no longer exists")
        elif requires_company:
            issues.append("Customer user must be bound to a company")

        result["binding_issues"] = issues
        result["binding_valid"] = len(issues) == 0

        return result

    @classmethod
    def _can_manage_role(cls, manager_role: UserRole, target_role: UserRole) -> bool:
        if manager_role == UserRole.SYSTEM_ADMIN:
            return True
        if manager_role == UserRole.ADMIN:
            return target_role != UserRole.SYSTEM_ADMIN
        if manager_role == UserRole.MANAGER:
            return target_role in [UserRole.EDITOR, UserRole.VIEWER, UserRole.CUSTOMER]
        return False

    @staticmethod
    def _serialize_user(user: User, db: Session) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "tenant_id": user.tenant_id,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "company_name": None,
            "company_slug": None,
        }
        if user.tenant_id:
            tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
            if tenant:
                payload["company_name"] = tenant.name
                payload["company_slug"] = tenant.slug
        return payload
