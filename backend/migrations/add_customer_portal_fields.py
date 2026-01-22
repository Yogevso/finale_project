"""
Migration: Add Customer Portal Fields
This migration adds the new fields required for the customer portal feature.

Run with: python migrations/add_customer_portal_fields.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db import engine, Base
from app.models import (
    Tenant, User, Document, Version, Section, Attachment, Comment,
    AuditLog, Notification, PasswordReset, SavedSearch, Bookmark,
    Feedback, ReadingProgress, ReviewRequest, document_company_assignments
)


def run_migration():
    """Run the migration to add customer portal fields."""
    print("=" * 60)
    print("Customer Portal Migration")
    print("=" * 60)
    
    with engine.connect() as conn:
        # Check if we're using SQLite
        is_sqlite = 'sqlite' in str(engine.url)
        
        # Step 1: Add new columns to tenants table
        print("\n[1/6] Updating tenants table...")
        try:
            conn.execute(text("ALTER TABLE tenants ADD COLUMN company_logo VARCHAR(500)"))
            print("  ✓ Added company_logo column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("  - company_logo column already exists")
            else:
                print(f"  ! Error: {e}")
        
        try:
            conn.execute(text("ALTER TABLE tenants ADD COLUMN contact_email VARCHAR(255)"))
            print("  ✓ Added contact_email column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("  - contact_email column already exists")
            else:
                print(f"  ! Error: {e}")
        
        try:
            conn.execute(text("ALTER TABLE tenants ADD COLUMN company_type VARCHAR(50) DEFAULT 'customer'"))
            print("  ✓ Added company_type column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("  - company_type column already exists")
            else:
                print(f"  ! Error: {e}")
        
        # Step 2: Add visibility column to documents table
        print("\n[2/6] Updating documents table...")
        try:
            conn.execute(text("ALTER TABLE documents ADD COLUMN visibility VARCHAR(20) DEFAULT 'internal'"))
            print("  ✓ Added visibility column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("  - visibility column already exists")
            else:
                print(f"  ! Error: {e}")
        
        # Step 3: Update user roles (super_admin -> system_admin)
        print("\n[3/6] Updating user roles...")
        try:
            result = conn.execute(text("UPDATE users SET role = 'system_admin' WHERE role = 'super_admin'"))
            count = result.rowcount
            if count > 0:
                print(f"  ✓ Updated {count} super_admin users to system_admin")
            else:
                print("  - No super_admin users to update")
        except Exception as e:
            print(f"  ! Error updating roles: {e}")
        
        # Step 4: Update feedback table with new columns
        print("\n[4/6] Updating feedbacks table...")
        try:
            conn.execute(text("ALTER TABLE feedbacks ADD COLUMN feedback_type VARCHAR(20) DEFAULT 'other'"))
            print("  ✓ Added feedback_type column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("  - feedback_type column already exists")
            else:
                print(f"  ! Error: {e}")
        
        try:
            conn.execute(text("ALTER TABLE feedbacks ADD COLUMN status VARCHAR(20) DEFAULT 'pending'"))
            print("  ✓ Added status column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("  - status column already exists")
            else:
                print(f"  ! Error: {e}")
        
        try:
            conn.execute(text("ALTER TABLE feedbacks ADD COLUMN content TEXT"))
            print("  ✓ Added content column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("  - content column already exists")
            else:
                print(f"  ! Error: {e}")
        
        try:
            conn.execute(text("ALTER TABLE feedbacks ADD COLUMN response TEXT"))
            print("  ✓ Added response column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("  - response column already exists")
            else:
                print(f"  ! Error: {e}")
        
        try:
            conn.execute(text("ALTER TABLE feedbacks ADD COLUMN responded_by INTEGER REFERENCES users(id)"))
            print("  ✓ Added responded_by column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("  - responded_by column already exists")
            else:
                print(f"  ! Error: {e}")
        
        try:
            conn.execute(text("ALTER TABLE feedbacks ADD COLUMN responded_at DATETIME"))
            print("  ✓ Added responded_at column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("  - responded_at column already exists")
            else:
                print(f"  ! Error: {e}")
        
        conn.commit()
        
        # Step 5: Create document_company_assignments table
        print("\n[5/6] Creating document_company_assignments table...")
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS document_company_assignments (
                    document_id INTEGER NOT NULL REFERENCES documents(id),
                    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
                    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    assigned_by INTEGER REFERENCES users(id),
                    PRIMARY KEY (document_id, tenant_id)
                )
            """))
            conn.commit()
            print("  ✓ Created document_company_assignments table")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("  - document_company_assignments table already exists")
            else:
                print(f"  ! Error: {e}")
        
        # Step 6: Create review_requests table
        print("\n[6/6] Creating review_requests table...")
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS review_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL REFERENCES documents(id),
                    version_id INTEGER REFERENCES versions(id),
                    submitted_by INTEGER NOT NULL REFERENCES users(id),
                    reviewed_by INTEGER REFERENCES users(id),
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    message TEXT,
                    review_comments TEXT,
                    submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            print("  ✓ Created review_requests table")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("  - review_requests table already exists")
            else:
                print(f"  ! Error: {e}")
        
        # Create indexes
        print("\n[7/7] Creating indexes...")
        indexes = [
            ("idx_documents_visibility", "documents", "visibility"),
            ("idx_feedbacks_status", "feedbacks", "status"),
            ("idx_review_requests_status", "review_requests", "status"),
            ("idx_review_requests_document", "review_requests", "document_id"),
        ]
        
        for idx_name, table, column in indexes:
            try:
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})"))
                print(f"  ✓ Created index {idx_name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"  - Index {idx_name} already exists")
                else:
                    print(f"  ! Error creating {idx_name}: {e}")
        
        conn.commit()
    
    print("\n" + "=" * 60)
    print("✓ Migration completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    run_migration()
