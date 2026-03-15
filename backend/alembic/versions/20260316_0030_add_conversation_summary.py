"""add summary column to assistant conversations

Revision ID: 20260316_0030
Revises: 20260316_0025
"""

from alembic import op
import sqlalchemy as sa

revision = "20260316_0030"
down_revision = "20260316_0025"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(f"PRAGMA table_info({table})"))
    return any(row[1] == column for row in result)


def upgrade() -> None:
    if not _column_exists("assistant_conversations", "summary"):
        op.add_column(
            "assistant_conversations",
            sa.Column("summary", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    if _column_exists("assistant_conversations", "summary"):
        op.drop_column("assistant_conversations", "summary")
