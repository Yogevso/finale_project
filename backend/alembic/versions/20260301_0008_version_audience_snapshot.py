"""Add audience snapshot fields to versions table.

Revision ID: 20260301_0008
Revises: 20260301_0007
Create Date: 2026-03-01

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260301_0008"
down_revision = "20260301_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add audience snapshot columns to versions table."""
    op.add_column(
        "versions",
        sa.Column("audience_visibility_snapshot", sa.String(50), nullable=True),
    )
    op.add_column(
        "versions",
        sa.Column("audience_company_ids_snapshot", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove audience snapshot columns from versions table."""
    op.drop_column("versions", "audience_company_ids_snapshot")
    op.drop_column("versions", "audience_visibility_snapshot")
