"""Add audience-governance columns to audit_logs

Revision ID: 20260308_0016
Revises: 20260308_0015
Create Date: 2026-03-08 17:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260308_0016"
down_revision = "20260308_0015"
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name)


def upgrade() -> None:
    if not _table_exists("audit_logs"):
        return

    existing_columns = _column_names("audit_logs")

    with op.batch_alter_table("audit_logs") as batch_op:
        if "audience_event_type" not in existing_columns:
            batch_op.add_column(sa.Column("audience_event_type", sa.String(length=32), nullable=True))
        if "assignment_diff" not in existing_columns:
            batch_op.add_column(sa.Column("assignment_diff", sa.Text(), nullable=True))
        if "signature_key_id" not in existing_columns:
            batch_op.add_column(sa.Column("signature_key_id", sa.String(length=32), nullable=True))
        if "signature" not in existing_columns:
            batch_op.add_column(sa.Column("signature", sa.String(length=128), nullable=True))

    existing_indexes = _index_names("audit_logs")
    if "ix_audit_logs_audience_event_type" not in existing_indexes:
        op.create_index(
            "ix_audit_logs_audience_event_type",
            "audit_logs",
            ["audience_event_type"],
            unique=False,
        )


def downgrade() -> None:
    if not _table_exists("audit_logs"):
        return

    existing_indexes = _index_names("audit_logs")
    if "ix_audit_logs_audience_event_type" in existing_indexes:
        op.drop_index("ix_audit_logs_audience_event_type", table_name="audit_logs")

    existing_columns = _column_names("audit_logs")
    with op.batch_alter_table("audit_logs") as batch_op:
        if "signature" in existing_columns:
            batch_op.drop_column("signature")
        if "signature_key_id" in existing_columns:
            batch_op.drop_column("signature_key_id")
        if "assignment_diff" in existing_columns:
            batch_op.drop_column("assignment_diff")
        if "audience_event_type" in existing_columns:
            batch_op.drop_column("audience_event_type")
