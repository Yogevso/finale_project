"""Migration script to add multi-tenancy support

This script:
1. Creates the tenants table
2. Creates a default tenant
3. Adds tenant_id columns to users and documents
4. Migrates existing data to default tenant
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db import engine, SessionLocal
from app.models import Tenant, User, Document, Base


def migrate():
    """Run the multi-tenancy migration"""
    print("=" * 60)
    print("Multi-Tenancy Migration Script")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Step 1: Create tenants table and add tenant_id columns using raw SQL
        print("\n[1/5] Creating tenants table and adding tenant_id columns...")
        
        # Check if tenants table exists
        result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='tenants'")).fetchone()
        if not result:
            print("      Creating tenants table...")
            db.execute(text("""
                CREATE TABLE tenants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(255) NOT NULL,
                    slug VARCHAR(100) NOT NULL UNIQUE,
                    is_active BOOLEAN DEFAULT 1,
                    settings TEXT DEFAULT '{}',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            db.commit()
            print("      ✓ tenants table created")
        else:
            print("      ✓ tenants table already exists")
        
        # Check if tenant_id column exists in users table
        result = db.execute(text("PRAGMA table_info(users)")).fetchall()
        user_columns = [row[1] for row in result]
        
        if "tenant_id" not in user_columns:
            print("      Adding tenant_id column to users table...")
            db.execute(text("ALTER TABLE users ADD COLUMN tenant_id INTEGER REFERENCES tenants(id)"))
            db.commit()
            print("      ✓ tenant_id added to users")
        else:
            print("      ✓ tenant_id already exists in users")
        
        # Check if tenant_id column exists in documents table
        result = db.execute(text("PRAGMA table_info(documents)")).fetchall()
        doc_columns = [row[1] for row in result]
        
        if "tenant_id" not in doc_columns:
            print("      Adding tenant_id column to documents table...")
            db.execute(text("ALTER TABLE documents ADD COLUMN tenant_id INTEGER REFERENCES tenants(id)"))
            db.commit()
            print("      ✓ tenant_id added to documents")
        else:
            print("      ✓ tenant_id already exists in documents")
        
        print("      ✓ Tables created/updated")
        
        # Step 2: Check if default tenant already exists
        print("\n[2/5] Checking for existing default tenant...")
        result = db.execute(text("SELECT id, name FROM tenants WHERE slug = 'default'")).fetchone()
        
        if result:
            default_tenant_id = result[0]
            print(f"      ✓ Default tenant already exists (ID: {default_tenant_id})")
        else:
            # Create default tenant
            print("      Creating default tenant...")
            db.execute(text("""
                INSERT INTO tenants (name, slug, is_active, settings)
                VALUES ('Default Organization', 'default', 1, '{}')
            """))
            db.commit()
            result = db.execute(text("SELECT id FROM tenants WHERE slug = 'default'")).fetchone()
            default_tenant_id = result[0]
            print(f"      ✓ Default tenant created (ID: {default_tenant_id})")
        
        # Step 3: Update users without tenant_id
        print("\n[3/5] Migrating users to default tenant...")
        result = db.execute(text("SELECT COUNT(*) FROM users WHERE tenant_id IS NULL")).fetchone()
        users_without_tenant = result[0]
        if users_without_tenant > 0:
            db.execute(
                text("UPDATE users SET tenant_id = :tid WHERE tenant_id IS NULL"),
                {"tid": default_tenant_id}
            )
            db.commit()
            print(f"      ✓ Updated {users_without_tenant} users")
        else:
            print("      ✓ All users already have tenant_id")
        
        # Step 4: Update documents without tenant_id
        print("\n[4/5] Migrating documents to default tenant...")
        result = db.execute(text("SELECT COUNT(*) FROM documents WHERE tenant_id IS NULL")).fetchone()
        docs_without_tenant = result[0]
        if docs_without_tenant > 0:
            db.execute(
                text("UPDATE documents SET tenant_id = :tid WHERE tenant_id IS NULL"),
                {"tid": default_tenant_id}
            )
            db.commit()
            print(f"      ✓ Updated {docs_without_tenant} documents")
        else:
            print("      ✓ All documents already have tenant_id")
        
        # Step 5: Verify migration
        print("\n[5/5] Verifying migration...")
        tenant_count = db.execute(text("SELECT COUNT(*) FROM tenants")).fetchone()[0]
        user_with_tenant = db.execute(text("SELECT COUNT(*) FROM users WHERE tenant_id IS NOT NULL")).fetchone()[0]
        total_users = db.execute(text("SELECT COUNT(*) FROM users")).fetchone()[0]
        doc_with_tenant = db.execute(text("SELECT COUNT(*) FROM documents WHERE tenant_id IS NOT NULL")).fetchone()[0]
        total_docs = db.execute(text("SELECT COUNT(*) FROM documents")).fetchone()[0]
        
        print(f"      Tenants: {tenant_count}")
        print(f"      Users with tenant: {user_with_tenant}/{total_users}")
        print(f"      Documents with tenant: {doc_with_tenant}/{total_docs}")
        
        if user_with_tenant == total_users and doc_with_tenant == total_docs:
            print("\n" + "=" * 60)
            print("✓ Migration completed successfully!")
            print("=" * 60)
        else:
            print("\n⚠ Warning: Some records may not have been migrated")
        
        return default_tenant_id
        
    except Exception as e:
        db.rollback()
        print(f"\n✗ Migration failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
