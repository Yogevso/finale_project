"""Add scheduled publish columns to versions table

Revision ID: 20260301_0009
Revises: 20260301_0008
Create Date: 2026-03-01 10:00:00

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = '20260301_0009'
down_revision = '20260301_0008'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('versions', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('scheduled_publish_at', sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('scheduled_publish_audience_validated_at', sa.DateTime(), nullable=True)
        )
        batch_op.create_index('ix_versions_scheduled_publish_at', ['scheduled_publish_at'])


def downgrade():
    with op.batch_alter_table('versions', schema=None) as batch_op:
        batch_op.drop_index('ix_versions_scheduled_publish_at')
        batch_op.drop_column('scheduled_publish_audience_validated_at')
        batch_op.drop_column('scheduled_publish_at')
