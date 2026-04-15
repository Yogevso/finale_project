"""Cleanup worker for expired sessions, tokens, stale records, and GDPR data retention.

Purges:
  - UserSession rows that have been revoked OR inactive > SESSION_INACTIVITY_DAYS
  - PasswordReset tokens that are expired AND used (or just expired > 7 days)
  - IdempotencyKeyRecord entries older than 7 days
  - Data retention: SecurityEvent, SearchAnalytics, NpsSurvey, Notification,
    resolved SupportTicket, ChatMessage (soft-deleted), AssistantConversation,
    CollaborationSnapshot (non-pinned / expired)

Run:
  python -m app.workers.cleanup_worker          # one-shot
  python -m app.workers.cleanup_worker --loop   # hourly loop
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import datetime, timedelta

import sqlalchemy as sa

from app.config import settings
from app.db import (
    AnalyticsSessionLocal,
    ChatSessionLocal,
    SessionLocal,
)
from app.models import (
    ActionType,
    AssistantConversation,
    ChatMessage,
    CollaborationSession,
    CollaborationSnapshot,
    Document,
    DocumentStatus,
    IdempotencyKeyRecord,
    Notification,
    NpsSurvey,
    PasswordReset,
    SearchAnalytics,
    SecurityEvent,
    SupportTicket,
    SupportTicketStatus,
    UserSession,
    Version,
)
from app.services.audit_helper import write_audit_log
from app.services.search_index_service import SearchIndexSyncService
from app.services.system_document_lifecycle_settings_service import (
    SystemDocumentLifecycleSettingsService,
)

logger = logging.getLogger(__name__)

IDEMPOTENCY_TTL_DAYS = 7
EXPIRED_RESET_GRACE_DAYS = 7


def _column_exists(db, table: str, column: str) -> bool:
    inspector = sa.inspect(db.bind)
    return any(existing["name"] == column for existing in inspector.get_columns(table))


def _document_model_columns_available(db) -> bool:
    required_columns = {"audience_version"}
    existing_columns = {
        existing["name"] for existing in sa.inspect(db.bind).get_columns("documents")
    }
    return required_columns.issubset(existing_columns)


def purge_expired_sessions(cutoff: datetime, *, dry_run: bool = False) -> int:
    """Delete revoked sessions and sessions inactive beyond threshold."""
    db = SessionLocal()
    try:
        query = db.query(UserSession).filter(
            (UserSession.revoked_at.isnot(None)) | (UserSession.last_active_at < cutoff)
        )
        count = query.count()
        if not dry_run and count:
            query.delete(synchronize_session=False)
            db.commit()
        logger.info("Purged %d expired/revoked sessions (dry_run=%s)", count, dry_run)
        return count
    finally:
        db.close()


def purge_expired_password_resets(now: datetime, *, dry_run: bool = False) -> int:
    """Delete password reset tokens that are expired and either used or past grace period."""
    db = SessionLocal()
    try:
        grace_cutoff = now - timedelta(days=EXPIRED_RESET_GRACE_DAYS)
        query = db.query(PasswordReset).filter(
            (PasswordReset.expires_at < now)
            & ((PasswordReset.used_at.isnot(None)) | (PasswordReset.expires_at < grace_cutoff))
        )
        count = query.count()
        if not dry_run and count:
            query.delete(synchronize_session=False)
            db.commit()
        logger.info("Purged %d expired password resets (dry_run=%s)", count, dry_run)
        return count
    finally:
        db.close()


def purge_stale_idempotency_records(cutoff: datetime, *, dry_run: bool = False) -> int:
    """Delete idempotency records older than TTL."""
    db = SessionLocal()
    try:
        query = db.query(IdempotencyKeyRecord).filter(IdempotencyKeyRecord.created_at < cutoff)
        count = query.count()
        if not dry_run and count:
            query.delete(synchronize_session=False)
            db.commit()
        logger.info("Purged %d stale idempotency records (dry_run=%s)", count, dry_run)
        return count
    finally:
        db.close()


# ---------------------------------------------------------------------------
# GDPR Data Retention Purges
# ---------------------------------------------------------------------------


def _purge_analytics(model, cutoff: datetime, *, dry_run: bool = False, label: str = "") -> int:
    """Purge rows from an Analytics DB table older than cutoff."""
    db = AnalyticsSessionLocal()
    try:
        query = db.query(model).filter(model.created_at < cutoff)
        count = query.count()
        if not dry_run and count:
            query.delete(synchronize_session=False)
            db.commit()
        logger.info(
            "Purged %d %s records (dry_run=%s)", count, label or model.__tablename__, dry_run
        )
        return count
    finally:
        db.close()


def purge_old_notifications(cutoff: datetime, *, dry_run: bool = False) -> int:
    """Delete read notifications older than cutoff."""
    db = ChatSessionLocal()
    try:
        query = db.query(Notification).filter(
            Notification.created_at < cutoff,
            Notification.is_read.is_(True),
        )
        count = query.count()
        if not dry_run and count:
            query.delete(synchronize_session=False)
            db.commit()
        logger.info("Purged %d old notifications (dry_run=%s)", count, dry_run)
        return count
    finally:
        db.close()


def purge_resolved_support_tickets(cutoff: datetime, *, dry_run: bool = False) -> int:
    """Delete support tickets resolved before cutoff (cascade deletes messages)."""
    db = SessionLocal()
    try:
        query = db.query(SupportTicket).filter(
            SupportTicket.status == SupportTicketStatus.CLOSED,
            SupportTicket.resolved_at.isnot(None),
            SupportTicket.resolved_at < cutoff,
        )
        count = query.count()
        if not dry_run and count:
            query.delete(synchronize_session=False)
            db.commit()
        logger.info("Purged %d resolved support tickets (dry_run=%s)", count, dry_run)
        return count
    finally:
        db.close()


def purge_soft_deleted_chat_messages(cutoff: datetime, *, dry_run: bool = False) -> int:
    """Hard-delete soft-deleted chat messages older than cutoff."""
    db = ChatSessionLocal()
    try:
        query = db.query(ChatMessage.id).filter(
            ChatMessage.deleted_at.isnot(None),
            ChatMessage.deleted_at < cutoff,
        )
        count = query.count()
        if not dry_run and count:
            db.query(ChatMessage).filter(
                ChatMessage.deleted_at.isnot(None),
                ChatMessage.deleted_at < cutoff,
            ).delete(synchronize_session=False)
            db.commit()
        logger.info("Purged %d soft-deleted chat messages (dry_run=%s)", count, dry_run)
        return count
    finally:
        db.close()


def purge_old_assistant_conversations(cutoff: datetime, *, dry_run: bool = False) -> int:
    """Delete archived assistant conversations older than cutoff (cascade deletes messages)."""
    db = ChatSessionLocal()
    try:
        query = db.query(AssistantConversation).filter(
            AssistantConversation.updated_at < cutoff,
            AssistantConversation.is_archived.is_(True),
        )
        count = query.count()
        if not dry_run and count:
            query.delete(synchronize_session=False)
            db.commit()
        logger.info("Purged %d old assistant conversations (dry_run=%s)", count, dry_run)
        return count
    finally:
        db.close()


def purge_soft_deleted_documents(cutoff: datetime, *, dry_run: bool = False) -> int:
    """Delete documents whose recovery window has expired."""
    db = SessionLocal()
    try:
        if not (
            _column_exists(db, "documents", "deleted_at")
            and _column_exists(db, "documents", "purge_at")
            and _document_model_columns_available(db)
        ):
            logger.info("Skipped deleted-document purge; recovery columns are not present yet")
            return 0
        query = db.query(Document).filter(
            Document.deleted_at.isnot(None),
            Document.purge_at.isnot(None),
            Document.purge_at < cutoff,
        )
        count = query.count()
        if not dry_run and count:
            for document in query.all():
                db.delete(document)
            db.commit()
        logger.info("Purged %d soft-deleted documents (dry_run=%s)", count, dry_run)
        return count
    finally:
        db.close()


def auto_archive_published_documents(now: datetime, *, dry_run: bool = False) -> int:
    """Archive active documents whose latest published version is older than the configured retention window."""
    db = SessionLocal()
    chat_db = ChatSessionLocal()
    try:
        if not (
            _column_exists(db, "documents", "status")
            and _column_exists(db, "documents", "deleted_at")
            and _column_exists(db, "documents", "row_version")
            and _column_exists(db, "versions", "published_at")
        ):
            logger.info(
                "Skipped document auto-archive; required retention columns are not present yet"
            )
            return 0
        lifecycle_settings, _metadata = (
            SystemDocumentLifecycleSettingsService.get_effective_settings(db)
        )
        cutoff = lifecycle_settings.archive_cutoff(now)
        if cutoff is None:
            logger.info("Skipped document auto-archive; policy is disabled")
            return 0

        latest_published = (
            db.query(
                Version.document_id.label("document_id"),
                sa.func.max(Version.published_at).label("last_published"),
            )
            .filter(
                Version.is_published.is_(True),
                Version.published_at.isnot(None),
            )
            .group_by(Version.document_id)
            .subquery()
        )

        rows = (
            db.query(Document.id, latest_published.c.last_published)
            .join(latest_published, latest_published.c.document_id == Document.id)
            .filter(
                Document.status == DocumentStatus.ACTIVE,
                Document.deleted_at.is_(None),
                latest_published.c.last_published <= cutoff,
            )
            .all()
        )
        count = len(rows)
        if not dry_run and rows:
            from app.projections import (
                invalidate_portal_audience_cache,
                invalidate_search_audience_cache,
            )

            archived_document_ids: list[int] = []
            search_index = SearchIndexSyncService(db)

            for document_id, last_published in rows:
                db.query(Document).filter(Document.id == document_id).update(
                    {
                        Document.status: DocumentStatus.ARCHIVED,
                        Document.updated_at: now,
                        Document.row_version: Document.row_version + 1,
                    },
                    synchronize_session=False,
                )
                archived_document_ids.append(int(document_id))
                search_index.remove_document(int(document_id))
                write_audit_log(
                    user_id=None,
                    document_id=document_id,
                    action=ActionType.SYSTEM,
                    details=json.dumps(
                        {
                            "event": "document_auto_archived",
                            "basis": lifecycle_settings.auto_archive_basis,
                            "last_published": (
                                last_published.isoformat() if last_published is not None else None
                            ),
                            "cutoff": cutoff.isoformat(),
                            "auto_archive_after_value": lifecycle_settings.auto_archive_after_value,
                            "auto_archive_after_unit": lifecycle_settings.auto_archive_after_unit,
                        },
                        sort_keys=True,
                    ),
                )

            db.commit()

            chat_db.query(CollaborationSession).filter(
                CollaborationSession.document_id.in_(archived_document_ids),
                CollaborationSession.is_active.is_(True),
            ).update({"is_active": False, "ended_at": now}, synchronize_session=False)
            chat_db.commit()

            invalidate_portal_audience_cache()
            invalidate_search_audience_cache()

        logger.info(
            "Auto-archived %d documents (dry_run=%s, cutoff=%s)",
            count,
            dry_run,
            cutoff.isoformat(),
        )
        return count
    finally:
        chat_db.close()
        db.close()


def purge_expired_collab_snapshots(now: datetime, *, dry_run: bool = False) -> int:
    """Delete non-pinned collaboration snapshots past their expires_at or older than retention."""
    db = ChatSessionLocal()
    try:
        cutoff = now - timedelta(days=settings.RETENTION_COLLAB_SNAPSHOTS_DAYS)
        query = db.query(CollaborationSnapshot).filter(
            CollaborationSnapshot.is_pinned.is_(False),
            (
                (
                    CollaborationSnapshot.expires_at.isnot(None)
                    & (CollaborationSnapshot.expires_at < now)
                )
                | (CollaborationSnapshot.created_at < cutoff)
            ),
        )
        count = query.count()
        if not dry_run and count:
            query.delete(synchronize_session=False)
            db.commit()
        logger.info("Purged %d expired collab snapshots (dry_run=%s)", count, dry_run)
        return count
    finally:
        db.close()


def run_cleanup(*, dry_run: bool = False) -> dict[str, int]:
    """Execute all cleanup tasks. Returns counts of purged records."""
    now = datetime.utcnow()
    session_cutoff = now - timedelta(days=settings.SESSION_INACTIVITY_DAYS)
    idempotency_cutoff = now - timedelta(days=IDEMPOTENCY_TTL_DAYS)

    result: dict[str, int] = {
        "sessions": purge_expired_sessions(session_cutoff, dry_run=dry_run),
        "password_resets": purge_expired_password_resets(now, dry_run=dry_run),
        "idempotency_records": purge_stale_idempotency_records(idempotency_cutoff, dry_run=dry_run),
    }

    # GDPR data retention purges
    retention_tasks: list[tuple[str, int, object]] = [
        ("security_events", settings.RETENTION_SECURITY_EVENTS_DAYS, SecurityEvent),
        ("search_analytics", settings.RETENTION_SEARCH_ANALYTICS_DAYS, SearchAnalytics),
        ("nps_surveys", settings.RETENTION_NPS_SURVEYS_DAYS, NpsSurvey),
    ]
    for key, days, model in retention_tasks:
        if days > 0:
            cutoff = now - timedelta(days=days)
            result[key] = _purge_analytics(model, cutoff, dry_run=dry_run, label=key)

    if settings.RETENTION_NOTIFICATIONS_DAYS > 0:
        cutoff = now - timedelta(days=settings.RETENTION_NOTIFICATIONS_DAYS)
        result["notifications"] = purge_old_notifications(cutoff, dry_run=dry_run)

    if settings.RETENTION_RESOLVED_TICKETS_DAYS > 0:
        cutoff = now - timedelta(days=settings.RETENTION_RESOLVED_TICKETS_DAYS)
        result["resolved_tickets"] = purge_resolved_support_tickets(cutoff, dry_run=dry_run)

    if settings.RETENTION_CHAT_MESSAGES_DAYS > 0:
        cutoff = now - timedelta(days=settings.RETENTION_CHAT_MESSAGES_DAYS)
        result["chat_messages_deleted"] = purge_soft_deleted_chat_messages(cutoff, dry_run=dry_run)

    if settings.RETENTION_ASSISTANT_CONVERSATIONS_DAYS > 0:
        cutoff = now - timedelta(days=settings.RETENTION_ASSISTANT_CONVERSATIONS_DAYS)
        result["assistant_conversations"] = purge_old_assistant_conversations(
            cutoff, dry_run=dry_run
        )

    result["auto_archived_documents"] = auto_archive_published_documents(now, dry_run=dry_run)
    result["deleted_documents"] = purge_soft_deleted_documents(now, dry_run=dry_run)
    result["collab_snapshots"] = purge_expired_collab_snapshots(now, dry_run=dry_run)

    return result


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    parser = argparse.ArgumentParser(description="Cleanup expired sessions/tokens")
    parser.add_argument("--loop", action="store_true", help="Run hourly in a loop")
    parser.add_argument("--dry-run", action="store_true", help="Count only, don't delete")
    parser.add_argument("--interval", type=int, default=3600, help="Loop interval in seconds")
    args = parser.parse_args()

    if args.loop:
        logger.info("Starting cleanup worker loop (interval=%ds)", args.interval)
        while True:
            try:
                result = run_cleanup(dry_run=args.dry_run)
                logger.info("Cleanup complete: %s", result)
            except Exception:  # policy: LOSSY — worker loop records failure and continues polling
                logger.exception("Cleanup cycle failed")
            time.sleep(args.interval)
    else:
        result = run_cleanup(dry_run=args.dry_run)
        logger.info("Cleanup complete: %s", result)


if __name__ == "__main__":
    main()
