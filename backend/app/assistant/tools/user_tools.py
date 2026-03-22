"""User management assistant tools."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.assistant.tools.base import BaseTool
from app.models import ActionType, AuditLog, User, UserRole
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
            "search": {"type": "string", "description": "Search by username or email", "maxLength": 255},
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
        role = params.get("role")
        if role and role != "null":
            query = query.filter(User.role == role)
        is_active = params.get("is_active")
        if is_active is not None and is_active != "null":
            query = query.filter(User.is_active == is_active)
        search = params.get("search")
        if search and search != "null":
            query = query.filter(
                (User.username.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%"))
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
            f"Created: {target.created_at}"
        )
        return {"success": True, "result": info}


class CreateUserTool(BaseTool):
    name = "create_user"
    description = "Create a new user account with username, email, full name, role, and password."
    parameters = {
        "type": "object",
        "properties": {
            "username": {"type": "string", "description": "Unique username", "maxLength": 100},
            "email": {"type": "string", "description": "Email address", "maxLength": 255},
            "full_name": {"type": "string", "description": "Full name", "maxLength": 255},
            "role": {
                "type": "string",
                "description": "User role",
                "enum": ["admin", "manager", "editor", "viewer", "customer"],
            },
            "password": {"type": "string", "description": "Initial password (min 8 chars)", "maxLength": 100},
        },
        "required": ["username", "email", "full_name", "role", "password"],
    }
    required_permission = Permission.MANAGE_USERS

    async def execute(self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session) -> dict[str, Any]:
        import re
        from app.security import get_password_hash

        # M-08: enforce password complexity
        pwd = params["password"]
        if len(pwd) < 8:
            return {"success": False, "result": "", "error": "Password must be at least 8 characters."}
        if not re.search(r"[A-Z]", pwd) or not re.search(r"[a-z]", pwd) or not re.search(r"\d", pwd) or not re.search(r"[^A-Za-z0-9]", pwd):
            return {"success": False, "result": "", "error": "Password must contain uppercase, lowercase, digit, and special character."}

        # Prevent creating users with higher privilege
        try:
            target_role = UserRole(params["role"])
            caller_role = UserRole(user.role) if not isinstance(user.role, UserRole) else user.role
        except (ValueError, KeyError):
            return {"success": False, "result": "", "error": "Invalid role value."}
        caller_idx = self._ROLE_HIERARCHY.index(caller_role)
        target_idx = self._ROLE_HIERARCHY.index(target_role)
        if target_idx > caller_idx:
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
        # AE-005: Audit trail for AI-initiated user creation
        db.add(AuditLog(
            user_id=user.id,
            action=ActionType.CREATE,
            details=f"Created user '{params['username']}' (role: {params['role']}) via AI assistant",
        ))
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
        # AE-005: Audit trail for AI-initiated user deactivation
        db.add(AuditLog(
            user_id=user.id,
            action=ActionType.UPDATE,
            details=f"Deactivated user '{target.username}' (ID: {target.id}) via AI assistant",
        ))
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

        try:
            new_role = UserRole(params["new_role"])
            caller_role = UserRole(user.role) if not isinstance(user.role, UserRole) else user.role
        except (ValueError, KeyError):
            return {"success": False, "result": "", "error": "Invalid role value."}
        caller_idx = self._ROLE_HIERARCHY.index(caller_role)
        new_role_idx = self._ROLE_HIERARCHY.index(new_role)
        if new_role_idx > caller_idx:
            return {"success": False, "result": "", "error": "You cannot assign a role higher than your own."}

        old_role = target.role
        target.role = new_role
        # AE-005: Audit trail for AI-initiated role change
        db.add(AuditLog(
            user_id=user.id,
            action=ActionType.UPDATE,
            details=f"Changed role for user '{target.username}' from {old_role} to {new_role} via AI assistant",
        ))
        db.commit()
        return {"success": True, "result": f"User '{target.username}' role changed from {old_role} to {new_role}."}
