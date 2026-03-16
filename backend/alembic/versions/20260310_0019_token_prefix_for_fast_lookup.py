"""Add token_prefix column to password_resets for fast indexed lookup

Revision ID: 20260310_0019
Revises: 20260309_0018
Create Date: 2026-03-10 09:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260310_0019"
down_revision = "20260309_0018"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name)


def _column_exists(table_name: str, column_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _index_exists(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    if not _table_exists("password_resets"):
        return
    # Add token_prefix column for indexed lookup (first 8 chars of raw token)
    if not _column_exists("password_resets", "token_prefix"):
        op.add_column(
            "password_resets",
            sa.Column("token_prefix", sa.String(16), nullable=True),
        )
    if not _index_exists("password_resets", "ix_password_resets_token_prefix"):
        op.create_index(
            "ix_password_resets_token_prefix",
            "password_resets",
            ["token_prefix"],
            unique=False,
        )


def downgrade() -> None:
    if _index_exists("password_resets", "ix_password_resets_token_prefix"):
        op.drop_index("ix_password_resets_token_prefix", table_name="password_resets")
    if _column_exists("password_resets", "token_prefix"):
        op.drop_column("password_resets", "token_prefix")
