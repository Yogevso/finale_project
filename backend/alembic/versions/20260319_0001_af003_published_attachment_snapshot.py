"""AF-003: Add published_attachment_ids_snapshot to versions table.

Revision ID: af003_attach_snap
Revises: 20260318_0001
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa

revision = "af003_attach_snap"
down_revision = None  # standalone — run after existing head
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("versions") as batch_op:
        batch_op.add_column(
            sa.Column("published_attachment_ids_snapshot", sa.Text(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("versions") as batch_op:
        batch_op.drop_column("published_attachment_ids_snapshot")
