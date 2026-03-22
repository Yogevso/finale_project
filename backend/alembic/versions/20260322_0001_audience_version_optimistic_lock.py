"""Add audience_version to Document and audience_version_snapshot to ReviewRequest

Revision ID: 20260322_0001
Revises: h14_consolidate_platform
Create Date: 2026-03-22
"""

from alembic import op
import sqlalchemy as sa

revision = "20260322_0001"
down_revision = "h14_consolidate_platform"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("audience_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "review_requests",
        sa.Column("audience_version_snapshot", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("review_requests", "audience_version_snapshot")
    op.drop_column("documents", "audience_version")
