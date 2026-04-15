"""Admin / system-admin tools — impersonation, feature flags, maintenance, quotas, etc."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.assistant.tools.base import BaseTool
from app.models import (
    ActionType,
    AdminAction,
    AdminActionStatus,
    Attachment,
    Document,
    FeatureFlag,
    ImpersonationSession,
    MaintenanceWindow,
    Tenant,
    TenantQuota,
    User,
    UserRole,
    UserSession,
)
from app.services.audit_helper import write_audit_log
from app.services.permissions import Permission

# --- Feature Flags ---


class ListFeatureFlagsTool(BaseTool):
    name = "list_feature_flags"
    description = "List feature flags for a tenant (sysadmin only)."
    parameters = {
        "type": "object",
        "properties": {
            "tenant_id": {"type": "integer", "description": "Tenant ID to inspect"},
        },
        "required": ["tenant_id"],
    }
    required_permission = Permission.SYSTEM_SETTINGS
    required_role = UserRole.SYSTEM_ADMIN

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        tid = params["tenant_id"]
        flags = (
            db.query(FeatureFlag)
            .filter(FeatureFlag.tenant_id == tid)
            .order_by(FeatureFlag.feature_key)
            .all()
        )
        if not flags:
            return {"success": True, "result": f"No feature flags configured for tenant {tid}."}
        lines = [f"{len(flags)} feature flag(s) for tenant {tid}:"]
        for f in flags:
            state = "ON" if f.enabled else "OFF"
            lines.append(f"- {f.feature_key}: {state} (updated {f.updated_at:%Y-%m-%d})")
        return {"success": True, "result": "\n".join(lines)}


class ToggleFeatureFlagTool(BaseTool):
    name = "toggle_feature_flag"
    description = "Enable or disable a feature flag for a tenant (sysadmin only)."
    parameters = {
        "type": "object",
        "properties": {
            "tenant_id": {"type": "integer", "description": "Tenant ID"},
            "feature_key": {
                "type": "string",
                "description": "Feature flag key name",
                "maxLength": 255,
            },
            "enabled": {"type": "boolean", "description": "True to enable, False to disable"},
        },
        "required": ["tenant_id", "feature_key", "enabled"],
    }
    required_permission = Permission.SYSTEM_SETTINGS
    required_role = UserRole.SYSTEM_ADMIN
    confirm_before_execute = True

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        tid = params["tenant_id"]
        key = params["feature_key"]
        enabled = params["enabled"]
        flag = (
            db.query(FeatureFlag)
            .filter(FeatureFlag.tenant_id == tid, FeatureFlag.feature_key == key)
            .first()
        )
        if not flag:
            flag = FeatureFlag(tenant_id=tid, feature_key=key, enabled=enabled, updated_by=user.id)
            db.add(flag)
            action = "Created and enabled" if enabled else "Created and disabled"
        else:
            flag.enabled = enabled
            flag.updated_by = user.id
            action = "Enabled" if enabled else "Disabled"
        # AE-005: Audit trail for AI-initiated feature flag changes
        write_audit_log(
            user_id=user.id,
            action=ActionType.UPDATE,
            details=f"{action} feature flag '{key}' for tenant {tid} via AI assistant",
        )
        db.commit()
        return {"success": True, "result": f"{action} feature flag '{key}' for tenant {tid}."}


# --- Maintenance Windows ---


class ListMaintenanceWindowsTool(BaseTool):
    name = "list_maintenance_windows"
    description = "List upcoming or active maintenance windows (sysadmin only)."
    parameters = {
        "type": "object",
        "properties": {
            "include_past": {
                "type": "boolean",
                "description": "Include past windows (default false)",
            },
        },
        "required": [],
    }
    required_permission = Permission.SYSTEM_SETTINGS
    required_role = UserRole.SYSTEM_ADMIN

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        from datetime import datetime as dt

        q = db.query(MaintenanceWindow)
        if not params.get("include_past", False):
            q = q.filter(MaintenanceWindow.scheduled_end >= dt.utcnow())
        windows = q.order_by(MaintenanceWindow.scheduled_start).limit(20).all()
        if not windows:
            return {"success": True, "result": "No maintenance windows found."}
        lines = [f"{len(windows)} maintenance window(s):"]
        for w in windows:
            active = " [ACTIVE]" if w.is_active else ""
            ro = " (read-only)" if w.is_read_only else ""
            lines.append(
                f"- [{w.id}] {w.title}{active}{ro}: "
                f"{w.scheduled_start:%Y-%m-%d %H:%M} → {w.scheduled_end:%Y-%m-%d %H:%M}"
            )
        return {"success": True, "result": "\n".join(lines)}


class CreateMaintenanceWindowTool(BaseTool):
    name = "create_maintenance_window"
    description = "Schedule a new maintenance window (sysadmin only)."
    parameters = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Title of the maintenance window",
                "maxLength": 255,
            },
            "description": {
                "type": "string",
                "description": "Details about the maintenance",
                "maxLength": 2000,
            },
            "scheduled_start": {
                "type": "string",
                "description": "Start time (ISO 8601, e.g. 2025-01-15T02:00:00)",
                "maxLength": 50,
            },
            "scheduled_end": {
                "type": "string",
                "description": "End time (ISO 8601)",
                "maxLength": 50,
            },
            "is_read_only": {
                "type": "boolean",
                "description": "Put system in read-only mode (default true)",
            },
        },
        "required": ["title", "scheduled_start", "scheduled_end"],
    }
    required_permission = Permission.SYSTEM_SETTINGS
    required_role = UserRole.SYSTEM_ADMIN
    confirm_before_execute = True

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        from datetime import datetime as dt

        start = dt.fromisoformat(params["scheduled_start"])
        end = dt.fromisoformat(params["scheduled_end"])
        if end <= start:
            return {"success": False, "result": "End time must be after start time."}
        mw = MaintenanceWindow(
            title=params["title"],
            description=params.get("description", ""),
            scheduled_start=start,
            scheduled_end=end,
            is_read_only=params.get("is_read_only", True),
            created_by=user.id,
        )
        db.add(mw)
        # AE-005: Audit trail for AI-initiated maintenance window creation
        write_audit_log(
            user_id=user.id,
            action=ActionType.CREATE,
            details=f"Created maintenance window '{params['title']}' ({start} - {end}) via AI assistant",
        )
        db.commit()
        db.refresh(mw)
        return {
            "success": True,
            "result": f"Maintenance window '{mw.title}' scheduled (ID: {mw.id}).",
        }


# --- Tenant Quotas ---


class GetTenantQuotaTool(BaseTool):
    name = "get_tenant_quota"
    description = "Get quota limits for a tenant (max users, documents, storage)."
    parameters = {
        "type": "object",
        "properties": {
            "tenant_id": {"type": "integer", "description": "Tenant ID"},
        },
        "required": ["tenant_id"],
    }
    required_permission = Permission.SYSTEM_SETTINGS
    required_role = UserRole.SYSTEM_ADMIN

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        tid = params["tenant_id"]
        quota = db.query(TenantQuota).filter(TenantQuota.tenant_id == tid).first()
        tenant = db.query(Tenant).filter(Tenant.id == tid).first()
        if not tenant:
            return {"success": False, "result": f"Tenant {tid} not found."}
        # Get current usage
        user_count = db.query(func.count(User.id)).filter(User.tenant_id == tid).scalar() or 0
        doc_count = (
            db.query(func.count(Document.id)).filter(Document.tenant_id == tid).scalar() or 0
        )
        storage = (
            db.query(func.sum(Attachment.file_size))
            .join(Document)
            .filter(Document.tenant_id == tid)
            .scalar()
            or 0
        )
        storage_mb = round(storage / (1024 * 1024), 1)
        if not quota:
            return {
                "success": True,
                "result": (
                    f"Tenant '{tenant.name}' (ID: {tid}) — no quotas set (unlimited).\n"
                    f"Current usage: {user_count} users, {doc_count} documents, {storage_mb} MB storage."
                ),
            }
        mu = f"{quota.max_users}" if quota.max_users else "unlimited"
        md = f"{quota.max_documents}" if quota.max_documents else "unlimited"
        ms = f"{quota.max_storage_mb} MB" if quota.max_storage_mb else "unlimited"
        return {
            "success": True,
            "result": (
                f"Tenant '{tenant.name}' (ID: {tid}) quotas:\n"
                f"- Users: {user_count} / {mu}\n"
                f"- Documents: {doc_count} / {md}\n"
                f"- Storage: {storage_mb} MB / {ms}"
            ),
        }


class UpdateTenantQuotaTool(BaseTool):
    name = "update_tenant_quota"
    description = "Update quota limits for a tenant (sysadmin only)."
    parameters = {
        "type": "object",
        "properties": {
            "tenant_id": {"type": "integer", "description": "Tenant ID"},
            "max_users": {"type": "integer", "description": "Max users (null for unlimited)"},
            "max_documents": {
                "type": "integer",
                "description": "Max documents (null for unlimited)",
            },
            "max_storage_mb": {
                "type": "integer",
                "description": "Max storage in MB (null for unlimited)",
            },
        },
        "required": ["tenant_id"],
    }
    required_permission = Permission.SYSTEM_SETTINGS
    required_role = UserRole.SYSTEM_ADMIN
    confirm_before_execute = True

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        tid = params["tenant_id"]
        quota = db.query(TenantQuota).filter(TenantQuota.tenant_id == tid).first()
        if not quota:
            quota = TenantQuota(tenant_id=tid, updated_by=user.id)
            db.add(quota)
        if "max_users" in params:
            quota.max_users = params["max_users"]
        if "max_documents" in params:
            quota.max_documents = params["max_documents"]
        if "max_storage_mb" in params:
            quota.max_storage_mb = params["max_storage_mb"]
        quota.updated_by = user.id
        # AE-005: Audit trail for AI-initiated quota changes
        write_audit_log(
            user_id=user.id,
            action=ActionType.UPDATE,
            details=f"Updated quotas for tenant {tid} via AI assistant",
        )
        db.commit()
        return {"success": True, "result": f"Quotas updated for tenant {tid}."}


# --- Impersonation Sessions ---


class ListImpersonationSessionsTool(BaseTool):
    name = "list_impersonation_sessions"
    description = "List recent impersonation sessions (sysadmin auditing)."
    parameters = {
        "type": "object",
        "properties": {
            "active_only": {
                "type": "boolean",
                "description": "Show only active sessions (default false)",
            },
            "limit": {"type": "integer", "description": "Max results (default 10)"},
        },
        "required": [],
    }
    required_permission = Permission.SYSTEM_SETTINGS
    required_role = UserRole.SYSTEM_ADMIN

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        limit = min(params.get("limit", 10), 50)
        q = db.query(ImpersonationSession)
        if params.get("active_only", False):
            q = q.filter(ImpersonationSession.is_active.is_(True))
        sessions = q.order_by(ImpersonationSession.started_at.desc()).limit(limit).all()
        if not sessions:
            return {"success": True, "result": "No impersonation sessions found."}
        lines = [f"{len(sessions)} impersonation session(s):"]
        for s in sessions:
            admin = db.query(User).filter(User.id == s.admin_user_id).first()
            tenant = db.query(Tenant).filter(Tenant.id == s.target_tenant_id).first()
            admin_name = admin.full_name if admin else f"User#{s.admin_user_id}"
            tenant_name = tenant.name if tenant else f"Tenant#{s.target_tenant_id}"
            status = (
                "ACTIVE"
                if s.is_active
                else f"ended {s.ended_at:%Y-%m-%d %H:%M}"
                if s.ended_at
                else "ended"
            )
            lines.append(
                f"- [{s.id}] {admin_name} → {tenant_name} ({status}, started {s.started_at:%Y-%m-%d %H:%M})"
            )
        return {"success": True, "result": "\n".join(lines)}


# --- Admin Actions (Approval Queue) ---


class ListAdminActionsTool(BaseTool):
    name = "list_admin_actions"
    description = "List pending or recent admin actions that require approval."
    parameters = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "Filter by status: pending, approved, rejected, executed, cancelled",
            },
            "limit": {"type": "integer", "description": "Max results (default 10)"},
        },
        "required": [],
    }
    required_permission = Permission.SYSTEM_SETTINGS
    required_role = UserRole.SYSTEM_ADMIN

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        limit = min(params.get("limit", 10), 50)
        q = db.query(AdminAction)
        status_filter = params.get("status")
        if status_filter:
            try:
                st = AdminActionStatus(status_filter)
                q = q.filter(AdminAction.status == st)
            except ValueError:
                return {
                    "success": False,
                    "result": f"Invalid status '{status_filter}'. Use: pending, approved, rejected, executed, cancelled.",
                }
        actions = q.order_by(AdminAction.created_at.desc()).limit(limit).all()
        if not actions:
            return {"success": True, "result": "No admin actions found."}
        lines = [f"{len(actions)} admin action(s):"]
        for a in actions:
            requester = db.query(User).filter(User.id == a.requested_by).first()
            req_name = requester.full_name if requester else f"User#{a.requested_by}"
            lines.append(
                f"- [{a.id}] {a.action_type.value} — {a.status.value} (by {req_name}, {a.created_at:%Y-%m-%d})"
            )
        return {"success": True, "result": "\n".join(lines)}


class ReviewAdminActionTool(BaseTool):
    name = "review_admin_action"
    description = (
        "Approve or reject a pending admin action (requires different sysadmin than requester)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action_id": {"type": "integer", "description": "Admin action ID"},
            "decision": {"type": "string", "description": "'approve' or 'reject'"},
            "comment": {"type": "string", "description": "Optional review comment"},
        },
        "required": ["action_id", "decision"],
    }
    required_permission = Permission.SYSTEM_SETTINGS
    required_role = UserRole.SYSTEM_ADMIN
    confirm_before_execute = True

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        from datetime import datetime as dt

        action = db.query(AdminAction).filter(AdminAction.id == params["action_id"]).first()
        if not action:
            return {"success": False, "result": "Admin action not found."}
        if action.status != AdminActionStatus.PENDING:
            return {
                "success": False,
                "result": f"Action is already '{action.status.value}', cannot review.",
            }
        if action.requested_by == user.id:
            return {"success": False, "result": "You cannot review your own action request."}
        decision = params["decision"].lower()
        if decision == "approve":
            action.status = AdminActionStatus.APPROVED
        elif decision == "reject":
            action.status = AdminActionStatus.REJECTED
        else:
            return {"success": False, "result": "Decision must be 'approve' or 'reject'."}
        action.reviewed_by = user.id
        action.review_comment = params.get("comment", "")
        action.reviewed_at = dt.utcnow()
        # AE-005: Audit trail for AI-initiated admin action review
        write_audit_log(
            user_id=user.id,
            action=ActionType.UPDATE,
            details=f"Admin action #{action.id} {decision}d via AI assistant",
        )
        db.commit()
        return {"success": True, "result": f"Admin action #{action.id} {decision}d."}


# --- Platform Overview ---


class GetPlatformOverviewTool(BaseTool):
    name = "get_platform_overview"
    description = (
        "Get a high-level overview of the platform: total tenants, users, documents, storage."
    )
    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
    }
    required_permission = Permission.SYSTEM_SETTINGS
    required_role = UserRole.SYSTEM_ADMIN

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        tenants = db.query(func.count(Tenant.id)).scalar() or 0
        users = db.query(func.count(User.id)).scalar() or 0
        active_users = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0
        docs = db.query(func.count(Document.id)).scalar() or 0
        storage = db.query(func.sum(Attachment.file_size)).scalar() or 0
        storage_mb = round(storage / (1024 * 1024), 1)
        active_sessions = (
            db.query(func.count(UserSession.id)).filter(UserSession.revoked_at.is_(None)).scalar()
            or 0
        )
        active_mw = (
            db.query(func.count(MaintenanceWindow.id))
            .filter(MaintenanceWindow.is_active.is_(True))
            .scalar()
            or 0
        )
        return {
            "success": True,
            "result": (
                "Platform overview:\n"
                f"- Tenants: {tenants}\n"
                f"- Users: {active_users} active / {users} total\n"
                f"- Documents: {docs}\n"
                f"- Storage: {storage_mb} MB\n"
                f"- Active sessions: {active_sessions}\n"
                f"- Active maintenance windows: {active_mw}"
            ),
        }


class GetTenantSummaryTool(BaseTool):
    name = "get_tenant_summary"
    description = "Get a detailed summary of a specific tenant — users, documents, storage, flags."
    parameters = {
        "type": "object",
        "properties": {
            "tenant_id": {"type": "integer", "description": "Tenant ID"},
        },
        "required": ["tenant_id"],
    }
    required_permission = Permission.SYSTEM_SETTINGS
    required_role = UserRole.SYSTEM_ADMIN

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        tid = params["tenant_id"]
        tenant = db.query(Tenant).filter(Tenant.id == tid).first()
        if not tenant:
            return {"success": False, "result": f"Tenant {tid} not found."}
        user_count = db.query(func.count(User.id)).filter(User.tenant_id == tid).scalar() or 0
        active_users = (
            db.query(func.count(User.id))
            .filter(User.tenant_id == tid, User.is_active.is_(True))
            .scalar()
            or 0
        )
        doc_count = (
            db.query(func.count(Document.id)).filter(Document.tenant_id == tid).scalar() or 0
        )
        storage = (
            db.query(func.sum(Attachment.file_size))
            .join(Document)
            .filter(Document.tenant_id == tid)
            .scalar()
            or 0
        )
        storage_mb = round(storage / (1024 * 1024), 1)
        flags = db.query(FeatureFlag).filter(FeatureFlag.tenant_id == tid).all()
        flag_str = (
            ", ".join(f"{f.feature_key}={'on' if f.enabled else 'off'}" for f in flags)
            if flags
            else "none"
        )
        quota = db.query(TenantQuota).filter(TenantQuota.tenant_id == tid).first()
        quota_str = "unlimited"
        if quota:
            parts = []
            if quota.max_users:
                parts.append(f"users≤{quota.max_users}")
            if quota.max_documents:
                parts.append(f"docs≤{quota.max_documents}")
            if quota.max_storage_mb:
                parts.append(f"storage≤{quota.max_storage_mb}MB")
            quota_str = ", ".join(parts) if parts else "unlimited"
        return {
            "success": True,
            "result": (
                f"Tenant: {tenant.name} (ID: {tid})\n"
                f"- Users: {active_users} active / {user_count} total\n"
                f"- Documents: {doc_count}\n"
                f"- Storage: {storage_mb} MB\n"
                f"- Feature flags: {flag_str}\n"
                f"- Quotas: {quota_str}"
            ),
        }
