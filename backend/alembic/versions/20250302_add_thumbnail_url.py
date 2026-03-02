"""add thumbnail_url to documents

Revision ID: 20250302_thumb
Revises: 20260301_0009
Create Date: 2025-03-02
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20250302_thumb"
down_revision = "20260301_0009"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in set(inspector.get_table_names())


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "documents"):
        return

    with op.batch_alter_table("documents") as batch:
        if not _has_column(inspector, "documents", "thumbnail_url"):
            batch.add_column(sa.Column("thumbnail_url", sa.String(500), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "documents"):
        return

    with op.batch_alter_table("documents") as batch:
        if _has_column(inspector, "documents", "thumbnail_url"):
            batch.drop_column("thumbnail_url")
