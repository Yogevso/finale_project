"""C13: Make Document.tenant_id NOT NULL.

Revision ID: c13_doc_tenant_not_null
Revises: f9f304f9ce71
Create Date: 2026-03-20
"""

from alembic import op
import sqlalchemy as sa

revision = "c13_doc_tenant_not_null"
down_revision = "f9f304f9ce71"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Skip if documents table doesn't have tenant_id column (minimal legacy schemas)
    if "documents" not in inspector.get_table_names():
        return
    existing_cols = {c["name"] for c in inspector.get_columns("documents")}
    if "tenant_id" not in existing_cols:
        return

    # First, assign orphaned documents (tenant_id IS NULL) to tenant 1 (default)
    op.execute("UPDATE documents SET tenant_id = 1 WHERE tenant_id IS NULL")

    # Then make the column NOT NULL
    with op.batch_alter_table("documents") as batch_op:
        batch_op.alter_column(
            "tenant_id",
            existing_type=sa.Integer(),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.alter_column(
            "tenant_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
