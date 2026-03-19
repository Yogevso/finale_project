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
    # AH-008: document-scoped chats
    with op.batch_alter_table("chats") as batch_op:
        batch_op.add_column(
            sa.Column("document_id", sa.Integer(), nullable=True)
        )
        batch_op.create_index("ix_chats_document_id", ["document_id"])
        batch_op.create_foreign_key(
            "fk_chats_document_id",
            "documents",
            ["document_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # AH-009: context cards in chat messages
    with op.batch_alter_table("chat_messages") as batch_op:
        batch_op.add_column(
            sa.Column("context_json", sa.Text(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("chat_messages") as batch_op:
        batch_op.drop_column("context_json")

    with op.batch_alter_table("chats") as batch_op:
        batch_op.drop_constraint("fk_chats_document_id", type_="foreignkey")
        batch_op.drop_index("ix_chats_document_id")
        batch_op.drop_column("document_id")
