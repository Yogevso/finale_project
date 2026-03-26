"""Hash invitation tokens at rest and sanitize invitation messages.

Revision ID: 20260326_0001
Revises: 20260322_0001
Create Date: 2026-03-26
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.auth_context.invitation_tokens import (
    hash_invitation_token,
    looks_like_invitation_token_hash,
)
from app.utils.sanitization import sanitize_plain_text

revision = "20260326_0001"
down_revision = "20260322_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    invitation_table = sa.table(
        "invitations",
        sa.column("id", sa.Integer()),
        sa.column("token", sa.String(length=255)),
        sa.column("message", sa.Text()),
    )
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(
            invitation_table.c.id,
            invitation_table.c.token,
            invitation_table.c.message,
        )
    ).mappings()

    for row in rows:
        updates: dict[str, object] = {}
        token = row["token"]
        if token and not looks_like_invitation_token_hash(token):
            updates["token"] = hash_invitation_token(token)

        sanitized_message = sanitize_plain_text(row["message"])
        if sanitized_message != row["message"]:
            updates["message"] = sanitized_message

        if updates:
            connection.execute(
                invitation_table.update()
                .where(invitation_table.c.id == row["id"])
                .values(**updates)
            )


def downgrade() -> None:
    # Irreversible: plaintext invitation tokens cannot be recovered from hashes.
    pass
