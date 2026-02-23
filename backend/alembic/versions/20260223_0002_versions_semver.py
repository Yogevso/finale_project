"""Managed migration for versions semantic-version columns and normalization."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260223_0002"
down_revision = "20260223_0001"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in set(inspector.get_table_names())


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "versions"):
        return

    with op.batch_alter_table("versions") as batch_op:
        if not _has_column(inspector, "versions", "semantic_version"):
            batch_op.add_column(sa.Column("semantic_version", sa.String(length=32), nullable=True))

        if not _has_column(inspector, "versions", "bump_type"):
            batch_op.add_column(
                sa.Column(
                    "bump_type",
                    sa.String(length=10),
                    nullable=False,
                    server_default="PATCH",
                )
            )

        if not _has_column(inspector, "versions", "published_by"):
            batch_op.add_column(sa.Column("published_by", sa.Integer(), nullable=True))

    inspector = sa.inspect(bind)
    if not _has_index(inspector, "versions", "ix_versions_semantic_version"):
        op.create_index("ix_versions_semantic_version", "versions", ["semantic_version"], unique=False)

    op.execute(
        sa.text(
            "UPDATE versions "
            "SET semantic_version = CASE "
            "WHEN version_number IS NULL OR version_number < 1 THEN '1.0.0' "
            "ELSE CAST(version_number AS TEXT) || '.0.0' END "
            "WHERE semantic_version IS NULL OR TRIM(semantic_version) = ''"
        )
    )

    op.execute(
        sa.text(
            "UPDATE versions "
            "SET bump_type = CASE LOWER(COALESCE(bump_type, '')) "
            "WHEN 'major' THEN 'MAJOR' "
            "WHEN 'minor' THEN 'MINOR' "
            "WHEN 'patch' THEN 'PATCH' "
            "ELSE COALESCE(bump_type, 'PATCH') END"
        )
    )


def downgrade() -> None:
    """Columns are intentionally kept for backward compatibility on SQLite deployments."""
    pass
