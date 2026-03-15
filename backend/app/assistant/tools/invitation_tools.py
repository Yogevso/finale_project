"""AI assistant tools for user invitations."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.assistant.tools.base import BaseTool
from app.models import Invitation, InvitationStatus, User, UserRole
from app.services.permissions import Permission

logger = logging.getLogger(__name__)


class CreateInvitationTool(BaseTool):
    name = "create_invitation"
    description = "Create an invitation to onboard a new user via email."
    parameters = {
        "type": "object",
        "properties": {
            "email": {"type": "string", "description": "Email address to invite"},
            "role": {
                "type": "string",
                "description": "Role for the new user (e.g. VIEWER, EDITOR, ADMIN, CUSTOMER)",
            },
            "message": {"type": "string", "description": "Optional message to include"},
        },
        "required": ["email", "role"],
    }
    required_role = "ADMIN"
    confirm_before_execute = True

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session,
    ) -> dict[str, Any]:
        email = params["email"].strip().lower()
        role_str = params["role"].upper()

        # Validate role
        try:
            role = UserRole(role_str.lower()) if hasattr(UserRole, role_str) else UserRole[role_str]
        except (KeyError, ValueError):
            valid = ", ".join(r.name for r in UserRole)
            return {"success": False, "result": "", "error": f"Invalid role '{role_str}'. Valid: {valid}"}

        # Check if invitation already exists
        existing = (
            db.query(Invitation)
            .filter(
                Invitation.email == email,
                Invitation.status == InvitationStatus.PENDING,
            )
            .first()
        )
        if existing:
            return {"success": False, "result": "", "error": f"A pending invitation for {email} already exists (ID: {existing.id})."}

        invitation = Invitation(
            email=email,
            token=secrets.token_urlsafe(32),
            role=role,
            tenant_id=tenant_id,
            invited_by=user.id,
            status=InvitationStatus.PENDING,
            message=params.get("message", "")[:500] if params.get("message") else None,
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        db.add(invitation)
        db.commit()
        db.refresh(invitation)

        return {
            "success": True,
            "result": f"Invitation created (ID: {invitation.id}) for **{email}** with role **{role.name}**. Expires in 7 days.",
        }


class ListInvitationsTool(BaseTool):
    name = "list_invitations"
    description = "List invitations, optionally filtered by status."
    parameters = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "Filter by status: PENDING, ACCEPTED, EXPIRED, CANCELLED",
            },
            "limit": {"type": "integer", "description": "Max results (default 20)"},
        },
        "required": [],
    }
    required_role = "ADMIN"

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session,
    ) -> dict[str, Any]:
        limit = min(params.get("limit", 20), 50)
        query = db.query(Invitation)

        if tenant_id is not None:
            query = query.filter(Invitation.tenant_id == tenant_id)

        status_str = params.get("status", "").upper()
        if status_str:
            try:
                status = InvitationStatus(status_str.lower()) if hasattr(InvitationStatus, status_str) else InvitationStatus[status_str]
                query = query.filter(Invitation.status == status)
            except (KeyError, ValueError):
                pass

        invitations = query.order_by(Invitation.created_at.desc()).limit(limit).all()
        if not invitations:
            return {"success": True, "result": "No invitations found."}

        inviter_ids = {i.invited_by for i in invitations}
        users = {u.id: u.full_name or u.email for u in db.query(User).filter(User.id.in_(inviter_ids)).all()} if inviter_ids else {}

        lines = [f"**Invitations** ({len(invitations)})\n"]
        for inv in invitations:
            inviter = users.get(inv.invited_by, "Unknown")
            date = inv.created_at.strftime("%Y-%m-%d") if inv.created_at else "N/A"
            expires = inv.expires_at.strftime("%Y-%m-%d") if inv.expires_at else "N/A"
            lines.append(
                f"- **{inv.email}** — {inv.status.value} | Role: {inv.role.name} | "
                f"By: {inviter} | Created: {date} | Expires: {expires}"
            )

        return {"success": True, "result": "\n".join(lines)}
