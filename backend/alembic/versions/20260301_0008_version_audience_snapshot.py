"""Add audience snapshot fields to versions table.

Revision ID: 20260301_0008
Revises: 20260301_0007
Create Date: 2026-03-01

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260301_0008"
down_revision = "20260301_0007"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in set(inspector.get_table_names())


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "versions"):
        return

    with op.batch_alter_table("versions") as batch_op:
        if not _has_column(inspector, "versions", "audience_visibility_snapshot"):
            batch_op.add_column(
                sa.Column("audience_visibility_snapshot", sa.String(length=50), nullable=True)
            )

        if not _has_column(inspector, "versions", "audience_company_ids_snapshot"):
            batch_op.add_column(
                sa.Column("audience_company_ids_snapshot", sa.Text(), nullable=True)
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "versions"):
        return

    with op.batch_alter_table("versions") as batch_op:
        if _has_column(inspector, "versions", "audience_company_ids_snapshot"):
            batch_op.drop_column("audience_company_ids_snapshot")

        if _has_column(inspector, "versions", "audience_visibility_snapshot"):
            batch_op.drop_column("audience_visibility_snapshot")
