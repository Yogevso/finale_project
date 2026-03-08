"""Merge concurrent heads after auth and thumbnail branches

Revision ID: 20260308_0015
Revises: 20250302_thumb, 20260308_0014
Create Date: 2026-03-08 15:40:00
"""

from __future__ import annotations

# revision identifiers, used by Alembic.
revision = "20260308_0015"
down_revision = ("20250302_thumb", "20260308_0014")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge migration only; no schema changes.
    pass


def downgrade() -> None:
    # Split back into the two previous branch heads.
    pass
