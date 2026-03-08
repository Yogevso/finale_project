"""Add login anomaly tracking columns and security events table

Revision ID: 20260308_0012
Revises: 20260308_0011
Create Date: 2026-03-08 23:40:00

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260308_0012"
down_revision = "20260308_0011"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in set(inspector.get_table_names())


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "users"):
        with op.batch_alter_table("users", schema=None) as batch_op:
            if not _has_column(inspector, "users", "last_login_ip"):
                batch_op.add_column(sa.Column("last_login_ip", sa.String(length=45), nullable=True))
            if not _has_column(inspector, "users", "last_login_user_agent"):
                batch_op.add_column(
                    sa.Column("last_login_user_agent", sa.String(length=512), nullable=True)
                )

    if not _table_exists(inspector, "security_events"):
        op.create_table(
            "security_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("event_type", sa.String(length=64), nullable=False),
            sa.Column("ip_address", sa.String(length=45), nullable=True),
            sa.Column("user_agent", sa.String(length=512), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_security_events_id", "security_events", ["id"], unique=False)
        op.create_index(
            "ix_security_events_user_id", "security_events", ["user_id"], unique=False
        )
        op.create_index(
            "ix_security_events_event_type", "security_events", ["event_type"], unique=False
        )
        op.create_index(
            "ix_security_events_created_at", "security_events", ["created_at"], unique=False
        )
    else:
        if not _index_exists(inspector, "security_events", "ix_security_events_id"):
            op.create_index("ix_security_events_id", "security_events", ["id"], unique=False)
        if not _index_exists(inspector, "security_events", "ix_security_events_user_id"):
            op.create_index(
                "ix_security_events_user_id", "security_events", ["user_id"], unique=False
            )
        if not _index_exists(inspector, "security_events", "ix_security_events_event_type"):
            op.create_index(
                "ix_security_events_event_type",
                "security_events",
                ["event_type"],
                unique=False,
            )
        if not _index_exists(inspector, "security_events", "ix_security_events_created_at"):
            op.create_index(
                "ix_security_events_created_at",
                "security_events",
                ["created_at"],
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "security_events"):
        for index_name in (
            "ix_security_events_created_at",
            "ix_security_events_event_type",
            "ix_security_events_user_id",
            "ix_security_events_id",
        ):
            if _index_exists(inspector, "security_events", index_name):
                op.drop_index(index_name, table_name="security_events")
        op.drop_table("security_events")

    if _table_exists(inspector, "users"):
        with op.batch_alter_table("users", schema=None) as batch_op:
            if _has_column(inspector, "users", "last_login_user_agent"):
                batch_op.drop_column("last_login_user_agent")
            if _has_column(inspector, "users", "last_login_ip"):
                batch_op.drop_column("last_login_ip")
