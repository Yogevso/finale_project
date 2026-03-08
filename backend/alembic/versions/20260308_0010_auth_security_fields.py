"""Add auth security and verification fields to users

Revision ID: 20260308_0010
Revises: 20260301_0009
Create Date: 2026-03-08 22:00:00

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "20260308_0010"
down_revision = "20260301_0009"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in set(inspector.get_table_names())


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "users"):
        return

    with op.batch_alter_table("users", schema=None) as batch_op:
        if not _has_column(inspector, "users", "is_email_verified"):
            batch_op.add_column(
                sa.Column(
                    "is_email_verified",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                )
            )
        if not _has_column(inspector, "users", "email_verification_token_hash"):
            batch_op.add_column(
                sa.Column("email_verification_token_hash", sa.String(length=255), nullable=True)
            )
        if not _has_column(inspector, "users", "email_verification_expires_at"):
            batch_op.add_column(
                sa.Column("email_verification_expires_at", sa.DateTime(), nullable=True)
            )
        if not _has_column(inspector, "users", "failed_login_attempts"):
            batch_op.add_column(
                sa.Column(
                    "failed_login_attempts",
                    sa.Integer(),
                    nullable=False,
                    server_default="0",
                )
            )
        if not _has_column(inspector, "users", "locked_until"):
            batch_op.add_column(sa.Column("locked_until", sa.DateTime(), nullable=True))

    # Preserve access for existing accounts after rollout.
    op.execute(sa.text("UPDATE users SET is_email_verified = 1 WHERE is_email_verified = 0"))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "users"):
        return

    with op.batch_alter_table("users", schema=None) as batch_op:
        if _has_column(inspector, "users", "locked_until"):
            batch_op.drop_column("locked_until")
        if _has_column(inspector, "users", "failed_login_attempts"):
            batch_op.drop_column("failed_login_attempts")
        if _has_column(inspector, "users", "email_verification_expires_at"):
            batch_op.drop_column("email_verification_expires_at")
        if _has_column(inspector, "users", "email_verification_token_hash"):
            batch_op.drop_column("email_verification_token_hash")
        if _has_column(inspector, "users", "is_email_verified"):
            batch_op.drop_column("is_email_verified")
