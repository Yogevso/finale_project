"""Add user sessions table for active session management

Revision ID: 20260308_0013
Revises: 20260308_0012
Create Date: 2026-03-08 23:58:00

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260308_0013"
down_revision = "20260308_0012"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in set(inspector.get_table_names())


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "user_sessions"):
        op.create_table(
            "user_sessions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("session_token_hash", sa.String(length=64), nullable=False),
            sa.Column("ip_address", sa.String(length=45), nullable=True),
            sa.Column("user_agent", sa.String(length=512), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("last_active_at", sa.DateTime(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("session_token_hash"),
        )
        op.create_index("ix_user_sessions_id", "user_sessions", ["id"], unique=False)
        op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"], unique=False)
        op.create_index(
            "ix_user_sessions_session_token_hash",
            "user_sessions",
            ["session_token_hash"],
            unique=True,
        )
        op.create_index(
            "ix_user_sessions_created_at", "user_sessions", ["created_at"], unique=False
        )
        op.create_index(
            "ix_user_sessions_last_active_at",
            "user_sessions",
            ["last_active_at"],
            unique=False,
        )
        op.create_index(
            "ix_user_sessions_revoked_at", "user_sessions", ["revoked_at"], unique=False
        )
    else:
        if not _index_exists(inspector, "user_sessions", "ix_user_sessions_id"):
            op.create_index("ix_user_sessions_id", "user_sessions", ["id"], unique=False)
        if not _index_exists(inspector, "user_sessions", "ix_user_sessions_user_id"):
            op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"], unique=False)
        if not _index_exists(inspector, "user_sessions", "ix_user_sessions_session_token_hash"):
            op.create_index(
                "ix_user_sessions_session_token_hash",
                "user_sessions",
                ["session_token_hash"],
                unique=True,
            )
        if not _index_exists(inspector, "user_sessions", "ix_user_sessions_created_at"):
            op.create_index(
                "ix_user_sessions_created_at",
                "user_sessions",
                ["created_at"],
                unique=False,
            )
        if not _index_exists(inspector, "user_sessions", "ix_user_sessions_last_active_at"):
            op.create_index(
                "ix_user_sessions_last_active_at",
                "user_sessions",
                ["last_active_at"],
                unique=False,
            )
        if not _index_exists(inspector, "user_sessions", "ix_user_sessions_revoked_at"):
            op.create_index(
                "ix_user_sessions_revoked_at",
                "user_sessions",
                ["revoked_at"],
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "user_sessions"):
        for index_name in (
            "ix_user_sessions_revoked_at",
            "ix_user_sessions_last_active_at",
            "ix_user_sessions_created_at",
            "ix_user_sessions_session_token_hash",
            "ix_user_sessions_user_id",
            "ix_user_sessions_id",
        ):
            if _index_exists(inspector, "user_sessions", index_name):
                op.drop_index(index_name, table_name="user_sessions")
        op.drop_table("user_sessions")
