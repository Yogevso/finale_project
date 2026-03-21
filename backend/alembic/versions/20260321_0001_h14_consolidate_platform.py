"""H-14: Consolidate platform string -> platform_id FK.

For every Document row that has a `platform` string but no `platform_id`,
find-or-create a Platform record and set the FK.  After migration the string
column is kept (for backwards compat) but marked deprecated — it will be
dropped in a future major version once all read paths have migrated.

Revision ID: h14_consolidate_platform
Revises: h13_missing_indexes
Create Date: 2026-03-21
"""

import sqlalchemy as sa
from alembic import op

revision = "h14_consolidate_platform"
down_revision = "h13_missing_indexes"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # 1. Find documents with a platform string but no FK set
    rows = conn.execute(
        sa.text(
            "SELECT id, platform FROM documents "
            "WHERE platform IS NOT NULL AND platform != '' AND platform_id IS NULL"
        )
    ).fetchall()

    if not rows:
        return

    # 2. Build a mapping of platform name -> id from existing Platform table
    existing = conn.execute(sa.text("SELECT id, name FROM platforms")).fetchall()
    # Case-insensitive lookup
    name_to_id: dict[str, int] = {r[1].lower(): r[0] for r in existing}

    for doc_id, platform_name in rows:
        key = platform_name.strip().lower()
        if not key:
            continue

        platform_id = name_to_id.get(key)
        if platform_id is None:
            # Create a new Platform row
            slug = key.replace(" ", "-").replace("/", "-")
            conn.execute(
                sa.text(
                    "INSERT INTO platforms (name, slug, created_at, updated_at) "
                    "VALUES (:name, :slug, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {"name": platform_name.strip(), "slug": slug},
            )
            # Fetch the new id
            result = conn.execute(
                sa.text("SELECT id FROM platforms WHERE slug = :slug"),
                {"slug": slug},
            ).fetchone()
            platform_id = result[0]
            name_to_id[key] = platform_id

        conn.execute(
            sa.text("UPDATE documents SET platform_id = :pid WHERE id = :did"),
            {"pid": platform_id, "did": doc_id},
        )


def downgrade():
    # Nothing to undo — the data migration is additive (sets platform_id that
    # was previously NULL).  The string column was never dropped.
    pass
