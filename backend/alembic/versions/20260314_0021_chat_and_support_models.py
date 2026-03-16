"""Add chat and support ticket models (Wave X.1).

Creates tables for internal messaging (chats, participants, messages)
and customer support (tickets, ticket messages, ticket assignments).
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260314_0021"
down_revision = "20260311_0020"
branch_labels = None
depends_on = None


def _table_exists(name: str) -> bool:
    """Check if table already exists (handles create_all + migration overlap)."""
    bind = op.get_bind()
    return bind.dialect.has_table(bind, name)


def upgrade() -> None:
    # --- Internal Chat tables ---
    if not _table_exists("chats"):
        op.create_table(
            "chats",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("type", sa.String(20), nullable=False),
            sa.Column("name", sa.String(255), nullable=True),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("last_message_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_chats_id", "chats", ["id"])
        op.create_index("ix_chats_created_by", "chats", ["created_by"])
        op.create_index("ix_chats_tenant_id", "chats", ["tenant_id"])
        op.create_index("ix_chats_last_message_at", "chats", ["last_message_at"])

    if not _table_exists("chat_participants"):
        op.create_table(
            "chat_participants",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("chat_id", sa.Integer(), sa.ForeignKey("chats.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("role", sa.String(20), nullable=False, server_default="member"),
            sa.Column("joined_at", sa.DateTime(), nullable=False),
            sa.Column("last_read_at", sa.DateTime(), nullable=True),
            sa.Column("is_muted", sa.Boolean(), nullable=False, server_default="0"),
            sa.UniqueConstraint("chat_id", "user_id", name="uq_chat_participant"),
        )
        op.create_index("ix_chat_participants_id", "chat_participants", ["id"])
        op.create_index("ix_chat_participants_chat_id", "chat_participants", ["chat_id"])
        op.create_index("ix_chat_participants_user_id", "chat_participants", ["user_id"])

    if not _table_exists("chat_messages"):
        op.create_table(
            "chat_messages",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("chat_id", sa.Integer(), sa.ForeignKey("chats.id", ondelete="CASCADE"), nullable=False),
            sa.Column("sender_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("message_type", sa.String(20), nullable=False, server_default="text"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_chat_messages_id", "chat_messages", ["id"])
        op.create_index("ix_chat_messages_chat_id", "chat_messages", ["chat_id"])
        op.create_index("ix_chat_messages_sender_id", "chat_messages", ["sender_id"])
        op.create_index("ix_chat_messages_created_at", "chat_messages", ["created_at"])
        op.create_index("ix_chat_messages_chat_created", "chat_messages", ["chat_id", "created_at"])

    # --- Support Ticket tables ---
    if not _table_exists("support_tickets"):
        op.create_table(
            "support_tickets",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("customer_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("subject", sa.String(500), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="open"),
            sa.Column("priority", sa.String(20), nullable=False, server_default="normal"),
            sa.Column("category", sa.String(100), nullable=True),
            sa.Column("feedback_id", sa.Integer(), sa.ForeignKey("feedbacks.id"), nullable=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_support_tickets_id", "support_tickets", ["id"])
        op.create_index("ix_support_tickets_customer_id", "support_tickets", ["customer_id"])
        op.create_index("ix_support_tickets_status", "support_tickets", ["status"])
        op.create_index("ix_support_tickets_priority", "support_tickets", ["priority"])
        op.create_index("ix_support_tickets_tenant_id", "support_tickets", ["tenant_id"])
        op.create_index("ix_support_tickets_category", "support_tickets", ["category"])
        op.create_index("ix_support_tickets_feedback_id", "support_tickets", ["feedback_id"])

    if not _table_exists("support_ticket_messages"):
        op.create_table(
            "support_ticket_messages",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("ticket_id", sa.Integer(), sa.ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False),
            sa.Column("sender_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("sender_type", sa.String(20), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("is_internal_note", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_support_ticket_messages_id", "support_ticket_messages", ["id"])
        op.create_index("ix_support_ticket_messages_ticket_id", "support_ticket_messages", ["ticket_id"])
        op.create_index("ix_support_ticket_messages_sender_id", "support_ticket_messages", ["sender_id"])
        op.create_index("ix_support_ticket_messages_created_at", "support_ticket_messages", ["created_at"])
        op.create_index("ix_support_messages_ticket_created", "support_ticket_messages", ["ticket_id", "created_at"])

    if not _table_exists("support_ticket_assignments"):
        op.create_table(
            "support_ticket_assignments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("ticket_id", sa.Integer(), sa.ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False),
            sa.Column("agent_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("assigned_at", sa.DateTime(), nullable=False),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="0"),
            sa.UniqueConstraint("ticket_id", "agent_id", name="uq_ticket_assignment"),
        )
        op.create_index("ix_support_ticket_assignments_id", "support_ticket_assignments", ["id"])
        op.create_index("ix_support_ticket_assignments_ticket_id", "support_ticket_assignments", ["ticket_id"])
        op.create_index("ix_support_ticket_assignments_agent_id", "support_ticket_assignments", ["agent_id"])


def downgrade() -> None:
    op.drop_table("support_ticket_assignments")
    op.drop_table("support_ticket_messages")
    op.drop_table("support_tickets")
    op.drop_table("chat_messages")
    op.drop_table("chat_participants")
    op.drop_table("chats")
