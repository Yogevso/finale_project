"""AI Assistant — conversation and message tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260315_0024"
down_revision = "20260314_0023"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in set(inspector.get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "assistant_conversations"):
        op.create_table(
            "assistant_conversations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=True),
            sa.Column("title", sa.String(255), nullable=False, server_default="New Chat"),
            sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index(
            "ix_assistant_conv_user_created",
            "assistant_conversations",
            ["user_id", "created_at"],
        )

    if not _table_exists(inspector, "assistant_messages"):
        op.create_table(
            "assistant_messages",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "conversation_id",
                sa.Integer(),
                sa.ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("role", sa.String(20), nullable=False),
            sa.Column("content", sa.Text(), nullable=True),
            sa.Column("tool_calls", sa.Text(), nullable=True),
            sa.Column("tool_call_id", sa.String(100), nullable=True),
            sa.Column("tool_name", sa.String(100), nullable=True),
            sa.Column("token_count", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index(
            "ix_assistant_msg_conv_created",
            "assistant_messages",
            ["conversation_id", "created_at"],
        )


def downgrade() -> None:
    op.drop_table("assistant_messages")
    op.drop_table("assistant_conversations")
