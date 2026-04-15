"""Wave AA — GDPR data export, deletion, and audit integrity services.

AA-001: Data export workflow
AA-002: Data deletion / anonymization workflow
AA-004: Audit log immutability & integrity verification
"""

from __future__ import annotations

import io
import json
import logging
import secrets
import zipfile
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import (
    ActionType,
    Attachment,
    AuditLog,
    Bookmark,
    ChatMessage,
    Comment,
    DataRequest,
    DataRequestStatus,
    DataRequestType,
    Document,
    Feedback,
    Notification,
    ReadingProgress,
    SecurityEvent,
    SupportTicketMessage,
    User,
    UserSession,
)
from app.services.audit_helper import write_audit_log
from app.utils.audience_audit_signing import verify_payload_signature

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# AA-001  Data Export
# ---------------------------------------------------------------------------


def request_data_export(db: Session, *, user_id: int, reason: str) -> DataRequest:
    """Create a data export request (GDPR Article 20)."""
    req = DataRequest(
        user_id=user_id,
        request_type=DataRequestType.EXPORT,
        status=DataRequestStatus.PENDING,
        reason=reason,
        requested_at=datetime.utcnow(),
    )
    db.add(req)
    write_audit_log(
        user_id=user_id,
        action=ActionType.SYSTEM,
        details=json.dumps({"event": "data_export_requested"}),
    )
    db.commit()
    db.refresh(req)
    return req


def execute_data_export(
    db: Session, request_id: int, *, analytics_db: Session | None = None
) -> bytes:
    """Build a ZIP archive containing all user data for a given export request.

    Returns the raw ZIP bytes.
    """
    req = db.query(DataRequest).filter(DataRequest.id == request_id).first()
    if not req or req.request_type != DataRequestType.EXPORT:
        raise ValueError("Invalid export request")

    _analytics = analytics_db or db

    req.status = DataRequestStatus.PROCESSING
    db.commit()

    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise ValueError("User not found")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. User profile
        profile = {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "timezone": user.timezone,
            "locale": user.locale,
            "created_at": str(user.created_at),
            "updated_at": str(user.updated_at),
        }
        zf.writestr("profile.json", json.dumps(profile, indent=2))

        # 2. Documents created by user
        docs = db.query(Document).filter(Document.created_by == user.id).all()
        doc_list = []
        for d in docs:
            doc_list.append(
                {
                    "id": d.id,
                    "title": d.title,
                    "document_number": d.document_number,
                    "status": d.status.value if hasattr(d.status, "value") else str(d.status),
                    "category": d.category,
                    "created_at": str(d.created_at),
                }
            )
        zf.writestr("documents.json", json.dumps(doc_list, indent=2))

        # 3. Comments
        comments = db.query(Comment).filter(Comment.user_id == user.id).all()
        comment_list = [
            {
                "id": c.id,
                "document_id": c.document_id,
                "content": c.content,
                "created_at": str(c.created_at),
            }
            for c in comments
        ]
        zf.writestr("comments.json", json.dumps(comment_list, indent=2))

        # 4. Bookmarks
        bookmarks = db.query(Bookmark).filter(Bookmark.user_id == user.id).all()
        bookmark_list = [{"id": b.id, "document_id": b.document_id} for b in bookmarks]
        zf.writestr("bookmarks.json", json.dumps(bookmark_list, indent=2))

        # 5. Feedback
        feedbacks = db.query(Feedback).filter(Feedback.user_id == user.id).all()
        feedback_list = [
            {
                "id": f.id,
                "document_id": f.document_id,
                "content": f.content,
                "type": f.type.value if hasattr(f.type, "value") else str(f.type),
                "created_at": str(f.created_at),
            }
            for f in feedbacks
        ]
        zf.writestr("feedback.json", json.dumps(feedback_list, indent=2))

        # 6. Audit logs for this user
        audit_logs = _analytics.query(AuditLog).filter(AuditLog.user_id == user.id).all()
        audit_list = [
            {
                "id": a.id,
                "action": a.action.value if hasattr(a.action, "value") else str(a.action),
                "details": a.details,
                "created_at": str(a.created_at),
            }
            for a in audit_logs
        ]
        zf.writestr("audit_logs.json", json.dumps(audit_list, indent=2))

        # 7. Reading progress
        progress = db.query(ReadingProgress).filter(ReadingProgress.user_id == user.id).all()
        progress_list = [
            {"document_id": p.document_id, "progress_pct": p.progress_pct} for p in progress
        ]
        zf.writestr("reading_progress.json", json.dumps(progress_list, indent=2))

        # 8. Notifications
        notifications = db.query(Notification).filter(Notification.user_id == user.id).all()
        notif_list = [
            {
                "id": n.id,
                "type": n.type.value if hasattr(n.type, "value") else str(n.type),
                "title": n.title,
                "created_at": str(n.created_at),
            }
            for n in notifications
        ]
        zf.writestr("notifications.json", json.dumps(notif_list, indent=2))

        # 9. Attachments metadata for user's documents
        if docs:
            doc_ids = [d.id for d in docs]
            attachments = db.query(Attachment).filter(Attachment.document_id.in_(doc_ids)).all()
            att_list = [
                {
                    "id": att.id,
                    "document_id": att.document_id,
                    "filename": att.filename,
                    "content_type": att.content_type,
                    "file_size": att.file_size,
                }
                for att in attachments
            ]
            zf.writestr("attachments.json", json.dumps(att_list, indent=2))

        # 10. Security events (AG-015)
        sec_events = _analytics.query(SecurityEvent).filter(SecurityEvent.user_id == user.id).all()
        sec_list = [
            {
                "id": e.id,
                "event_type": e.event_type.value
                if hasattr(e.event_type, "value")
                else str(e.event_type),
                "ip_address": e.ip_address,
                "user_agent": e.user_agent,
                "details": e.details,
                "created_at": str(e.created_at),
            }
            for e in sec_events
        ]
        zf.writestr("security_events.json", json.dumps(sec_list, indent=2))

        # 11. User sessions (AG-015)
        sessions = db.query(UserSession).filter(UserSession.user_id == user.id).all()
        session_list = [
            {
                "id": s.id,
                "ip_address": s.ip_address,
                "user_agent": s.user_agent,
                "last_active_at": str(s.last_active_at) if s.last_active_at else None,
                "revoked_at": str(s.revoked_at) if s.revoked_at else None,
                "created_at": str(s.created_at),
            }
            for s in sessions
        ]
        zf.writestr("user_sessions.json", json.dumps(session_list, indent=2))

        # 12. Chat messages (AG-015)
        chat_msgs = db.query(ChatMessage).filter(ChatMessage.sender_id == user.id).all()
        chat_list = [
            {
                "id": m.id,
                "chat_id": m.chat_id,
                "content": m.content,
                "message_type": m.message_type.value
                if hasattr(m.message_type, "value")
                else str(m.message_type),
                "created_at": str(m.created_at),
            }
            for m in chat_msgs
        ]
        zf.writestr("chat_messages.json", json.dumps(chat_list, indent=2))

        # 13. Support ticket messages (AG-015)
        support_msgs = (
            db.query(SupportTicketMessage).filter(SupportTicketMessage.sender_id == user.id).all()
        )
        support_list = [
            {
                "id": m.id,
                "ticket_id": m.ticket_id,
                "content": m.content,
                "is_internal_note": m.is_internal_note,
                "created_at": str(m.created_at),
            }
            for m in support_msgs
        ]
        zf.writestr("support_messages.json", json.dumps(support_list, indent=2))

    # Finalize
    token = secrets.token_urlsafe(64)
    req.download_token = token
    req.download_expires_at = datetime.utcnow() + timedelta(hours=48)
    req.status = DataRequestStatus.COMPLETED
    req.completed_at = datetime.utcnow()
    write_audit_log(
        user_id=req.user_id,
        action=ActionType.SYSTEM,
        details=json.dumps({"event": "data_export_completed", "request_id": req.id}),
    )
    db.commit()

    logger.info("Data export completed for user %d, request %d", req.user_id, req.id)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# AA-002  Data Deletion / Anonymization
# ---------------------------------------------------------------------------


def request_data_deletion(db: Session, *, user_id: int, reason: str) -> DataRequest:
    """Create a data deletion request.  Requires admin approval before execution."""
    req = DataRequest(
        user_id=user_id,
        request_type=DataRequestType.DELETION,
        status=DataRequestStatus.PENDING,
        reason=reason,
        requested_at=datetime.utcnow(),
    )
    db.add(req)
    write_audit_log(
        user_id=user_id,
        action=ActionType.SYSTEM,
        details=json.dumps({"event": "data_deletion_requested"}),
    )
    db.commit()
    db.refresh(req)
    return req


def approve_data_deletion(
    db: Session, request_id: int, *, admin_id: int, approved: bool, comment: str | None = None
) -> DataRequest:
    """Admin approves or rejects a deletion request."""
    req = db.query(DataRequest).filter(DataRequest.id == request_id).first()
    if not req or req.request_type != DataRequestType.DELETION:
        raise ValueError("Invalid deletion request")
    if req.status != DataRequestStatus.PENDING:
        raise ValueError("Request already processed")

    req.reviewed_by = admin_id
    req.admin_comment = comment
    if approved:
        req.status = DataRequestStatus.APPROVED
        req.approved_at = datetime.utcnow()
    else:
        req.status = DataRequestStatus.REJECTED

    write_audit_log(
        user_id=admin_id,
        action=ActionType.SYSTEM,
        details=json.dumps(
            {
                "event": "data_deletion_reviewed",
                "request_id": req.id,
                "approved": approved,
                "target_user_id": req.user_id,
            }
        ),
    )
    db.commit()
    db.refresh(req)
    return req


def execute_data_deletion(
    db: Session, request_id: int, *, analytics_db: Session | None = None
) -> dict[str, Any]:
    """Anonymize user data while preserving audit trail integrity.

    - Replaces PII with 'Deleted User' placeholder
    - Removes personal content (comments, bookmarks, feedback, sessions, etc.)
    - Preserves audit_logs with anonymized user reference
    - Deactivates the account
    """
    req = db.query(DataRequest).filter(DataRequest.id == request_id).first()
    if not req or req.request_type != DataRequestType.DELETION:
        raise ValueError("Invalid deletion request")
    if req.status != DataRequestStatus.APPROVED:
        raise ValueError("Request not approved")

    req.status = DataRequestStatus.PROCESSING
    db.commit()

    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise ValueError("User not found")

    anonymized_email = f"deleted-user-{user.id}@anonymized.local"
    anonymized_username = f"deleted-user-{user.id}"

    # 1. Delete personal content
    db.query(Comment).filter(Comment.user_id == user.id).delete()
    db.query(Bookmark).filter(Bookmark.user_id == user.id).delete()
    db.query(Feedback).filter(Feedback.user_id == user.id).delete()
    db.query(ReadingProgress).filter(ReadingProgress.user_id == user.id).delete()
    db.query(Notification).filter(Notification.user_id == user.id).delete()
    _analytics = analytics_db or db
    _analytics.query(SecurityEvent).filter(SecurityEvent.user_id == user.id).delete()
    if _analytics is not db:
        _analytics.commit()
    db.query(UserSession).filter(UserSession.user_id == user.id).delete()

    # 2. Anonymize user record (preserve for FK integrity in audit_logs)
    user.email = anonymized_email
    user.username = anonymized_username
    user.full_name = "Deleted User"
    user.hashed_password = "ACCOUNT_DELETED"
    user.is_active = False
    user.avatar_url = None
    user.last_login_ip = None
    user.last_login_user_agent = None
    user.notification_preferences = None

    # 3. Transfer document ownership label (documents stay but author shown as "Deleted User")
    # Documents remain intact — just the created_by FK stays pointing at the anonymized user

    # 4. Audit log entries remain intact — user_id FK still valid but user is anonymized

    # 5. Mark request completed
    req.status = DataRequestStatus.COMPLETED
    req.executed_at = datetime.utcnow()
    req.completed_at = datetime.utcnow()

    write_audit_log(
        user_id=req.reviewed_by,  # Use admin's ID since user is being deleted
        action=ActionType.SYSTEM,
        details=json.dumps(
            {
                "event": "data_deletion_executed",
                "request_id": req.id,
                "target_user_id": user.id,
                "anonymized_email": anonymized_email,
            }
        ),
    )
    db.commit()

    logger.info("Data deletion executed for user %d, request %d", user.id, req.id)
    return {
        "request_id": req.id,
        "user_id": user.id,
        "anonymized_email": anonymized_email,
        "status": "completed",
    }


# ---------------------------------------------------------------------------
# AA-004  Audit Log Immutability & Integrity Verification
# ---------------------------------------------------------------------------


def install_audit_immutability_trigger(db: Session, *, analytics_db: Session | None = None) -> None:
    """Install a SQLite trigger that prevents UPDATE and DELETE on audit_logs.

    This makes audit_logs append-only at the database level.
    For PostgreSQL, a similar trigger using RAISE would be used.
    """
    _analytics = analytics_db or db
    # SQLite: BEFORE DELETE trigger — raises an error by selecting from a table that doesn't exist
    _analytics.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS prevent_audit_log_delete
            BEFORE DELETE ON audit_logs
            BEGIN
                SELECT RAISE(ABORT, 'Audit logs are immutable — DELETE not allowed');
            END
            """
        )
    )
    _analytics.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS prevent_audit_log_update
            BEFORE UPDATE ON audit_logs
            BEGIN
                SELECT RAISE(ABORT, 'Audit logs are immutable — UPDATE not allowed');
            END
            """
        )
    )
    _analytics.commit()
    logger.info("Audit log immutability triggers installed")


def check_audit_integrity(db: Session, *, analytics_db: Session | None = None) -> dict[str, Any]:
    """Verify HMAC signatures on all signed audit log entries.

    Returns a summary with counts of valid, invalid, and unsigned entries.
    """
    _analytics = analytics_db or db
    signed_logs = (
        _analytics.query(AuditLog)
        .filter(AuditLog.signature.isnot(None), AuditLog.signature_key_id.isnot(None))
        .all()
    )

    total_signed = len(signed_logs)
    valid = 0
    invalid = 0

    for log_entry in signed_logs:
        # Reconstruct the payload that was signed
        payload: dict[str, Any] = {}
        if log_entry.details:
            try:
                payload = json.loads(log_entry.details)
            except json.JSONDecodeError:
                pass
        if log_entry.assignment_diff:
            try:
                payload["assignment_diff"] = json.loads(log_entry.assignment_diff)
            except json.JSONDecodeError:
                pass

        if verify_payload_signature(payload, log_entry.signature_key_id, log_entry.signature):
            valid += 1
        else:
            invalid += 1
            logger.warning("Audit log %d has invalid signature", log_entry.id)

    unsigned = _analytics.query(AuditLog).filter(AuditLog.signature.is_(None)).count()

    return {
        "total_signed": total_signed,
        "valid": valid,
        "invalid": invalid,
        "unsigned": unsigned,
        "integrity_ok": invalid == 0,
    }
