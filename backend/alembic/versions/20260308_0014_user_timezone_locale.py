"""Add timezone and locale preferences to users

Revision ID: 20260308_0014
Revises: 20260308_0013
Create Date: 2026-03-08 14:05:00

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260308_0014"
down_revision = "20260308_0013"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in set(inspector.get_table_names())


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "users"):
        with op.batch_alter_table("users", schema=None) as batch_op:
            if not _has_column(inspector, "users", "timezone"):
                batch_op.add_column(
                    sa.Column(
                        "timezone",
                        sa.String(length=64),
                        nullable=False,
                        server_default="UTC",
                    )
                )
            if not _has_column(inspector, "users", "locale"):
                batch_op.add_column(
                    sa.Column(
                        "locale",
                        sa.String(length=10),
                        nullable=False,
                        server_default="en",
                    )
                )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "users"):
        with op.batch_alter_table("users", schema=None) as batch_op:
            if _has_column(inspector, "users", "locale"):
                batch_op.drop_column("locale")
            if _has_column(inspector, "users", "timezone"):
                batch_op.drop_column("timezone")
