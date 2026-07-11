"""Lightweight SQLite migration helpers used during startup initialization."""

from __future__ import annotations

import re

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine


def _legacy_preview_token() -> str:
    return "_".join(("preview", "pdf"))


def _legacy_preview_column(*parts: str) -> str:
    return "_".join((_legacy_preview_token(), *parts))


def run_lightweight_migrations(
    *,
    engine: Engine,
    analytics_engine: Engine | None = None,
    skip_versions_semantic_migration: bool = False,
) -> None:
    """Apply lightweight startup migrations for SQLite deployments."""
    if engine.dialect.name != "sqlite":
        return  # Alembic handles migrations for PostgreSQL
    with engine.connect() as conn:
        _ensure_platforms_table(conn)
        _ensure_document_columns(conn)
        _sync_document_platform_links(conn)
        _repair_document_status_lifecycle_drift(conn)
        _ensure_user_columns(conn)
        _ensure_feedback_columns(conn)
        _ensure_attachment_columns(conn)
        _ensure_support_ticket_message_columns(conn)
        _backfill_attachment_aliases(conn)
        _ensure_attachment_artifacts(conn)
        _ensure_attachment_conversion_jobs(conn)
        _ensure_domain_event_outbox(conn)
        _ensure_idempotency_keys(conn)
        _ensure_document_assignment_indexes(conn)
        _backfill_invitation_security_fields(conn)
        _ensure_invitation_delivery_columns(conn)
        if not skip_versions_semantic_migration:
            _ensure_versions_semantic_columns(conn)
        conn.commit()

    # audit_logs lives in the analytics database, not core.
    audit_log_engine = analytics_engine or engine
    if audit_log_engine.dialect.name == "sqlite":
        with audit_log_engine.connect() as audit_conn:
            _ensure_audit_log_columns(audit_conn)
            audit_conn.commit()


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "platform"


def _ensure_platforms_table(conn: Connection) -> None:
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS platforms (
                id INTEGER PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                slug VARCHAR(120) NOT NULL UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
            """
        )
    )
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_platforms_name ON platforms (name)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_platforms_slug ON platforms (slug)"))


def _ensure_document_columns(conn: Connection) -> None:
    columns = conn.execute(text("PRAGMA table_info(documents)")).fetchall()
    existing = {row[1] for row in columns}
    required_document_columns = {
        "topic": "ALTER TABLE documents ADD COLUMN topic VARCHAR(150)",
        "platform": "ALTER TABLE documents ADD COLUMN platform VARCHAR(100)",
        "platform_id": "ALTER TABLE documents ADD COLUMN platform_id INTEGER",
        "version_label": "ALTER TABLE documents ADD COLUMN version_label VARCHAR(50)",
        "parent_id": "ALTER TABLE documents ADD COLUMN parent_id INTEGER",
        "release_branch": "ALTER TABLE documents ADD COLUMN release_branch VARCHAR(100)",
        "row_version": "ALTER TABLE documents ADD COLUMN row_version INTEGER NOT NULL DEFAULT 1",
        "deleted_by": "ALTER TABLE documents ADD COLUMN deleted_by INTEGER",
        "deleted_at": "ALTER TABLE documents ADD COLUMN deleted_at DATETIME",
        "purge_at": "ALTER TABLE documents ADD COLUMN purge_at DATETIME",
    }
    for column_name, ddl in required_document_columns.items():
        if column_name not in existing:
            conn.execute(text(ddl))

    conn.execute(
        text(
            """
            UPDATE documents
            SET row_version = 1
            WHERE row_version IS NULL OR row_version < 1
            """
        )
    )
    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_documents_platform_id ON documents (platform_id)")
    )
    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_documents_deleted_by ON documents (deleted_by)")
    )
    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_documents_deleted_at ON documents (deleted_at)")
    )
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_documents_purge_at ON documents (purge_at)"))


def _sync_document_platform_links(conn: Connection) -> None:
    conn.execute(
        text(
            """
            INSERT OR IGNORE INTO platforms (name, slug, created_at, updated_at)
            VALUES ('Unspecified', 'unspecified', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
        )
    )
    unspecified_id = conn.execute(
        text("SELECT id FROM platforms WHERE slug = 'unspecified' LIMIT 1")
    ).scalar()

    platform_names = conn.execute(
        text(
            """
            SELECT DISTINCT TRIM(platform) AS platform_name
            FROM documents
            WHERE platform IS NOT NULL AND TRIM(platform) != ''
            """
        )
    ).fetchall()
    for row in platform_names:
        platform_name = row[0]
        if not platform_name:
            continue

        existing_platform_id = conn.execute(
            text(
                """
                SELECT id FROM platforms
                WHERE LOWER(name) = LOWER(:name)
                LIMIT 1
                """
            ),
            {"name": platform_name},
        ).scalar()
        if existing_platform_id:
            continue

        base_slug = _slugify(platform_name)
        slug = base_slug
        suffix = 2
        while conn.execute(
            text("SELECT 1 FROM platforms WHERE slug = :slug LIMIT 1"), {"slug": slug}
        ).scalar():
            slug = f"{base_slug}-{suffix}"
            suffix += 1

        conn.execute(
            text(
                """
                INSERT INTO platforms (name, slug, created_at, updated_at)
                VALUES (:name, :slug, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {"name": platform_name, "slug": slug},
        )

    platforms = conn.execute(text("SELECT id, name FROM platforms")).fetchall()
    for platform_id, platform_name in platforms:
        conn.execute(
            text(
                """
                UPDATE documents
                SET platform_id = :platform_id
                WHERE platform_id IS NULL
                  AND platform IS NOT NULL
                  AND LOWER(TRIM(platform)) = LOWER(:platform_name)
                """
            ),
            {"platform_id": platform_id, "platform_name": platform_name},
        )

    if unspecified_id is not None:
        conn.execute(
            text(
                """
                UPDATE documents
                SET platform = 'Unspecified',
                    platform_id = :platform_id
                WHERE platform_id IS NULL
                """
            ),
            {"platform_id": unspecified_id},
        )


def _repair_document_status_lifecycle_drift(conn: Connection) -> None:
    """Backfill document status from published-version reality for SQLite startups."""
    conn.execute(
        text(
            """
            UPDATE documents
            SET status = 'ACTIVE'
            WHERE deleted_at IS NULL
              AND status != 'ARCHIVED'
              AND status != 'ACTIVE'
              AND EXISTS (
                SELECT 1
                FROM versions
                WHERE versions.document_id = documents.id
                  AND versions.is_published = 1
              )
            """
        )
    )


def _ensure_attachment_columns(conn: Connection) -> None:
    attachment_columns = conn.execute(text("PRAGMA table_info(attachments)")).fetchall()
    existing_attachment_columns = {row[1] for row in attachment_columns}
    required_attachment_columns = {
        "size_bytes": "ALTER TABLE attachments ADD COLUMN size_bytes INTEGER",
        "storage_key": "ALTER TABLE attachments ADD COLUMN storage_key VARCHAR(500)",
        "sha256": "ALTER TABLE attachments ADD COLUMN sha256 VARCHAR(64)",
        "reader_html_status": "ALTER TABLE attachments ADD COLUMN reader_html_status VARCHAR(20)",
        "reader_html_content": "ALTER TABLE attachments ADD COLUMN reader_html_content TEXT",
        "reader_toc_json": "ALTER TABLE attachments ADD COLUMN reader_toc_json TEXT",
        "reader_toc_source": "ALTER TABLE attachments ADD COLUMN reader_toc_source VARCHAR(20)",
        "reader_html_error": "ALTER TABLE attachments ADD COLUMN reader_html_error TEXT",
        "reader_html_generated_at": "ALTER TABLE attachments ADD COLUMN reader_html_generated_at DATETIME",
    }
    # Preserve legacy columns so older SQLite files still match the current ORM model.
    required_attachment_columns.update(
        {
            _legacy_preview_column("status"): (
                f"ALTER TABLE attachments ADD COLUMN {_legacy_preview_column('status')} VARCHAR(20)"
            ),
            _legacy_preview_column("storage", "key"): (
                f"ALTER TABLE attachments ADD COLUMN {_legacy_preview_column('storage', 'key')} VARCHAR(500)"
            ),
            _legacy_preview_column("mime", "type"): (
                f"ALTER TABLE attachments ADD COLUMN {_legacy_preview_column('mime', 'type')} VARCHAR(100)"
            ),
            _legacy_preview_column("size", "bytes"): (
                f"ALTER TABLE attachments ADD COLUMN {_legacy_preview_column('size', 'bytes')} INTEGER"
            ),
            _legacy_preview_column("sha256"): (
                f"ALTER TABLE attachments ADD COLUMN {_legacy_preview_column('sha256')} VARCHAR(64)"
            ),
            _legacy_preview_column("error"): (
                f"ALTER TABLE attachments ADD COLUMN {_legacy_preview_column('error')} TEXT"
            ),
            _legacy_preview_column("generated", "at"): (
                f"ALTER TABLE attachments ADD COLUMN {_legacy_preview_column('generated', 'at')} DATETIME"
            ),
        }
    )
    for column_name, ddl in required_attachment_columns.items():
        if column_name not in existing_attachment_columns:
            conn.execute(text(ddl))

    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_attachments_storage_key ON attachments (storage_key)")
    )
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_attachments_sha256 ON attachments (sha256)"))
    for column_name in (
        _legacy_preview_column("status"),
        _legacy_preview_column("storage", "key"),
        _legacy_preview_column("sha256"),
    ):
        index_name = f"ix_attachments_{column_name}"
        conn.execute(
            text(f"CREATE INDEX IF NOT EXISTS {index_name} ON attachments ({column_name})")
        )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_attachments_reader_html_status "
            "ON attachments (reader_html_status)"
        )
    )


def _ensure_user_columns(conn: Connection) -> None:
    user_table = conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    ).fetchone()
    if user_table is None:
        return

    user_columns = conn.execute(text("PRAGMA table_info(users)")).fetchall()
    existing_user_columns = {row[1] for row in user_columns}
    required_user_columns = {
        "onboarding_state": "ALTER TABLE users ADD COLUMN onboarding_state JSON",
    }
    for column_name, ddl in required_user_columns.items():
        if column_name not in existing_user_columns:
            conn.execute(text(ddl))


def _ensure_feedback_columns(conn: Connection) -> None:
    feedback_table = conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='feedbacks'")
    ).fetchone()
    if feedback_table is None:
        return

    feedback_columns = conn.execute(text("PRAGMA table_info(feedbacks)")).fetchall()
    existing_feedback_columns = {row[1] for row in feedback_columns}
    required_feedback_columns = {
        "anchor_text": "ALTER TABLE feedbacks ADD COLUMN anchor_text TEXT",
    }
    for column_name, ddl in required_feedback_columns.items():
        if column_name not in existing_feedback_columns:
            conn.execute(text(ddl))


def _ensure_support_ticket_message_columns(conn: Connection) -> None:
    support_message_table = conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='support_ticket_messages'")
    ).fetchone()
    if support_message_table is None:
        return

    support_message_columns = conn.execute(
        text("PRAGMA table_info(support_ticket_messages)")
    ).fetchall()
    existing_support_message_columns = {row[1] for row in support_message_columns}
    required_support_message_columns = {
        "file_name": "ALTER TABLE support_ticket_messages ADD COLUMN file_name VARCHAR(255)",
        "file_size": "ALTER TABLE support_ticket_messages ADD COLUMN file_size INTEGER",
        "file_mime_type": "ALTER TABLE support_ticket_messages ADD COLUMN file_mime_type VARCHAR(100)",
        "file_storage_key": "ALTER TABLE support_ticket_messages ADD COLUMN file_storage_key VARCHAR(500)",
    }
    for column_name, ddl in required_support_message_columns.items():
        if column_name not in existing_support_message_columns:
            conn.execute(text(ddl))

    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_support_ticket_messages_file_storage_key "
            "ON support_ticket_messages (file_storage_key)"
        )
    )


def _backfill_attachment_aliases(conn: Connection) -> None:
    conn.execute(
        text(
            """
            UPDATE attachments
            SET size_bytes = file_size
            WHERE size_bytes IS NULL
              AND file_size IS NOT NULL
            """
        )
    )
    conn.execute(
        text(
            """
            UPDATE attachments
            SET storage_key = storage_path
            WHERE storage_key IS NULL
              AND storage_path IS NOT NULL
            """
        )
    )


def _ensure_attachment_artifacts(conn: Connection) -> None:
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS attachment_artifacts (
                id INTEGER PRIMARY KEY,
                attachment_id INTEGER NOT NULL,
                kind VARCHAR(40) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                mime_type VARCHAR(100),
                storage_key VARCHAR(500),
                size_bytes INTEGER,
                sha256 VARCHAR(64),
                content_text TEXT,
                content_json TEXT,
                source VARCHAR(40),
                error TEXT,
                generated_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                FOREIGN KEY(attachment_id) REFERENCES attachments(id),
                UNIQUE(attachment_id, kind)
            )
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_attachment_artifacts_attachment_id
            ON attachment_artifacts (attachment_id)
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_attachment_artifacts_kind
            ON attachment_artifacts (kind)
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_attachment_artifacts_status
            ON attachment_artifacts (status)
            """
        )
    )
    conn.execute(
        text(
            """
            INSERT INTO attachment_artifacts (
                attachment_id,
                kind,
                status,
                content_text,
                content_json,
                source,
                error,
                generated_at,
                created_at,
                updated_at
            )
            SELECT
                a.id,
                'reader_html',
                COALESCE(a.reader_html_status, 'pending'),
                a.reader_html_content,
                a.reader_toc_json,
                a.reader_toc_source,
                a.reader_html_error,
                a.reader_html_generated_at,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            FROM attachments a
            WHERE NOT EXISTS (
                SELECT 1
                FROM attachment_artifacts aa
                WHERE aa.attachment_id = a.id
                  AND aa.kind = 'reader_html'
            )
            """
        )
    )


def _ensure_attachment_conversion_jobs(conn: Connection) -> None:
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS attachment_conversion_jobs (
                id INTEGER PRIMARY KEY,
                attachment_id INTEGER NOT NULL,
                job_type VARCHAR(40) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                force BOOLEAN NOT NULL DEFAULT 0,
                attempts INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 3,
                last_error TEXT,
                started_at DATETIME,
                finished_at DATETIME,
                next_run_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                FOREIGN KEY(attachment_id) REFERENCES attachments(id),
                UNIQUE(attachment_id, job_type)
            )
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_attachment_conversion_jobs_status
            ON attachment_conversion_jobs (status)
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_attachment_conversion_jobs_next_run_at
            ON attachment_conversion_jobs (next_run_at)
            """
        )
    )


def _ensure_domain_event_outbox(conn: Connection) -> None:
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS domain_event_outbox (
                id INTEGER PRIMARY KEY,
                event_type VARCHAR(120) NOT NULL,
                event_key VARCHAR(255),
                payload_json TEXT NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 5,
                next_attempt_at DATETIME,
                last_error TEXT,
                claimed_at DATETIME,
                processed_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ix_domain_event_outbox_event_key
            ON domain_event_outbox (event_key)
            WHERE event_key IS NOT NULL
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_domain_event_outbox_status
            ON domain_event_outbox (status)
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_domain_event_outbox_next_attempt_at
            ON domain_event_outbox (next_attempt_at)
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_domain_event_outbox_event_type
            ON domain_event_outbox (event_type)
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_domain_event_outbox_created_at
            ON domain_event_outbox (created_at)
            """
        )
    )


def _ensure_idempotency_keys(conn: Connection) -> None:
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS idempotency_keys (
                id INTEGER PRIMARY KEY,
                idempotency_key VARCHAR(255) NOT NULL,
                method VARCHAR(10) NOT NULL,
                path VARCHAR(500) NOT NULL,
                user_scope VARCHAR(64) NOT NULL,
                user_id INTEGER,
                request_hash VARCHAR(64) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'processing',
                response_status INTEGER,
                response_body TEXT,
                response_content_type VARCHAR(120),
                processing_started_at DATETIME,
                last_error TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_idempotency_scope
            ON idempotency_keys (idempotency_key, method, path, user_scope)
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_idempotency_keys_status
            ON idempotency_keys (status)
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_idempotency_keys_user_id
            ON idempotency_keys (user_id)
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_idempotency_keys_created_at
            ON idempotency_keys (created_at)
            """
        )
    )


def _ensure_document_assignment_indexes(conn: Connection) -> None:
    conn.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_document_company_assignments_document_id_tenant_id
            ON document_company_assignments (document_id, tenant_id)
            """
        )
    )


def _ensure_audit_log_columns(conn: Connection) -> None:
    audit_columns = conn.execute(text("PRAGMA table_info(audit_logs)")).fetchall()
    existing_audit_columns = {row[1] for row in audit_columns}
    required_audit_columns = {
        "audience_event_type": "ALTER TABLE audit_logs ADD COLUMN audience_event_type VARCHAR(32)",
        "assignment_diff": "ALTER TABLE audit_logs ADD COLUMN assignment_diff TEXT",
        "signature_key_id": "ALTER TABLE audit_logs ADD COLUMN signature_key_id VARCHAR(32)",
        "signature": "ALTER TABLE audit_logs ADD COLUMN signature VARCHAR(128)",
    }
    for column_name, ddl in required_audit_columns.items():
        if column_name not in existing_audit_columns:
            conn.execute(text(ddl))

    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_audit_logs_audience_event_type "
            "ON audit_logs (audience_event_type)"
        )
    )


def _backfill_invitation_security_fields(conn: Connection) -> None:
    invitation_table = conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='invitations'")
    ).fetchone()
    if invitation_table is None:
        return

    from app.auth_context.invitation_tokens import (
        hash_invitation_token,
        looks_like_invitation_token_hash,
    )
    from app.utils.sanitization import sanitize_plain_text

    rows = conn.execute(text("SELECT id, token, message FROM invitations")).fetchall()
    for invitation_id, token, message in rows:
        updates: dict[str, object] = {}

        if token and not looks_like_invitation_token_hash(token):
            updates["token"] = hash_invitation_token(token)

        sanitized_message = sanitize_plain_text(message)
        if sanitized_message != message:
            updates["message"] = sanitized_message

        if not updates:
            continue

        params = {"invitation_id": invitation_id, **updates}
        set_clause = ", ".join(f"{column} = :{column}" for column in updates)
        conn.execute(
            text(f"UPDATE invitations SET {set_clause} WHERE id = :invitation_id"),
            params,
        )


def _ensure_invitation_delivery_columns(conn: Connection) -> None:
    invitation_table = conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='invitations'")
    ).fetchone()
    if invitation_table is None:
        return

    invitation_columns = conn.execute(text("PRAGMA table_info(invitations)")).fetchall()
    existing_columns = {row[1] for row in invitation_columns}
    required_columns = {
        "email_delivery_status": (
            "ALTER TABLE invitations ADD COLUMN email_delivery_status VARCHAR(20) "
            "NOT NULL DEFAULT 'pending'"
        ),
        "email_delivery_attempt_count": (
            "ALTER TABLE invitations ADD COLUMN email_delivery_attempt_count INTEGER "
            "NOT NULL DEFAULT 0"
        ),
        "email_last_attempted_at": (
            "ALTER TABLE invitations ADD COLUMN email_last_attempted_at DATETIME"
        ),
        "email_last_sent_at": "ALTER TABLE invitations ADD COLUMN email_last_sent_at DATETIME",
        "email_last_error": "ALTER TABLE invitations ADD COLUMN email_last_error TEXT",
        "email_last_subject": (
            "ALTER TABLE invitations ADD COLUMN email_last_subject VARCHAR(255)"
        ),
        "email_last_sender_email": (
            "ALTER TABLE invitations ADD COLUMN email_last_sender_email VARCHAR(255)"
        ),
        "email_last_sender_name": (
            "ALTER TABLE invitations ADD COLUMN email_last_sender_name VARCHAR(255)"
        ),
    }
    for column_name, ddl in required_columns.items():
        if column_name not in existing_columns:
            conn.execute(text(ddl))

    conn.execute(
        text(
            """
            UPDATE invitations
            SET email_delivery_status = 'pending'
            WHERE email_delivery_status IS NULL OR TRIM(email_delivery_status) = ''
            """
        )
    )
    conn.execute(
        text(
            """
            UPDATE invitations
            SET email_delivery_attempt_count = 0
            WHERE email_delivery_attempt_count IS NULL OR email_delivery_attempt_count < 0
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_invitations_email_delivery_status
            ON invitations (email_delivery_status)
            """
        )
    )


def _ensure_versions_semantic_columns(conn: Connection) -> None:
    version_columns = conn.execute(text("PRAGMA table_info(versions)")).fetchall()
    existing_version_columns = {row[1] for row in version_columns}
    required_version_columns = {
        "semantic_version": "ALTER TABLE versions ADD COLUMN semantic_version VARCHAR(32)",
        "bump_type": "ALTER TABLE versions ADD COLUMN bump_type VARCHAR(10) DEFAULT 'PATCH' NOT NULL",
        "published_by": "ALTER TABLE versions ADD COLUMN published_by INTEGER",
        "row_version": "ALTER TABLE versions ADD COLUMN row_version INTEGER NOT NULL DEFAULT 1",
    }
    for column_name, ddl in required_version_columns.items():
        if column_name not in existing_version_columns:
            conn.execute(text(ddl))

    conn.execute(
        text(
            """
            UPDATE versions
            SET row_version = 1
            WHERE row_version IS NULL OR row_version < 1
            """
        )
    )

    if (
        "semantic_version" in existing_version_columns
        or "semantic_version" in required_version_columns
    ):
        conn.execute(
            text(
                "UPDATE versions "
                "SET semantic_version = CASE "
                "WHEN version_number IS NULL OR version_number < 1 THEN '1.0.0' "
                "ELSE CAST(version_number AS TEXT) || '.0.0' END "
                "WHERE semantic_version IS NULL OR TRIM(semantic_version) = ''"
            )
        )

    conn.execute(
        text(
            "UPDATE versions "
            "SET bump_type = CASE LOWER(COALESCE(bump_type, '')) "
            "WHEN 'major' THEN 'MAJOR' "
            "WHEN 'minor' THEN 'MINOR' "
            "WHEN 'patch' THEN 'PATCH' "
            "ELSE COALESCE(bump_type, 'PATCH') END"
        )
    )
