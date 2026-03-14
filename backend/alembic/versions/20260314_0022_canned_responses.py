"""Add canned_responses table (Wave X.1 — X1-103)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260314_0022"
down_revision = "9fa05242e3a9"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in set(inspector.get_table_names())


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return index_name in {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "canned_responses"):
        op.create_table(
            "canned_responses",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("category", sa.String(100), nullable=True),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )

    # Refresh inspector after possible table creation
    inspector = sa.inspect(bind)

    for ix_name, columns in [
        ("ix_canned_responses_id", ["id"]),
        ("ix_canned_responses_category", ["category"]),
        ("ix_canned_responses_created_by", ["created_by"]),
        ("ix_canned_responses_tenant_id", ["tenant_id"]),
    ]:
        if not _index_exists(inspector, "canned_responses", ix_name):
            op.create_index(ix_name, "canned_responses", columns)


def downgrade() -> None:
    op.drop_index("ix_canned_responses_tenant_id", "canned_responses")
    op.drop_index("ix_canned_responses_created_by", "canned_responses")
    op.drop_index("ix_canned_responses_category", "canned_responses")
    op.drop_index("ix_canned_responses_id", "canned_responses")
    op.drop_table("canned_responses")
