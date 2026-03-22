"""H-13: Add missing database indexes for frequent query columns.

Revision ID: h13_missing_indexes
Revises: 20260320_0001_c13_document_tenant_not_null
Create Date: 2026-03-20
"""

from alembic import op

# revision identifiers
revision = "h13_missing_indexes"
down_revision = "c13_doc_tenant_not_null"
branch_labels = None
depends_on = None


def upgrade():
    # --- Composite indexes for common query patterns ---

    # Documents: tenant + status (dashboard queries, scoped listing)
    op.create_index(
        "ix_documents_tenant_status",
        "documents",
        ["tenant_id", "status"],
    )
    # Documents: tenant + visibility (access control filtering)
    op.create_index(
        "ix_documents_tenant_visibility",
        "documents",
        ["tenant_id", "visibility"],
    )
    # Documents: created_by + status (author dashboard)
    op.create_index(
        "ix_documents_created_by_status",
        "documents",
        ["created_by", "status"],
    )

    # Versions: document + is_published (fetch latest published)
    op.create_index(
        "ix_versions_document_published",
        "versions",
        ["document_id", "is_published"],
    )

    # Notifications: user + is_read (unread notification count)
    op.create_index(
        "ix_notifications_user_read",
        "notifications",
        ["user_id", "is_read"],
    )

    # Feedbacks: document + status (feedback listing per document)
    op.create_index(
        "ix_feedbacks_document_status",
        "feedbacks",
        ["document_id", "status"],
    )

    # Reading progress: user + document (unique-ish lookup)
    op.create_index(
        "ix_reading_progress_user_document",
        "reading_progress",
        ["user_id", "document_id"],
    )

    # Bookmarks: user + document (lookup)
    op.create_index(
        "ix_bookmarks_user_document",
        "bookmarks",
        ["user_id", "document_id"],
    )

    # Review requests: document + status (pending reviews query)
    op.create_index(
        "ix_review_requests_document_status",
        "review_requests",
        ["document_id", "status"],
    )

    # Audit logs: user + action (user activity reports)
    op.create_index(
        "ix_audit_logs_user_action",
        "audit_logs",
        ["user_id", "action"],
    )

    # Support tickets: tenant + status (scoped listing)
    op.create_index(
        "ix_support_tickets_tenant_status",
        "support_tickets",
        ["tenant_id", "status"],
    )

    # Collaboration sessions: document + is_active (active session lookup)
    op.create_index(
        "ix_collab_sessions_document_active",
        "collaboration_sessions",
        ["document_id", "is_active"],
    )


def downgrade():
    op.drop_index("ix_collab_sessions_document_active", table_name="collaboration_sessions")
    op.drop_index("ix_support_tickets_tenant_status", table_name="support_tickets")
    op.drop_index("ix_audit_logs_user_action", table_name="audit_logs")
    op.drop_index("ix_review_requests_document_status", table_name="review_requests")
    op.drop_index("ix_bookmarks_user_document", table_name="bookmarks")
    op.drop_index("ix_reading_progress_user_document", table_name="reading_progress")
    op.drop_index("ix_feedbacks_document_status", table_name="feedbacks")
    op.drop_index("ix_notifications_user_read", table_name="notifications")
    op.drop_index("ix_versions_document_published", table_name="versions")
    op.drop_index("ix_documents_created_by_status", table_name="documents")
    op.drop_index("ix_documents_tenant_visibility", table_name="documents")
    op.drop_index("ix_documents_tenant_status", table_name="documents")
