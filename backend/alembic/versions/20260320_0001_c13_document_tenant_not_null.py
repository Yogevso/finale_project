"""C13: Make Document.tenant_id NOT NULL.

Revision ID: c13_doc_tenant_not_null
Revises: f9f304f9ce71
Create Date: 2026-03-20
"""

from alembic import op
import sqlalchemy as sa

revision = "c13_doc_tenant_not_null"
down_revision = "f9f304f9ce71"
branch_labels = None
depends_on = None


def _drop_audit_triggers(bind):
    """Temporarily drop audit_logs immutability triggers for SQLite batch ops."""
    if bind.dialect.name != "sqlite":
        return
    for name in ("prevent_audit_log_update", "prevent_audit_log_delete"):
        bind.execute(sa.text(f"DROP TRIGGER IF EXISTS {name}"))


def _recreate_audit_triggers(bind):
    """Recreate audit_logs immutability triggers after SQLite batch ops."""
    if bind.dialect.name != "sqlite":
        return
    inspector = sa.inspect(bind)
    if "audit_logs" not in inspector.get_table_names():
        return
    bind.execute(sa.text(
        "CREATE TRIGGER IF NOT EXISTS prevent_audit_log_update "
        "BEFORE UPDATE ON audit_logs BEGIN "
        "SELECT RAISE(ABORT, 'Audit logs are immutable — UPDATE not allowed'); END"
    ))
    bind.execute(sa.text(
        "CREATE TRIGGER IF NOT EXISTS prevent_audit_log_delete "
        "BEFORE DELETE ON audit_logs BEGIN "
        "SELECT RAISE(ABORT, 'Audit logs are immutable — DELETE not allowed'); END"
    ))


def _set_sqlite_foreign_keys(bind, enabled: bool) -> None:
    """Toggle SQLite FK enforcement for batch table rebuild operations."""
    if bind.dialect.name != "sqlite":
        return
    bind.execute(sa.text(f"PRAGMA foreign_keys={'ON' if enabled else 'OFF'}"))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Skip if documents table doesn't have tenant_id column (minimal legacy schemas)
    if "documents" not in inspector.get_table_names():
        return
    existing_cols = {c["name"] for c in inspector.get_columns("documents")}
    if "tenant_id" not in existing_cols:
        return

    # First, assign orphaned documents (tenant_id IS NULL) to tenant 1 (default)
    op.execute("UPDATE documents SET tenant_id = 1 WHERE tenant_id IS NULL")

    if bind.dialect.name == "sqlite":
        # SQLite rebuilds tables for ALTER COLUMN and can fail on legacy DBs with
        # large FK graphs. Keep data normalized and continue migration chain.
        return

    # Temporarily drop audit immutability triggers — batch_alter_table recreates
    # the documents table and FK cascade (ondelete SET NULL) would trigger them.
    _drop_audit_triggers(bind)
    _set_sqlite_foreign_keys(bind, enabled=False)
    try:
        with op.batch_alter_table("documents") as batch_op:
            batch_op.alter_column(
                "tenant_id",
                existing_type=sa.Integer(),
                nullable=False,
            )
    finally:
        _set_sqlite_foreign_keys(bind, enabled=True)
        _recreate_audit_triggers(bind)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return
    _drop_audit_triggers(bind)
    _set_sqlite_foreign_keys(bind, enabled=False)
    try:
        with op.batch_alter_table("documents") as batch_op:
            batch_op.alter_column(
                "tenant_id",
                existing_type=sa.Integer(),
                nullable=True,
            )
    finally:
        _set_sqlite_foreign_keys(bind, enabled=True)
        _recreate_audit_triggers(bind)
