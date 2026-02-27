"""Managed migration for idempotency key persistence."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260227_0005"
down_revision = "20260227_0004"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in set(inspector.get_table_names())


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "idempotency_keys"):
        op.create_table(
            "idempotency_keys",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("idempotency_key", sa.String(length=255), nullable=False),
            sa.Column("method", sa.String(length=10), nullable=False),
            sa.Column("path", sa.String(length=500), nullable=False),
            sa.Column("user_scope", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("request_hash", sa.String(length=64), nullable=False),
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default="processing",
            ),
            sa.Column("response_status", sa.Integer(), nullable=True),
            sa.Column("response_body", sa.Text(), nullable=True),
            sa.Column("response_content_type", sa.String(length=120), nullable=True),
            sa.Column("processing_started_at", sa.DateTime(), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "idempotency_key",
                "method",
                "path",
                "user_scope",
                name="uq_idempotency_scope",
            ),
        )
        inspector = sa.inspect(bind)

    if not _index_exists(inspector, "idempotency_keys", "ix_idempotency_keys_idempotency_key"):
        op.create_index(
            "ix_idempotency_keys_idempotency_key",
            "idempotency_keys",
            ["idempotency_key"],
            unique=False,
        )
    if not _index_exists(inspector, "idempotency_keys", "ix_idempotency_keys_status"):
        op.create_index(
            "ix_idempotency_keys_status",
            "idempotency_keys",
            ["status"],
            unique=False,
        )
    if not _index_exists(inspector, "idempotency_keys", "ix_idempotency_keys_user_id"):
        op.create_index(
            "ix_idempotency_keys_user_id",
            "idempotency_keys",
            ["user_id"],
            unique=False,
        )
    if not _index_exists(inspector, "idempotency_keys", "ix_idempotency_keys_created_at"):
        op.create_index(
            "ix_idempotency_keys_created_at",
            "idempotency_keys",
            ["created_at"],
            unique=False,
        )


def downgrade() -> None:
    """Table is retained for backward compatibility."""
    pass
