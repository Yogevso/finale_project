"""AH-008/009: Add document_id to chats, context_json to chat_messages.

Revision ID: ah008_chat_unification
Revises: af003_attach_snap
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa

revision = "ah008_chat_unification"
down_revision = "af003_attach_snap"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # AH-008: document-scoped chats
    if "chats" in inspector.get_table_names():
        existing_chat_cols = {c["name"] for c in inspector.get_columns("chats")}
        if "document_id" not in existing_chat_cols:
            op.add_column("chats", sa.Column("document_id", sa.Integer(), nullable=True))
            op.create_index("ix_chats_document_id", "chats", ["document_id"])

    # AH-009: context cards in chat messages
    if "chat_messages" in inspector.get_table_names():
        existing_msg_cols = {c["name"] for c in inspector.get_columns("chat_messages")}
        if "context_json" not in existing_msg_cols:
            op.add_column("chat_messages", sa.Column("context_json", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("chat_messages") as batch_op:
        batch_op.drop_column("context_json")

    with op.batch_alter_table("chats") as batch_op:
        batch_op.drop_constraint("fk_chats_document_id", type_="foreignkey")
        batch_op.drop_index("ix_chats_document_id")
        batch_op.drop_column("document_id")
