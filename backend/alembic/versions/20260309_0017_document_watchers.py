"""Add document_watchers table

Revision ID: 20260309_0017
Revises: 20260308_0016
Create Date: 2026-03-09 13:15:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260309_0017"
down_revision = "20260308_0016"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name)


def upgrade() -> None:
    if _table_exists("document_watchers"):
        return

    op.create_table(
        "document_watchers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "user_id",
            "document_id",
            name="uq_document_watchers_user_document",
        ),
    )
    op.create_index(
        "ix_document_watchers_user_id",
        "document_watchers",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_watchers_document_id",
        "document_watchers",
        ["document_id"],
        unique=False,
    )


def downgrade() -> None:
    if not _table_exists("document_watchers"):
        return

    op.drop_index("ix_document_watchers_document_id", table_name="document_watchers")
    op.drop_index("ix_document_watchers_user_id", table_name="document_watchers")
    op.drop_table("document_watchers")
