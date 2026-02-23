"""Baseline schema snapshot for managed migrations."""

from __future__ import annotations

# revision identifiers, used by Alembic.
revision = "20260223_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Baseline marker; schema is currently provisioned by ORM + lightweight migrations."""
    pass


def downgrade() -> None:
    """No-op downgrade for baseline marker revision."""
    pass
