"""add file fields to chat_messages

Revision ID: 9fa05242e3a9
Revises: 20260314_0021
Create Date: 2025-01-01
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9fa05242e3a9'
down_revision = '20260314_0021'
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(c["name"] == column for c in inspector.get_columns(table))


def upgrade() -> None:
    if not _column_exists("chat_messages", "file_url"):
        op.add_column('chat_messages', sa.Column('file_url', sa.String(length=500), nullable=True))
    if not _column_exists("chat_messages", "file_name"):
        op.add_column('chat_messages', sa.Column('file_name', sa.String(length=255), nullable=True))
    if not _column_exists("chat_messages", "file_size"):
        op.add_column('chat_messages', sa.Column('file_size', sa.Integer(), nullable=True))
    if not _column_exists("chat_messages", "file_mime_type"):
        op.add_column('chat_messages', sa.Column('file_mime_type', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('chat_messages', 'file_mime_type')
    op.drop_column('chat_messages', 'file_size')
    op.drop_column('chat_messages', 'file_name')
    op.drop_column('chat_messages', 'file_url')
