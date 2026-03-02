"""Add scheduled publish columns to versions table

Revision ID: 20260301_0009
Revises: 20260301_0008
Create Date: 2026-03-01 10:00:00

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = '20260301_0009'
down_revision = '20260301_0008'
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in set(inspector.get_table_names())


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "versions"):
        return

    with op.batch_alter_table("versions", schema=None) as batch_op:
        if not _has_column(inspector, "versions", "scheduled_publish_at"):
            batch_op.add_column(
                sa.Column("scheduled_publish_at", sa.DateTime(), nullable=True)
            )
        if not _has_column(inspector, "versions", "scheduled_publish_audience_validated_at"):
            batch_op.add_column(
                sa.Column("scheduled_publish_audience_validated_at", sa.DateTime(), nullable=True)
            )
        if not _has_index(inspector, "versions", "ix_versions_scheduled_publish_at"):
            batch_op.create_index("ix_versions_scheduled_publish_at", ["scheduled_publish_at"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "versions"):
        return

    with op.batch_alter_table("versions", schema=None) as batch_op:
        if _has_index(inspector, "versions", "ix_versions_scheduled_publish_at"):
            batch_op.drop_index("ix_versions_scheduled_publish_at")
        if _has_column(inspector, "versions", "scheduled_publish_audience_validated_at"):
            batch_op.drop_column("scheduled_publish_audience_validated_at")
        if _has_column(inspector, "versions", "scheduled_publish_at"):
            batch_op.drop_column("scheduled_publish_at")
