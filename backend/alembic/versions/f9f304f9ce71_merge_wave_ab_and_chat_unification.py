"""Lightweight migration script template for managed revisions."""

from alembic import op
import sqlalchemy as sa




# revision identifiers, used by Alembic.
revision = 'f9f304f9ce71'
down_revision = ('wave_ab_001', 'ah008_chat_unification')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
