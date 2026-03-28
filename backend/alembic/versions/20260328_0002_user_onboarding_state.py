"""Add per-user onboarding state JSON

Revision ID: 20260328_0002
Revises: 20260328_0001
Create Date: 2026-03-28 15:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op


revision = "20260328_0002"
down_revision = "20260328_0001"
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
        if not _has_column(inspector, "users", "onboarding_state"):
            batch_op.add_column(sa.Column("onboarding_state", sa.JSON(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "users"):
        return

    with op.batch_alter_table("users", schema=None) as batch_op:
        if _has_column(inspector, "users", "onboarding_state"):
            batch_op.drop_column("onboarding_state")
