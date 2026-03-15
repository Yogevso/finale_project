"""Tests for the AI assistant user management tools."""

import asyncio
import pytest
from unittest.mock import MagicMock

from app.assistant.tools.user_tools import (
    ChangeUserRoleTool,
    CreateUserTool,
    DeactivateUserTool,
    GetUserTool,
    ListUsersTool,
)
from app.models import UserRole
from tests.factories import create_user


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user_obj(db, role=UserRole.ADMIN, tenant_id=None, **kw):
    defaults = dict(
        email=f"{role.value}@tools.test",
        username=f"tool_{role.value}",
        full_name=f"Tool {role.value}",
        plain_password="pass123",
        role=role,
        is_active=True,
    )
    defaults.update(kw)
    if tenant_id is not None:
        defaults["tenant_id"] = tenant_id
    return create_user(db, **defaults)


# ---------------------------------------------------------------------------
# ListUsersTool
# ---------------------------------------------------------------------------

class TestListUsersTool:
    def test_list_all_users(self, db):
        caller = _make_user_obj(db, UserRole.SYSTEM_ADMIN, email="sa@t.test", username="sa_list")
        _make_user_obj(db, UserRole.EDITOR, email="e1@t.test", username="e1_list")
        _make_user_obj(db, UserRole.VIEWER, email="v1@t.test", username="v1_list")

        tool = ListUsersTool()
        result = _run(tool.execute(caller, tenant_id=None, params={}, db=db))
        assert result["success"] is True
        assert "e1_list" in result["result"]
        assert "v1_list" in result["result"]

    def test_list_users_with_limit(self, db):
        caller = _make_user_obj(db, UserRole.SYSTEM_ADMIN, email="sa2@t.test", username="sa_lim")
        for i in range(5):
            _make_user_obj(db, UserRole.EDITOR, email=f"lim{i}@t.test", username=f"lim_{i}")

        tool = ListUsersTool()
        result = _run(tool.execute(caller, tenant_id=None, params={"limit": 2}, db=db))
        assert result["success"] is True
        assert "user(s)" in result["result"].lower() or "found" in result["result"].lower()

    def test_list_users_no_results(self, db):
        caller = _make_user_obj(db, UserRole.SYSTEM_ADMIN, email="sa3@t.test", username="sa_empty")

        tool = ListUsersTool()
        result = _run(tool.execute(caller, tenant_id=None, params={"search": "zzzznonexistent"}, db=db))
        assert result["success"] is True
        assert "no users" in result["result"].lower()

    def test_list_users_filter_by_role(self, db):
        caller = _make_user_obj(db, UserRole.SYSTEM_ADMIN, email="sa4@t.test", username="sa_role")
        _make_user_obj(db, UserRole.EDITOR, email="ef@t.test", username="editor_filter")
        _make_user_obj(db, UserRole.VIEWER, email="vf@t.test", username="viewer_filter")

        tool = ListUsersTool()
        result = _run(tool.execute(caller, tenant_id=None, params={"role": "editor"}, db=db))
        assert result["success"] is True
        assert "editor_filter" in result["result"]
        assert "viewer_filter" not in result["result"]


# ---------------------------------------------------------------------------
# GetUserTool
# ---------------------------------------------------------------------------

class TestGetUserTool:
    def test_get_existing_user(self, db):
        caller = _make_user_obj(db, UserRole.SYSTEM_ADMIN, email="sa5@t.test", username="sa_get")
        target = _make_user_obj(db, UserRole.EDITOR, email="gt@t.test", username="get_target")

        tool = GetUserTool()
        result = _run(tool.execute(caller, tenant_id=None, params={"user_id": target.id}, db=db))
        assert result["success"] is True
        assert "get_target" in result["result"]
        assert "gt@t.test" in result["result"]

    def test_get_nonexistent_user(self, db):
        caller = _make_user_obj(db, UserRole.SYSTEM_ADMIN, email="sa6@t.test", username="sa_gnf")

        tool = GetUserTool()
        result = _run(tool.execute(caller, tenant_id=None, params={"user_id": 99999}, db=db))
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_get_user_cross_tenant_denied(self, db):
        """Tenant-scoped caller cannot see users from other tenants."""
        from tests.factories import create_tenant
        t1 = create_tenant(db, name="Tenant A", slug="tenant-a")
        t2 = create_tenant(db, name="Tenant B", slug="tenant-b")
        caller = _make_user_obj(db, UserRole.ADMIN, email="a1@t.test", username="admin_cross", tenant_id=t1.id)
        other = _make_user_obj(db, UserRole.EDITOR, email="ot@t.test", username="other_tenant", tenant_id=t2.id)

        tool = GetUserTool()
        result = _run(tool.execute(caller, tenant_id=t1.id, params={"user_id": other.id}, db=db))
        assert result["success"] is False


# ---------------------------------------------------------------------------
# CreateUserTool
# ---------------------------------------------------------------------------

class TestCreateUserTool:
    def test_create_user_success(self, db):
        caller = _make_user_obj(db, UserRole.ADMIN, email="a2@t.test", username="admin_create")

        tool = CreateUserTool()
        result = _run(tool.execute(caller, tenant_id=None, params={
            "username": "newuser",
            "email": "new@example.com",
            "full_name": "New User",
            "role": "editor",
            "password": "password123",
        }, db=db))
        assert result["success"] is True
        assert "newuser" in result["result"]

    def test_create_user_duplicate_username(self, db):
        caller = _make_user_obj(db, UserRole.ADMIN, email="a3@t.test", username="admin_dup")
        _make_user_obj(db, UserRole.EDITOR, email="dup@t.test", username="existing_user")

        tool = CreateUserTool()
        result = _run(tool.execute(caller, tenant_id=None, params={
            "username": "existing_user",
            "email": "new2@example.com",
            "full_name": "Duplicate",
            "role": "editor",
            "password": "password123",
        }, db=db))
        assert result["success"] is False
        assert "already exists" in result["error"]

    def test_create_user_role_hierarchy_enforced(self, db):
        """An editor cannot create an admin."""
        caller = _make_user_obj(db, UserRole.EDITOR, email="e2@t.test", username="editor_nope")

        tool = CreateUserTool()
        result = _run(tool.execute(caller, tenant_id=None, params={
            "username": "hacker",
            "email": "hack@example.com",
            "full_name": "Hacker",
            "role": "admin",
            "password": "password123",
        }, db=db))
        assert result["success"] is False
        assert "higher role" in result["error"].lower()


# ---------------------------------------------------------------------------
# DeactivateUserTool
# ---------------------------------------------------------------------------

class TestDeactivateUserTool:
    def test_deactivate_user(self, db):
        caller = _make_user_obj(db, UserRole.ADMIN, email="a4@t.test", username="admin_deact")
        target = _make_user_obj(db, UserRole.EDITOR, email="d1@t.test", username="deact_target")

        tool = DeactivateUserTool()
        result = _run(tool.execute(caller, tenant_id=None, params={"user_id": target.id}, db=db))
        assert result["success"] is True
        assert "deactivated" in result["result"].lower()

        db.refresh(target)
        assert target.is_active is False

    def test_cannot_deactivate_self(self, db):
        caller = _make_user_obj(db, UserRole.ADMIN, email="a5@t.test", username="admin_self")

        tool = DeactivateUserTool()
        result = _run(tool.execute(caller, tenant_id=None, params={"user_id": caller.id}, db=db))
        assert result["success"] is False
        assert "yourself" in result["error"].lower()

    def test_deactivate_nonexistent(self, db):
        caller = _make_user_obj(db, UserRole.ADMIN, email="a6@t.test", username="admin_nf")

        tool = DeactivateUserTool()
        result = _run(tool.execute(caller, tenant_id=None, params={"user_id": 99999}, db=db))
        assert result["success"] is False


# ---------------------------------------------------------------------------
# ChangeUserRoleTool
# ---------------------------------------------------------------------------

class TestChangeUserRoleTool:
    def test_change_role_success(self, db):
        caller = _make_user_obj(db, UserRole.ADMIN, email="a7@t.test", username="admin_role")
        target = _make_user_obj(db, UserRole.EDITOR, email="r1@t.test", username="role_target")

        tool = ChangeUserRoleTool()
        result = _run(tool.execute(caller, tenant_id=None, params={
            "user_id": target.id, "new_role": "viewer",
        }, db=db))
        assert result["success"] is True
        db.refresh(target)
        assert target.role == UserRole.VIEWER

    def test_cannot_promote_above_own_role(self, db):
        """An editor cannot promote someone to admin."""
        caller = _make_user_obj(db, UserRole.EDITOR, email="e3@t.test", username="editor_promo")
        target = _make_user_obj(db, UserRole.VIEWER, email="r2@t.test", username="promo_target")

        tool = ChangeUserRoleTool()
        result = _run(tool.execute(caller, tenant_id=None, params={
            "user_id": target.id, "new_role": "admin",
        }, db=db))
        assert result["success"] is False
        assert "higher" in result["error"].lower()

    def test_change_role_nonexistent_user(self, db):
        caller = _make_user_obj(db, UserRole.ADMIN, email="a8@t.test", username="admin_rnf")

        tool = ChangeUserRoleTool()
        result = _run(tool.execute(caller, tenant_id=None, params={
            "user_id": 99999, "new_role": "viewer",
        }, db=db))
        assert result["success"] is False
