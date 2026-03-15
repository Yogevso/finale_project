"""add context_document_ids column to assistant conversations

Revision ID: 20260316_0035
Revises: 20260316_0030
"""

from alembic import op
import sqlalchemy as sa

revision = "20260316_0035"
down_revision = "20260316_0030"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(f"PRAGMA table_info({table})"))
    return any(row[1] == column for row in result)


def upgrade() -> None:
    if not _column_exists("assistant_conversations", "context_document_ids"):
        op.add_column(
            "assistant_conversations",
            sa.Column("context_document_ids", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("assistant_conversations", "context_document_ids")
