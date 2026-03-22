"""Tests for the AI assistant tool registry — registration, lookup, parameter sanitization."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.assistant.schemas import ToolResult
from app.assistant.tools.base import BaseTool
from app.assistant.tools.registry import ToolRegistry
from app.models import UserRole
from app.services.permissions import Permission


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Helpers — minimal concrete tool for testing
# ---------------------------------------------------------------------------

class _DummyTool(BaseTool):
    name = "dummy_tool"
    description = "A test tool"
    parameters = {"type": "object", "properties": {}, "required": []}

    async def execute(self, user, tenant_id, params, db):
        return {"success": True, "result": "ok"}


class _AdminOnlyTool(BaseTool):
    name = "admin_tool"
    description = "Admin-only tool"
    parameters = {"type": "object", "properties": {}, "required": []}
    required_role = UserRole.ADMIN

    async def execute(self, user, tenant_id, params, db):
        return {"success": True, "result": "admin ok"}


class _PermissionTool(BaseTool):
    name = "perm_tool"
    description = "Permission-gated tool"
    parameters = {"type": "object", "properties": {}, "required": []}
    required_permission = Permission.MANAGE_USERS

    async def execute(self, user, tenant_id, params, db):
        return {"success": True, "result": "perm ok"}


class _FailingTool(BaseTool):
    name = "failing_tool"
    description = "Always raises"
    parameters = {"type": "object", "properties": {}, "required": []}

    async def execute(self, user, tenant_id, params, db):
        raise RuntimeError("boom")


def _make_user(role: UserRole = UserRole.EDITOR, tenant_id: int | None = 1) -> MagicMock:
    user = MagicMock()
    user.id = 1
    user.username = "testuser"
    user.role = role
    user.tenant_id = tenant_id
    user.is_active = True
    return user


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class TestToolRegistration:
    def test_register_tool(self):
        reg = ToolRegistry()
        reg.register(_DummyTool())
        assert reg.get("dummy_tool") is not None

    def test_register_duplicate_raises(self):
        reg = ToolRegistry()
        reg.register(_DummyTool())
        with pytest.raises(ValueError, match="Duplicate"):
            reg.register(_DummyTool())

    def test_get_unknown_returns_none(self):
        reg = ToolRegistry()
        assert reg.get("nonexistent") is None

    def test_list_all(self):
        reg = ToolRegistry()
        reg.register(_DummyTool())
        reg.register(_AdminOnlyTool())
        assert len(reg.list_all()) == 2


# ---------------------------------------------------------------------------
# Permission filtering
# ---------------------------------------------------------------------------

class TestToolPermissions:
    def test_editor_sees_dummy_not_admin_tool(self):
        reg = ToolRegistry()
        reg.register(_DummyTool())
        reg.register(_AdminOnlyTool())
        user = _make_user(UserRole.EDITOR)
        tools = reg.get_tools_for_user(user)
        names = [t.name for t in tools]
        assert "dummy_tool" in names
        assert "admin_tool" not in names

    def test_admin_sees_both_tools(self):
        reg = ToolRegistry()
        reg.register(_DummyTool())
        reg.register(_AdminOnlyTool())
        user = _make_user(UserRole.ADMIN)
        tools = reg.get_tools_for_user(user)
        names = [t.name for t in tools]
        assert "dummy_tool" in names
        assert "admin_tool" in names

    def test_permission_gated_tool_denied_for_viewer(self):
        reg = ToolRegistry()
        reg.register(_PermissionTool())
        user = _make_user(UserRole.VIEWER)
        tools = reg.get_tools_for_user(user)
        assert len(tools) == 0

    def test_permission_gated_tool_allowed_for_admin(self):
        reg = ToolRegistry()
        reg.register(_PermissionTool())
        user = _make_user(UserRole.ADMIN)
        tools = reg.get_tools_for_user(user)
        assert len(tools) == 1

    def test_ollama_tools_format(self):
        reg = ToolRegistry()
        reg.register(_DummyTool())
        user = _make_user(UserRole.SYSTEM_ADMIN)
        ollama_tools = reg.get_ollama_tools(user)
        assert len(ollama_tools) == 1
        t = ollama_tools[0]
        assert t["type"] == "function"
        assert t["function"]["name"] == "dummy_tool"
        assert "parameters" in t["function"]


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

class TestToolExecution:
    def test_execute_unknown_tool(self):
        reg = ToolRegistry()
        user = _make_user()
        result = _run(reg.execute_tool("nope", user, 1, {}, MagicMock()))
        assert result.success is False
        assert "Unknown tool" in result.error

    def test_execute_permission_denied(self):
        reg = ToolRegistry()
        reg.register(_AdminOnlyTool())
        user = _make_user(UserRole.VIEWER)
        result = _run(reg.execute_tool("admin_tool", user, 1, {}, MagicMock()))
        assert result.success is False
        assert "permission" in result.error.lower()

    def test_execute_success(self):
        reg = ToolRegistry()
        reg.register(_DummyTool())
        user = _make_user()
        result = _run(reg.execute_tool("dummy_tool", user, 1, {}, MagicMock()))
        assert result.success is True
        assert result.result == "ok"

    def test_execute_failing_tool_returns_error(self):
        reg = ToolRegistry()
        reg.register(_FailingTool())
        user = _make_user()
        result = _run(reg.execute_tool("failing_tool", user, 1, {}, MagicMock()))
        assert result.success is False
        assert "internal error" in result.error.lower()


# ---------------------------------------------------------------------------
# Parameter sanitization
# ---------------------------------------------------------------------------

class TestSanitizeParams:
    def test_null_string_to_none(self):
        result = ToolRegistry._sanitize_params({"key": "null"})
        assert result["key"] is None

    def test_none_string_to_none(self):
        result = ToolRegistry._sanitize_params({"key": "None"})
        assert result["key"] is None

    def test_empty_string_to_none(self):
        result = ToolRegistry._sanitize_params({"key": ""})
        assert result["key"] is None

    def test_undefined_string_to_none(self):
        result = ToolRegistry._sanitize_params({"key": "undefined"})
        assert result["key"] is None

    def test_numeric_param_coercion(self):
        result = ToolRegistry._sanitize_params({"limit": "20"})
        assert result["limit"] == 20
        assert isinstance(result["limit"], int)

    def test_numeric_param_invalid_stays_string(self):
        result = ToolRegistry._sanitize_params({"limit": "abc"})
        assert result["limit"] == "abc"

    def test_boolean_true_coercion(self):
        result = ToolRegistry._sanitize_params({"is_active": "true"})
        assert result["is_active"] is True

    def test_boolean_false_coercion(self):
        result = ToolRegistry._sanitize_params({"is_active": "false"})
        assert result["is_active"] is False

    def test_non_string_passthrough(self):
        result = ToolRegistry._sanitize_params({"count": 42, "flag": True})
        assert result["count"] == 42
        assert result["flag"] is True

    def test_all_numeric_params_recognized(self):
        for param_name in ToolRegistry._NUMERIC_PARAMS:
            result = ToolRegistry._sanitize_params({param_name: "5"})
            assert result[param_name] == 5, f"{param_name} was not coerced"

    def test_empty_params(self):
        assert ToolRegistry._sanitize_params({}) == {}
