"""
Seed Data Script - Creates all users and sample documents
==========================================================

This script populates the database with:
- Default tenant/organization
- All user roles (sysadmin, admin, manager, editor, viewer, customer)
- Customer companies
- Sample documents with different visibility levels

Run this AFTER init_db.py:
    python init_db.py
    python seed_data.py
"""
import sys
import os

# Ensure the app module is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import SessionLocal
from app.models import (
    Tenant, User, UserRole, Document, DocumentStatus, 
    DocumentVisibility, Version
)
from app.security import get_password_hash


def create_tenants(db):
    """Create default organization and customer companies"""
    print("\n📁 Creating Tenants/Organizations...")
    
    tenants = {}
    
    # Default tenant for internal users
    default_tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
    if not default_tenant:
        default_tenant = Tenant(name="Default Organization", slug="default", is_active=True)
        db.add(default_tenant)
        db.flush()
        print(f"   ✓ Created 'Default Organization' (ID: {default_tenant.id})")
    else:
        print(f"   ✓ 'Default Organization' already exists (ID: {default_tenant.id})")
    tenants["default"] = default_tenant
    
    # Company A (customer tenant)
    company_a = db.query(Tenant).filter(Tenant.slug == "company-a").first()
    if not company_a:
        company_a = Tenant(
            name="Company A", 
            slug="company-a", 
            is_active=True,
            company_type="customer"
        )
        db.add(company_a)
        db.flush()
        print(f"   ✓ Created 'Company A' (ID: {company_a.id})")
    else:
        print(f"   ✓ 'Company A' already exists (ID: {company_a.id})")
    tenants["company-a"] = company_a
    
    # Company B (customer tenant)
    company_b = db.query(Tenant).filter(Tenant.slug == "company-b").first()
    if not company_b:
        company_b = Tenant(
            name="Company B", 
            slug="company-b", 
            is_active=True,
            company_type="customer"
        )
        db.add(company_b)
        db.flush()
        print(f"   ✓ Created 'Company B' (ID: {company_b.id})")
    else:
        print(f"   ✓ 'Company B' already exists (ID: {company_b.id})")
    tenants["company-b"] = company_b
    
    db.commit()
    return tenants


def create_users(db, tenants):
    """Create all user accounts"""
    print("\n👥 Creating Users...")
    
    default_tenant = tenants["default"]
    company_a = tenants["company-a"]
    company_b = tenants["company-b"]
    
    # Define all users to create
    users_config = [
        # Internal users (default tenant)
        {
            "username": "sysadmin",
            "email": "sysadmin@docportal.com",
            "full_name": "System Administrator",
            "password": "sysadmin123",
            "role": UserRole.SYSTEM_ADMIN,
            "tenant": default_tenant
        },
        {
            "username": "admin",
            "email": "admin@docportal.com",
            "full_name": "Admin User",
            "password": "admin123",
            "role": UserRole.ADMIN,
            "tenant": default_tenant
        },
        {
            "username": "manager",
            "email": "manager@docportal.com",
            "full_name": "Manager User",
            "password": "manager123",
            "role": UserRole.MANAGER,
            "tenant": default_tenant
        },
        {
            "username": "editor",
            "email": "editor@docportal.com",
            "full_name": "Editor User",
            "password": "editor123",
            "role": UserRole.EDITOR,
            "tenant": default_tenant
        },
        {
            "username": "viewer",
            "email": "viewer@docportal.com",
            "full_name": "Viewer User",
            "password": "viewer123",
            "role": UserRole.VIEWER,
            "tenant": default_tenant
        },
        # Customer users
        {
            "username": "customer1",
            "email": "customer1@companya.com",
            "full_name": "Customer One",
            "password": "customer123",
            "role": UserRole.CUSTOMER,
            "tenant": company_a
        },
        {
            "username": "customer2",
            "email": "customer2@companyb.com",
            "full_name": "Customer Two",
            "password": "customer123",
            "role": UserRole.CUSTOMER,
            "tenant": company_b
        },
    ]
    
    created_users = {}
    for user_data in users_config:
        existing = db.query(User).filter(User.username == user_data["username"]).first()
        if not existing:
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                full_name=user_data["full_name"],
                hashed_password=get_password_hash(user_data["password"]),
                role=user_data["role"],
                is_active=True,
                tenant_id=user_data["tenant"].id
            )
            db.add(user)
            created_users[user_data["username"]] = user
            print(f"   ✓ Created {user_data['username']} ({user_data['role'].value}) - password: {user_data['password']}")
        else:
            created_users[user_data["username"]] = existing
            print(f"   ✓ {user_data['username']} already exists")
    
    db.commit()
    return created_users


def create_documents(db, tenants, users):
    """Create sample documents with different visibility levels"""
    print("\n📄 Creating Sample Documents...")
    
    default_tenant = tenants["default"]
    company_a = tenants["company-a"]
    company_b = tenants["company-b"]
    admin = users.get("admin")
    
    if not admin:
        print("   ⚠ Admin user not found, skipping document creation")
        return
    
    documents_config = [
        # Public documents (visible to everyone)
        {
            "title": "Public Policy Document",
            "doc_num": "PUB-2024-001",
            "description": "A publicly available policy document",
            "category": "Policy",
            "visibility": DocumentVisibility.PUBLIC,
            "content": "<h1>Public Policy</h1><p>This document is publicly accessible to everyone.</p>"
        },
        {
            "title": "Public User Guide",
            "doc_num": "PUB-2024-002",
            "description": "Public user guide for all users",
            "category": "Guides",
            "visibility": DocumentVisibility.PUBLIC,
            "content": "<h1>User Guide</h1><p>Welcome to our comprehensive user guide.</p>"
        },
        # Internal documents (visible to internal users only)
        {
            "title": "Internal Procedures",
            "doc_num": "INT-2024-001",
            "description": "Internal company procedures",
            "category": "Procedures",
            "visibility": DocumentVisibility.INTERNAL,
            "content": "<h1>Internal Procedures</h1><p>This document contains internal procedures.</p>"
        },
        {
            "title": "Internal Training Material",
            "doc_num": "INT-2024-002",
            "description": "Training materials for staff",
            "category": "Training",
            "visibility": DocumentVisibility.INTERNAL,
            "content": "<h1>Training</h1><p>Training content for internal staff members.</p>"
        },
        # Company-specific documents
        {
            "title": "Company A Contract",
            "doc_num": "COMP-A-001",
            "description": "Contract for Company A",
            "category": "Contracts",
            "visibility": DocumentVisibility.COMPANY,
            "content": "<h1>Company A Contract</h1><p>Confidential contract for Company A.</p>",
            "assigned_company": company_a
        },
        {
            "title": "Company A Specifications",
            "doc_num": "COMP-A-002",
            "description": "Technical specs for Company A",
            "category": "Technical",
            "visibility": DocumentVisibility.COMPANY,
            "content": "<h1>Specifications</h1><p>Technical specifications for Company A.</p>",
            "assigned_company": company_a
        },
        {
            "title": "Company B Agreement",
            "doc_num": "COMP-B-001",
            "description": "Agreement for Company B",
            "category": "Contracts",
            "visibility": DocumentVisibility.COMPANY,
            "content": "<h1>Company B Agreement</h1><p>Confidential agreement for Company B.</p>",
            "assigned_company": company_b
        },
    ]
    
    for doc_data in documents_config:
        existing = db.query(Document).filter(
            Document.document_number == doc_data["doc_num"]
        ).first()
        
        if not existing:
            doc = Document(
                title=doc_data["title"],
                document_number=doc_data["doc_num"],
                description=doc_data["description"],
                category=doc_data["category"],
                status=DocumentStatus.ACTIVE,
                visibility=doc_data["visibility"],
                tenant_id=default_tenant.id,
                created_by=admin.id
            )
            db.add(doc)
            db.flush()
            
            # Create initial version with content
            version = Version(
                document_id=doc.id,
                version_number=1,
                content=doc_data["content"],
                changes_summary="Initial version",
                created_by=admin.id,
                is_published=True
            )
            db.add(version)
            
            # Assign company if specified
            if doc_data.get("assigned_company"):
                doc.assigned_companies.append(doc_data["assigned_company"])
            
            print(f"   ✓ Created '{doc_data['title']}' ({doc_data['visibility'].value})")
        else:
            print(f"   ✓ '{doc_data['title']}' already exists")
    
    db.commit()


def print_summary(db):
    """Print summary of seeded data"""
    tenant_count = db.query(Tenant).count()
    user_count = db.query(User).count()
    doc_count = db.query(Document).count()
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"   Tenants/Companies: {tenant_count}")
    print(f"   Users: {user_count}")
    print(f"   Documents: {doc_count}")
    
    print("\n" + "=" * 60)
    print("🔑 TEST ACCOUNTS")
    print("=" * 60)
    print("\n   Internal Users:")
    print("   ┌─────────────┬──────────────┬──────────────┐")
    print("   │ Username    │ Password     │ Role         │")
    print("   ├─────────────┼──────────────┼──────────────┤")
    print("   │ sysadmin    │ sysadmin123  │ System Admin │")
    print("   │ admin       │ admin123     │ Admin        │")
    print("   │ manager     │ manager123   │ Manager      │")
    print("   │ editor      │ editor123    │ Editor       │")
    print("   │ viewer      │ viewer123    │ Viewer       │")
    print("   └─────────────┴──────────────┴──────────────┘")
    print("\n   Customer Users:")
    print("   ┌─────────────┬──────────────┬──────────────────┐")
    print("   │ Username    │ Password     │ Company          │")
    print("   ├─────────────┼──────────────┼──────────────────┤")
    print("   │ customer1   │ customer123  │ Company A        │")
    print("   │ customer2   │ customer123  │ Company B        │")
    print("   └─────────────┴──────────────┴──────────────────┘")


def main():
    """Main seed function"""
    print("=" * 60)
    print("🌱 SEED DATA SCRIPT")
    print("=" * 60)
    print("Creating test data for the Document Portal...")
    
    db = SessionLocal()
    
    try:
        # Step 1: Create tenants
        tenants = create_tenants(db)
        
        # Step 2: Create users
        users = create_users(db, tenants)
        
        # Step 3: Create documents
        create_documents(db, tenants, users)
        
        # Step 4: Print summary
        print_summary(db)
        
        print("\n" + "=" * 60)
        print("✅ Seed completed successfully!")
        print("=" * 60 + "\n")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Seed failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
