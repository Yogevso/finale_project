"""Add document due dates and review SLA tracking fields

Revision ID: 20260309_0018
Revises: 20260309_0017
Create Date: 2026-03-09 18:20:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260309_0018"
down_revision = "20260309_0017"
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
    if not _column_exists("documents", "due_date"):
        op.add_column("documents", sa.Column("due_date", sa.Date(), nullable=True))
    if not _index_exists("documents", "ix_documents_due_date"):
        op.create_index("ix_documents_due_date", "documents", ["due_date"], unique=False)

    if _table_exists("review_requests"):
        if not _column_exists("review_requests", "reviewer_reminded_at"):
            op.add_column(
                "review_requests",
                sa.Column("reviewer_reminded_at", sa.DateTime(), nullable=True),
            )
        if not _column_exists("review_requests", "manager_escalated_at"):
            op.add_column(
                "review_requests",
                sa.Column("manager_escalated_at", sa.DateTime(), nullable=True),
            )


def downgrade() -> None:
    if _table_exists("review_requests"):
        if _column_exists("review_requests", "manager_escalated_at"):
            op.drop_column("review_requests", "manager_escalated_at")
        if _column_exists("review_requests", "reviewer_reminded_at"):
            op.drop_column("review_requests", "reviewer_reminded_at")

    if _index_exists("documents", "ix_documents_due_date"):
        op.drop_index("ix_documents_due_date", table_name="documents")
    if _column_exists("documents", "due_date"):
        op.drop_column("documents", "due_date")
