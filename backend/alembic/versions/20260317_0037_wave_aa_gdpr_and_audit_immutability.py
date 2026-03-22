"""Wave AA — GDPR data_requests table and audit immutability triggers.

Revision ID: 20260317_0037
Revises: 20260316_0035
Create Date: 2026-03-17
"""

from alembic import op
import sqlalchemy as sa

revision = "20260317_0037"
down_revision = "20260316_0035"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return table_name in inspector.get_table_names()


def _trigger_exists(trigger_name: str) -> bool:
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == "sqlite":
        result = conn.execute(
            sa.text("SELECT name FROM sqlite_master WHERE type='trigger' AND name=:t"),
            {"t": trigger_name},
        )
        return result.scalar() is not None
    # PostgreSQL: check pg_trigger joined with pg_class
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM pg_trigger t JOIN pg_class c ON t.tgrelid = c.oid "
            "WHERE t.tgname = :t LIMIT 1"
        ),
        {"t": trigger_name},
    )
    return result.scalar() is not None


def upgrade() -> None:
    if not _table_exists("data_requests"):
        op.create_table(
            "data_requests",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
            sa.Column("request_type", sa.String(20), nullable=False, index=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending", index=True),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("admin_comment", sa.Text(), nullable=True),
            sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("download_token", sa.String(128), nullable=True, unique=True),
            sa.Column("download_expires_at", sa.DateTime(), nullable=True),
            sa.Column("requested_at", sa.DateTime(), nullable=False),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("executed_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
        )

    # AA-004: Audit log immutability triggers
    dialect = op.get_bind().dialect.name

    if _table_exists("audit_logs") and not _trigger_exists("prevent_audit_log_delete"):
        if dialect == "sqlite":
            op.execute(
                """
                CREATE TRIGGER prevent_audit_log_delete
                BEFORE DELETE ON audit_logs
                BEGIN
                    SELECT RAISE(ABORT, 'Audit logs are immutable — DELETE not allowed');
                END
                """
            )
        else:
            op.execute(sa.text(
                "CREATE OR REPLACE FUNCTION prevent_audit_log_delete_fn() RETURNS trigger AS $$ "
                "BEGIN RAISE EXCEPTION 'Audit logs are immutable — DELETE not allowed'; END; "
                "$$ LANGUAGE plpgsql"
            ))
            op.execute(sa.text(
                "CREATE TRIGGER prevent_audit_log_delete "
                "BEFORE DELETE ON audit_logs "
                "FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_delete_fn()"
            ))

    if _table_exists("audit_logs") and not _trigger_exists("prevent_audit_log_update"):
        if dialect == "sqlite":
            op.execute(
                """
                CREATE TRIGGER prevent_audit_log_update
                BEFORE UPDATE ON audit_logs
                BEGIN
                    SELECT RAISE(ABORT, 'Audit logs are immutable — UPDATE not allowed');
                END
                """
            )
        else:
            op.execute(sa.text(
                "CREATE OR REPLACE FUNCTION prevent_audit_log_update_fn() RETURNS trigger AS $$ "
                "BEGIN RAISE EXCEPTION 'Audit logs are immutable — UPDATE not allowed'; END; "
                "$$ LANGUAGE plpgsql"
            ))
            op.execute(sa.text(
                "CREATE TRIGGER prevent_audit_log_update "
                "BEFORE UPDATE ON audit_logs "
                "FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_update_fn()"
            ))


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS prevent_audit_log_update")
        op.execute("DROP TRIGGER IF EXISTS prevent_audit_log_delete")
    else:
        op.execute(sa.text("DROP TRIGGER IF EXISTS prevent_audit_log_update ON audit_logs"))
        op.execute(sa.text("DROP TRIGGER IF EXISTS prevent_audit_log_delete ON audit_logs"))
        op.execute(sa.text("DROP FUNCTION IF EXISTS prevent_audit_log_update_fn()"))
        op.execute(sa.text("DROP FUNCTION IF EXISTS prevent_audit_log_delete_fn()"))
    op.drop_table("data_requests")
