"""Add document delete recovery-window fields.

Revision ID: 20260328_0001
Revises: 20260327_0001
Create Date: 2026-03-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260328_0001"
down_revision = "20260327_0001"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(existing["name"] == column for existing in inspector.get_columns(table))


def _index_exists(table: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(existing["name"] == index_name for existing in inspector.get_indexes(table))


def upgrade() -> None:
    if not _column_exists("documents", "deleted_by"):
        op.add_column("documents", sa.Column("deleted_by", sa.Integer(), nullable=True))
    if not _column_exists("documents", "deleted_at"):
        op.add_column("documents", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    if not _column_exists("documents", "purge_at"):
        op.add_column("documents", sa.Column("purge_at", sa.DateTime(), nullable=True))

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys("documents")}
    if "fk_documents_deleted_by_users" not in foreign_keys:
        op.create_foreign_key(
            "fk_documents_deleted_by_users",
            "documents",
            "users",
            ["deleted_by"],
            ["id"],
        )

    if not _index_exists("documents", "ix_documents_deleted_by"):
        op.create_index("ix_documents_deleted_by", "documents", ["deleted_by"])
    if not _index_exists("documents", "ix_documents_deleted_at"):
        op.create_index("ix_documents_deleted_at", "documents", ["deleted_at"])
    if not _index_exists("documents", "ix_documents_purge_at"):
        op.create_index("ix_documents_purge_at", "documents", ["purge_at"])


def downgrade() -> None:
    for index_name in [
        "ix_documents_purge_at",
        "ix_documents_deleted_at",
        "ix_documents_deleted_by",
    ]:
        if _index_exists("documents", index_name):
            op.drop_index(index_name, table_name="documents")

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys("documents")}
    if "fk_documents_deleted_by_users" in foreign_keys:
        op.drop_constraint("fk_documents_deleted_by_users", "documents", type_="foreignkey")

    for column_name in ["purge_at", "deleted_at", "deleted_by"]:
        if _column_exists("documents", column_name):
            op.drop_column("documents", column_name)
