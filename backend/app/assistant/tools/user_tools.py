"""User management assistant tools."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.assistant.tools.base import BaseTool
from app.models import User, UserRole
from app.services.permissions import Permission


class ListUsersTool(BaseTool):
    name = "list_users"
    description = "List users with optional filters by role, active status, or search term."
    parameters = {
        "type": "object",
        "properties": {
            "role": {
                "type": "string",
                "description": "Filter by role",
                "enum": ["system_admin", "admin", "manager", "editor", "viewer", "customer"],
            },
            "is_active": {"type": "boolean", "description": "Filter by active status"},
            "search": {"type": "string", "description": "Search by username or email"},
            "limit": {"type": "integer", "description": "Max results (default 20)"},
        },
        "required": [],
    }
    required_permission = Permission.MANAGE_USERS

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        limit = min(params.get("limit", 20), 100)
        query = db.query(User)

        if tenant_id is not None:
            query = query.filter(User.tenant_id == tenant_id)
        if params.get("role"):
            query = query.filter(User.role == params["role"])
        if params.get("is_active") is not None:
            query = query.filter(User.is_active == params["is_active"])
        if params.get("search"):
            s = params["search"]
            query = query.filter(
                (User.username.ilike(f"%{s}%")) | (User.email.ilike(f"%{s}%"))
            )

        users = query.order_by(User.id).limit(limit).all()
        if not users:
            return {"success": True, "result": "No users found matching the filters."}

        lines = [f"Found {len(users)} user(s):"]
        for u in users:
            status = "active" if u.is_active else "inactive"
            lines.append(f"- [{u.id}] {u.username} ({u.email}) — {u.role} — {status}")
        return {"success": True, "result": "\n".join(lines)}


class GetUserTool(BaseTool):
    name = "get_user"
    description = "Get detailed information about a specific user by their ID."
    parameters = {
        "type": "object",
        "properties": {
            "user_id": {"type": "integer", "description": "The user ID"},
        },
        "required": ["user_id"],
    }
    required_permission = Permission.MANAGE_USERS

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        target = db.query(User).filter(User.id == params["user_id"]).first()
        if target is None:
            return {"success": False, "result": "", "error": "User not found."}
        if tenant_id is not None and target.tenant_id != tenant_id:
            return {"success": False, "result": "", "error": "User not found."}

        info = (
            f"Username: {target.username}\n"
            f"Email: {target.email}\n"
            f"Full Name: {target.full_name}\n"
            f"Role: {target.role}\n"
            f"Active: {target.is_active}\n"
            f"Tenant ID: {target.tenant_id}\n"
            f"Created: {target.created_at}\n"
            f"Last Login: {target.last_login_at}"
        )
        return {"success": True, "result": info}


class CreateUserTool(BaseTool):
    name = "create_user"
    description = "Create a new user account with username, email, full name, role, and password."
    parameters = {
        "type": "object",
        "properties": {
            "username": {"type": "string", "description": "Unique username"},
            "email": {"type": "string", "description": "Email address"},
            "full_name": {"type": "string", "description": "Full name"},
            "role": {
                "type": "string",
                "description": "User role",
                "enum": ["admin", "manager", "editor", "viewer", "customer"],
            },
            "password": {"type": "string", "description": "Initial password (min 8 chars)"},
        },
        "required": ["username", "email", "full_name", "role", "password"],
    }
    required_permission = Permission.MANAGE_USERS

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        from app.security import get_password_hash

        # Prevent creating users with higher privilege
        target_role = UserRole(params["role"])
        caller_role = UserRole(user.role)
        if caller_role != UserRole.SYSTEM_ADMIN and target_role in (UserRole.SYSTEM_ADMIN, UserRole.ADMIN):
            return {"success": False, "result": "", "error": "You cannot create users with a higher role than your own."}

        # Check uniqueness
        if db.query(User).filter(User.username == params["username"]).first():
            return {"success": False, "result": "", "error": f"Username '{params['username']}' already exists."}
        if db.query(User).filter(User.email == params["email"]).first():
            return {"success": False, "result": "", "error": f"Email '{params['email']}' already exists."}

        new_user = User(
            username=params["username"],
            email=params["email"],
            full_name=params["full_name"],
            role=target_role,
            hashed_password=get_password_hash(params["password"]),
            tenant_id=tenant_id,
            is_active=True,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {"success": True, "result": f"User '{new_user.username}' created (ID: {new_user.id}, role: {new_user.role})."}


class DeactivateUserTool(BaseTool):
    name = "deactivate_user"
    description = "Deactivate a user account. The user will no longer be able to log in."
    parameters = {
        "type": "object",
        "properties": {
            "user_id": {"type": "integer", "description": "The user ID to deactivate"},
        },
        "required": ["user_id"],
    }
    required_permission = Permission.MANAGE_USERS
    confirm_before_execute = True

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        target = db.query(User).filter(User.id == params["user_id"]).first()
        if target is None:
            return {"success": False, "result": "", "error": "User not found."}
        if tenant_id is not None and target.tenant_id != tenant_id:
            return {"success": False, "result": "", "error": "User not found."}
        if target.id == user.id:
            return {"success": False, "result": "", "error": "You cannot deactivate yourself."}

        target.is_active = False
        db.commit()
        return {"success": True, "result": f"User '{target.username}' (ID: {target.id}) has been deactivated."}


class ChangeUserRoleTool(BaseTool):
    name = "change_user_role"
    description = "Change a user's role. Enforces role hierarchy — you cannot promote above your own level."
    parameters = {
        "type": "object",
        "properties": {
            "user_id": {"type": "integer", "description": "The user ID"},
            "new_role": {
                "type": "string",
                "description": "The new role",
                "enum": ["admin", "manager", "editor", "viewer", "customer"],
            },
        },
        "required": ["user_id", "new_role"],
    }
    required_permission = Permission.MANAGE_USERS

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        target = db.query(User).filter(User.id == params["user_id"]).first()
        if target is None:
            return {"success": False, "result": "", "error": "User not found."}
        if tenant_id is not None and target.tenant_id != tenant_id:
            return {"success": False, "result": "", "error": "User not found."}

        new_role = UserRole(params["new_role"])
        caller_role = UserRole(user.role)
        if caller_role != UserRole.SYSTEM_ADMIN and new_role in (UserRole.SYSTEM_ADMIN, UserRole.ADMIN):
            return {"success": False, "result": "", "error": "You cannot assign a role higher than your own."}

        old_role = target.role
        target.role = new_role
        db.commit()
        return {"success": True, "result": f"User '{target.username}' role changed from {old_role} to {new_role}."}
