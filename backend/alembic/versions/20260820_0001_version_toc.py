"""Store each version's table of contents beside its HTML.

Revision ID: 20260820_0001
Revises: 20260419_0001
Create Date: 2026-08-20

The contents panel derived its entries by scraping the rendered HTML in the
browser, which is why it carried no page numbers: nothing in the stored document
ever held them. The structure is known at conversion time - a DOCX states it
outright on the contents page Word generates - so it is stored next to the
content it describes, and rendered HTML stops being the place structure is
inferred from.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260820_0001"
down_revision = "20260419_0001"
branch_labels = None
depends_on = None

_TABLE = "versions"
_COLUMN = "toc_json"


def _has_column(inspector: sa.Inspector, table: str, column: str) -> bool:
    if table not in inspector.get_table_names():
        return False
    return any(item["name"] == column for item in inspector.get_columns(table))


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if _has_column(inspector, _TABLE, _COLUMN):
        return
    op.add_column(_TABLE, sa.Column(_COLUMN, sa.Text(), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not _has_column(inspector, _TABLE, _COLUMN):
        return
    op.drop_column(_TABLE, _COLUMN)
