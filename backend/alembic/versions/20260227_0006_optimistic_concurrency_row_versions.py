"""Managed migration for optimistic concurrency row-version columns."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260227_0006"
down_revision = "20260227_0005"
branch_labels = None
depends_on = None


def _column_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    try:
        return column_name in {column["name"] for column in inspector.get_columns(table_name)}
    except sa.exc.NoSuchTableError:
        return False


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _column_exists(inspector, "documents", "row_version"):
        op.add_column(
            "documents",
            sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        )
        op.execute("UPDATE documents SET row_version = 1 WHERE row_version IS NULL OR row_version < 1")

    if not _column_exists(inspector, "versions", "row_version"):
        op.add_column(
            "versions",
            sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        )
        op.execute("UPDATE versions SET row_version = 1 WHERE row_version IS NULL OR row_version < 1")


def downgrade() -> None:
    """Columns are retained for compatibility and rollback safety."""
    pass
