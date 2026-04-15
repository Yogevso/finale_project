"""Security tools — sessions, security events, invitations management."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.assistant.tools.base import BaseTool
from app.models import (
    ActionType,
    Invitation,
    InvitationStatus,
    SecurityEvent,
    User,
    UserRole,
    UserSession,
)
from app.services.audit_helper import write_audit_log
from app.services.permissions import Permission


class GetMySessionsTool(BaseTool):
    name = "get_my_sessions"
    description = "List your active login sessions (device, IP, last activity)."
    parameters = {
        "type": "object",
        "properties": {
            "include_revoked": {
                "type": "boolean",
                "description": "Include revoked sessions (default false)",
            },
        },
        "required": [],
    }
    required_permission = Permission.VIEW_PUBLIC_DOCS

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        q = db.query(UserSession).filter(UserSession.user_id == user.id)
        if not params.get("include_revoked", False):
            q = q.filter(UserSession.revoked_at.is_(None))
        sessions = q.order_by(UserSession.last_active_at.desc()).limit(20).all()
        if not sessions:
            return {"success": True, "result": "No active sessions found."}
        lines = [f"{len(sessions)} session(s):"]
        for s in sessions:
            status = "revoked" if s.revoked_at else "active"
            ua_short = (s.user_agent or "Unknown device")[:60]
            lines.append(
                f"- [{s.id}] {status} — IP: {s.ip_address or '?'}, "
                f"device: {ua_short}, last active: {s.last_active_at:%Y-%m-%d %H:%M}"
            )
        return {"success": True, "result": "\n".join(lines)}


class RevokeSessionTool(BaseTool):
    name = "revoke_session"
    description = "Revoke one of your login sessions (log out a specific device)."
    parameters = {
        "type": "object",
        "properties": {
            "session_id": {"type": "integer", "description": "Session ID to revoke"},
        },
        "required": ["session_id"],
    }
    required_permission = Permission.VIEW_PUBLIC_DOCS
    confirm_before_execute = True

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        from datetime import datetime as dt

        s = (
            db.query(UserSession)
            .filter(
                UserSession.id == params["session_id"],
                UserSession.user_id == user.id,
            )
            .first()
        )
        if not s:
            return {"success": False, "result": "Session not found or does not belong to you."}
        if s.revoked_at:
            return {"success": True, "result": "Session is already revoked."}
        s.revoked_at = dt.utcnow()
        # AE-005: Audit trail for AI-initiated session revocation
        write_audit_log(
            user_id=user.id,
            action=ActionType.UPDATE,
            details=f"Revoked session #{s.id} via AI assistant",
        )
        db.commit()
        return {
            "success": True,
            "result": f"Session #{s.id} revoked. That device will need to log in again.",
        }


class GetMySecurityEventsTool(BaseTool):
    name = "get_my_security_events"
    description = (
        "View recent security events for your account (login attempts, password changes, etc.)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Max results (default 20)"},
        },
        "required": [],
    }
    required_permission = Permission.VIEW_PUBLIC_DOCS

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        limit = min(params.get("limit", 20), 50)
        events = (
            db.query(SecurityEvent)
            .filter(SecurityEvent.user_id == user.id)
            .order_by(SecurityEvent.created_at.desc())
            .limit(limit)
            .all()
        )
        if not events:
            return {"success": True, "result": "No security events recorded for your account."}
        lines = [f"{len(events)} recent security event(s):"]
        for e in events:
            lines.append(
                f"- [{e.created_at:%Y-%m-%d %H:%M}] {e.event_type} — " f"IP: {e.ip_address or '?'}"
            )
        return {"success": True, "result": "\n".join(lines)}


class GetSecurityEventsAdminTool(BaseTool):
    name = "get_security_events_admin"
    description = "View security events across all users (sysadmin only)."
    parameters = {
        "type": "object",
        "properties": {
            "user_id": {"type": "integer", "description": "Filter by user ID (optional)"},
            "event_type": {
                "type": "string",
                "description": "Filter by event type (optional)",
                "maxLength": 100,
            },
            "limit": {"type": "integer", "description": "Max results (default 25)"},
        },
        "required": [],
    }
    required_permission = Permission.SYSTEM_SETTINGS
    required_role = UserRole.SYSTEM_ADMIN

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        limit = min(params.get("limit", 25), 100)
        q = db.query(SecurityEvent)
        if params.get("user_id"):
            q = q.filter(SecurityEvent.user_id == params["user_id"])
        if params.get("event_type"):
            q = q.filter(SecurityEvent.event_type == params["event_type"])
        events = q.order_by(SecurityEvent.created_at.desc()).limit(limit).all()
        if not events:
            return {"success": True, "result": "No security events found matching criteria."}
        lines = [f"{len(events)} security event(s):"]
        for e in events:
            u = db.query(User).filter(User.id == e.user_id).first()
            name = u.full_name if u else f"User#{e.user_id}"
            lines.append(
                f"- [{e.created_at:%Y-%m-%d %H:%M}] {e.event_type} — {name} "
                f"(IP: {e.ip_address or '?'})"
            )
        return {"success": True, "result": "\n".join(lines)}


class GetInvitationStatusTool(BaseTool):
    name = "get_invitation_status"
    description = "Check the status of outstanding invitations (pending, accepted, expired)."
    parameters = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "Filter: pending, accepted, expired, cancelled (optional)",
                "maxLength": 50,
            },
            "limit": {"type": "integer", "description": "Max results (default 20)"},
        },
        "required": [],
    }
    required_permission = Permission.MANAGE_USERS

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        limit = min(params.get("limit", 20), 50)
        q = db.query(Invitation)
        if tenant_id:
            q = q.filter(Invitation.tenant_id == tenant_id)
        if params.get("status"):
            try:
                st = InvitationStatus(params["status"])
                q = q.filter(Invitation.status == st)
            except ValueError:
                return {
                    "success": False,
                    "result": "Invalid status. Use: pending, accepted, expired, cancelled.",
                }
        invitations = q.order_by(Invitation.created_at.desc()).limit(limit).all()
        if not invitations:
            return {"success": True, "result": "No invitations found."}
        lines = [f"{len(invitations)} invitation(s):"]
        for inv in invitations:
            inviter = db.query(User).filter(User.id == inv.invited_by).first()
            inviter_name = inviter.full_name if inviter else "Unknown"
            exp = f"expires {inv.expires_at:%Y-%m-%d}" if inv.expires_at else ""
            lines.append(
                f"- [{inv.id}] {inv.email} — {inv.status.value} (role: {inv.role.value}, "
                f"invited by {inviter_name}, {exp})"
            )
        return {"success": True, "result": "\n".join(lines)}


class CancelInvitationTool(BaseTool):
    name = "cancel_invitation"
    description = "Cancel a pending invitation."
    parameters = {
        "type": "object",
        "properties": {
            "invitation_id": {"type": "integer", "description": "Invitation ID to cancel"},
        },
        "required": ["invitation_id"],
    }
    required_permission = Permission.MANAGE_USERS
    confirm_before_execute = True

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session
    ) -> dict[str, Any]:
        inv = db.query(Invitation).filter(Invitation.id == params["invitation_id"]).first()
        if not inv:
            return {"success": False, "result": "Invitation not found."}
        # AE-008: Tenant isolation — prevent cross-tenant invitation cancellation
        if tenant_id is not None and inv.tenant_id != tenant_id:
            return {"success": False, "result": "Invitation not found."}
        if inv.status != InvitationStatus.PENDING:
            return {
                "success": False,
                "result": f"Cannot cancel — invitation is already '{inv.status.value}'.",
            }
        inv.status = InvitationStatus.CANCELLED
        # AE-005: Audit trail for AI-initiated invitation cancellation
        write_audit_log(
            user_id=user.id,
            action=ActionType.UPDATE,
            details=f"Cancelled invitation to {inv.email} via AI assistant",
        )
        db.commit()
        return {"success": True, "result": f"Invitation to {inv.email} cancelled."}
