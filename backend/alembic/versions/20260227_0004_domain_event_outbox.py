"""Managed migration for durable domain-event outbox."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260227_0004"
down_revision = "20260224_0003"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in set(inspector.get_table_names())


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "domain_event_outbox"):
        op.create_table(
            "domain_event_outbox",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("event_type", sa.String(length=120), nullable=False),
            sa.Column("event_key", sa.String(length=255), nullable=True),
            sa.Column("payload_json", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
            sa.Column("next_attempt_at", sa.DateTime(), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("claimed_at", sa.DateTime(), nullable=True),
            sa.Column("processed_at", sa.DateTime(), nullable=True),
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
        )
        inspector = sa.inspect(bind)

    if not _index_exists(inspector, "domain_event_outbox", "ix_domain_event_outbox_event_type"):
        op.create_index(
            "ix_domain_event_outbox_event_type",
            "domain_event_outbox",
            ["event_type"],
            unique=False,
        )
    if not _index_exists(inspector, "domain_event_outbox", "ix_domain_event_outbox_event_key"):
        op.create_index(
            "ix_domain_event_outbox_event_key",
            "domain_event_outbox",
            ["event_key"],
            unique=True,
        )
    if not _index_exists(inspector, "domain_event_outbox", "ix_domain_event_outbox_status"):
        op.create_index(
            "ix_domain_event_outbox_status",
            "domain_event_outbox",
            ["status"],
            unique=False,
        )
    if not _index_exists(inspector, "domain_event_outbox", "ix_domain_event_outbox_next_attempt_at"):
        op.create_index(
            "ix_domain_event_outbox_next_attempt_at",
            "domain_event_outbox",
            ["next_attempt_at"],
            unique=False,
        )
    if not _index_exists(inspector, "domain_event_outbox", "ix_domain_event_outbox_created_at"):
        op.create_index(
            "ix_domain_event_outbox_created_at",
            "domain_event_outbox",
            ["created_at"],
            unique=False,
        )


def downgrade() -> None:
    """Table is retained for backward compatibility."""
    pass
