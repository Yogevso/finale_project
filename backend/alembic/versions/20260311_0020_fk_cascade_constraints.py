"""Add ON DELETE CASCADE/SET NULL to critical foreign key relationships (Y15-028).

This migration adds proper foreign key cascade rules for data integrity:
- document→tenant: SET NULL (preserve documents if tenant removed)
- attachment→document: CASCADE (remove attachments when document deleted)
- comment→document: CASCADE (remove comments when document deleted)
- version→document: CASCADE (remove versions when document deleted)
- section→version: CASCADE (remove sections when version deleted)
- user→tenant: SET NULL (preserve users if tenant removed)
"""

from __future__ import annotations

from alembic import op

revision = "20260311_0020"
down_revision = "20260310_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add ON DELETE rules to foreign keys.
    
    SQLite doesn't support ALTER TABLE for foreign keys, so we use batch mode.
    For PostgreSQL, we would drop and recreate constraints directly.
    
    NOTE: This is a no-op in SQLite since constraint changes require 
    recreating tables with proper schema (handled by model definitions).
    The ON DELETE behavior is enforced via model-level cascade settings.
    """
    # Check dialect - SQLite requires batch mode
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    
    if dialect_name == "sqlite":
        # SQLite: Foreign key cascade behavior is defined in the models.
        # The ORM handles cascades via relationship(cascade=...).
        # Altering SQLite FK constraints requires table recreation,
        # which we skip here to avoid data migration issues.
        # The cascade behavior is enforced at the ORM level.
        pass
    
    else:
        # PostgreSQL: Drop and recreate constraints
        # attachments → documents
        op.drop_constraint("attachments_document_id_fkey", "attachments", type_="foreignkey")
        op.create_foreign_key(
            "attachments_document_id_fkey",
            "attachments",
            "documents",
            ["document_id"],
            ["id"],
            ondelete="CASCADE",
        )
        
        # comments → documents
        op.drop_constraint("comments_document_id_fkey", "comments", type_="foreignkey")
        op.create_foreign_key(
            "comments_document_id_fkey",
            "comments",
            "documents",
            ["document_id"],
            ["id"],
            ondelete="CASCADE",
        )
        
        # versions → documents
        op.drop_constraint("versions_document_id_fkey", "versions", type_="foreignkey")
        op.create_foreign_key(
            "versions_document_id_fkey",
            "versions",
            "documents",
            ["document_id"],
            ["id"],
            ondelete="CASCADE",
        )
        
        # sections → versions
        op.drop_constraint("sections_version_id_fkey", "sections", type_="foreignkey")
        op.create_foreign_key(
            "sections_version_id_fkey",
            "sections",
            "versions",
            ["version_id"],
            ["id"],
            ondelete="CASCADE",
        )
        
        # documents → tenants
        op.drop_constraint("documents_tenant_id_fkey", "documents", type_="foreignkey")
        op.create_foreign_key(
            "documents_tenant_id_fkey",
            "documents",
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="SET NULL",
        )
        
        # users → tenants
        op.drop_constraint("users_tenant_id_fkey", "users", type_="foreignkey")
        op.create_foreign_key(
            "users_tenant_id_fkey",
            "users",
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Remove ON DELETE rules from foreign keys."""
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    
    if dialect_name == "sqlite":
        op.execute("PRAGMA foreign_keys=OFF")
        
        # Revert to basic FK without cascade
        tables_and_columns = [
            ("attachments", "document_id", "documents"),
            ("comments", "document_id", "documents"),
            ("versions", "document_id", "documents"),
            ("sections", "version_id", "versions"),
            ("documents", "tenant_id", "tenants"),
            ("users", "tenant_id", "tenants"),
        ]
        
        for table, col, ref_table in tables_and_columns:
            with op.batch_alter_table(table, schema=None) as batch_op:
                batch_op.drop_constraint(f"{table}_{col}_fkey", type_="foreignkey")
                batch_op.create_foreign_key(
                    f"{table}_{col}_fkey",
                    ref_table,
                    [col],
                    ["id"],
                )
        
        op.execute("PRAGMA foreign_keys=ON")
    
    else:
        # PostgreSQL
        tables_and_columns = [
            ("attachments", "document_id", "documents"),
            ("comments", "document_id", "documents"),
            ("versions", "document_id", "documents"),
            ("sections", "version_id", "versions"),
            ("documents", "tenant_id", "tenants"),
            ("users", "tenant_id", "tenants"),
        ]
        
        for table, col, ref_table in tables_and_columns:
            op.drop_constraint(f"{table}_{col}_fkey", table, type_="foreignkey")
            op.create_foreign_key(
                f"{table}_{col}_fkey",
                table,
                ref_table,
                [col],
                ["id"],
            )
