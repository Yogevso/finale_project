"""Track invitation email delivery metadata.

Revision ID: 20260327_0001
Revises: 20260326_0002
Create Date: 2026-03-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260327_0001"
down_revision = "20260326_0002"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(existing["name"] == column for existing in inspector.get_columns(table))


def _index_exists(table: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(existing["name"] == index_name for existing in inspector.get_indexes(table))


def upgrade() -> None:
    status_enum = sa.Enum(
        "pending",
        "sent",
        "failed",
        "suppressed",
        name="invitationemaildeliverystatus",
    )
    status_enum.create(op.get_bind(), checkfirst=True)

    if not _column_exists("invitations", "email_delivery_status"):
        op.add_column(
            "invitations",
            sa.Column(
                "email_delivery_status",
                status_enum,
                nullable=False,
                server_default="pending",
            ),
        )
    if not _column_exists("invitations", "email_delivery_attempt_count"):
        op.add_column(
            "invitations",
            sa.Column(
                "email_delivery_attempt_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )
    if not _column_exists("invitations", "email_last_attempted_at"):
        op.add_column("invitations", sa.Column("email_last_attempted_at", sa.DateTime(), nullable=True))
    if not _column_exists("invitations", "email_last_sent_at"):
        op.add_column("invitations", sa.Column("email_last_sent_at", sa.DateTime(), nullable=True))
    if not _column_exists("invitations", "email_last_error"):
        op.add_column("invitations", sa.Column("email_last_error", sa.Text(), nullable=True))
    if not _column_exists("invitations", "email_last_subject"):
        op.add_column("invitations", sa.Column("email_last_subject", sa.String(length=255), nullable=True))
    if not _column_exists("invitations", "email_last_sender_email"):
        op.add_column(
            "invitations",
            sa.Column("email_last_sender_email", sa.String(length=255), nullable=True),
        )
    if not _column_exists("invitations", "email_last_sender_name"):
        op.add_column(
            "invitations",
            sa.Column("email_last_sender_name", sa.String(length=255), nullable=True),
        )

    op.execute(
        sa.text(
            """
            UPDATE invitations
            SET email_delivery_status = 'pending'
            WHERE email_delivery_status IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE invitations
            SET email_delivery_attempt_count = 0
            WHERE email_delivery_attempt_count IS NULL OR email_delivery_attempt_count < 0
            """
        )
    )

    if not _index_exists("invitations", "ix_invitations_email_delivery_status"):
        op.create_index(
            "ix_invitations_email_delivery_status",
            "invitations",
            ["email_delivery_status"],
        )


def downgrade() -> None:
    if _index_exists("invitations", "ix_invitations_email_delivery_status"):
        op.drop_index("ix_invitations_email_delivery_status", table_name="invitations")
    for column_name in [
        "email_last_sender_name",
        "email_last_sender_email",
        "email_last_subject",
        "email_last_error",
        "email_last_sent_at",
        "email_last_attempted_at",
        "email_delivery_attempt_count",
        "email_delivery_status",
    ]:
        if _column_exists("invitations", column_name):
            op.drop_column("invitations", column_name)

    status_enum = sa.Enum(
        "pending",
        "sent",
        "failed",
        "suppressed",
        name="invitationemaildeliverystatus",
    )
    status_enum.drop(op.get_bind(), checkfirst=True)
