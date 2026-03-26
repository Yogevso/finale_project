"""Add attachment metadata columns to support ticket messages.

Revision ID: 20260326_0002
Revises: 20260326_0001
Create Date: 2026-03-26
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260326_0002"
down_revision = "20260326_0001"
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
    if not _column_exists("support_ticket_messages", "file_name"):
        op.add_column("support_ticket_messages", sa.Column("file_name", sa.String(length=255), nullable=True))
    if not _column_exists("support_ticket_messages", "file_size"):
        op.add_column("support_ticket_messages", sa.Column("file_size", sa.Integer(), nullable=True))
    if not _column_exists("support_ticket_messages", "file_mime_type"):
        op.add_column("support_ticket_messages", sa.Column("file_mime_type", sa.String(length=100), nullable=True))
    if not _column_exists("support_ticket_messages", "file_storage_key"):
        op.add_column(
            "support_ticket_messages",
            sa.Column("file_storage_key", sa.String(length=500), nullable=True),
        )
    if not _index_exists("support_ticket_messages", "ix_support_ticket_messages_file_storage_key"):
        op.create_index(
            "ix_support_ticket_messages_file_storage_key",
            "support_ticket_messages",
            ["file_storage_key"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_support_ticket_messages_file_storage_key", table_name="support_ticket_messages")
    op.drop_column("support_ticket_messages", "file_storage_key")
    op.drop_column("support_ticket_messages", "file_mime_type")
    op.drop_column("support_ticket_messages", "file_size")
    op.drop_column("support_ticket_messages", "file_name")
