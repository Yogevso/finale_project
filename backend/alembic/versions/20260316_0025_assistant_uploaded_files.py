"""AI Assistant — uploaded files table."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260316_0025"
down_revision = "20260315_0024"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in set(inspector.get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "assistant_uploaded_files"):
        op.create_table(
            "assistant_uploaded_files",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column(
                "conversation_id",
                sa.Integer(),
                sa.ForeignKey("assistant_conversations.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("filename", sa.String(255), nullable=False),
            sa.Column("original_filename", sa.String(255), nullable=False),
            sa.Column("mime_type", sa.String(100), nullable=False),
            sa.Column("file_size", sa.Integer(), nullable=False),
            sa.Column("storage_path", sa.String(500), nullable=False),
            sa.Column("extracted_text", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index(
            "ix_assistant_file_user",
            "assistant_uploaded_files",
            ["user_id"],
        )


def downgrade() -> None:
    op.drop_index("ix_assistant_file_user", table_name="assistant_uploaded_files")
    op.drop_table("assistant_uploaded_files")
