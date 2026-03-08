"""Add user profile preference and avatar fields

Revision ID: 20260308_0011
Revises: 20260308_0010
Create Date: 2026-03-08 22:40:00

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "20260308_0011"
down_revision = "20260308_0010"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in set(inspector.get_table_names())


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "users"):
        return

    with op.batch_alter_table("users", schema=None) as batch_op:
        if not _has_column(inspector, "users", "notification_preferences"):
            batch_op.add_column(sa.Column("notification_preferences", sa.JSON(), nullable=True))
        if not _has_column(inspector, "users", "avatar_url"):
            batch_op.add_column(sa.Column("avatar_url", sa.String(length=500), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "users"):
        return

    with op.batch_alter_table("users", schema=None) as batch_op:
        if _has_column(inspector, "users", "avatar_url"):
            batch_op.drop_column("avatar_url")
        if _has_column(inspector, "users", "notification_preferences"):
            batch_op.drop_column("notification_preferences")
