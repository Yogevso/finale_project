"""Seed script to create test tenants and users for multi-tenancy testing

Creates:
- 1 System Admin (sysadmin) - can access all tenants
- Test users for each role: admin, manager, editor, viewer
- 2 Companies with customer users
- Sample documents with different visibility levels
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db import engine, SessionLocal
from app.models import Tenant, User, UserRole, Document, DocumentStatus, DocumentVisibility, Version, document_company_assignments
from app.security import get_password_hash


def seed_multi_tenant_data():
    """Seed multi-tenant test data"""
    print("=" * 60)
    print("Multi-Tenant Seed Script")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # ========================================
        # 1. Create Default Tenant
        # ========================================
        print("\n[1/7] Creating Default Tenant...")
        
        default_tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
        if not default_tenant:
            default_tenant = Tenant(name="Default Organization", slug="default", is_active=True)
            db.add(default_tenant)
            db.commit()
            db.refresh(default_tenant)
            print(f"      ✓ Created 'Default Organization' (ID: {default_tenant.id})")
        else:
            print(f"      ✓ 'Default Organization' already exists (ID: {default_tenant.id})")
        
        # ========================================
        # 2. Create System Admin
        # ========================================
        print("\n[2/7] Creating System Admin...")
        
        sysadmin = db.query(User).filter(User.username == "sysadmin").first()
        if not sysadmin:
            sysadmin = User(
                username="sysadmin",
                email="sysadmin@docportal.com",
                full_name="System Administrator",
                hashed_password=get_password_hash("sysadmin123"),
                role=UserRole.SYSTEM_ADMIN,
                is_active=True,
                tenant_id=default_tenant.id
            )
            db.add(sysadmin)
            db.commit()
            print("      ✓ Created sysadmin (password: sysadmin123)")
        else:
            print("      ✓ sysadmin already exists")
        
        # ========================================
        # 3. Create Role-Based Users
        # ========================================
        print("\n[3/7] Creating Role-Based Users...")
        
        role_users = [
            {"username": "admin", "email": "admin@docportal.com", "full_name": "Admin User",
             "password": "admin123", "role": UserRole.ADMIN},
            {"username": "manager", "email": "manager@docportal.com", "full_name": "Manager User",
             "password": "manager123", "role": UserRole.MANAGER},
            {"username": "editor", "email": "editor@docportal.com", "full_name": "Editor User",
             "password": "editor123", "role": UserRole.EDITOR},
            {"username": "viewer", "email": "viewer@docportal.com", "full_name": "Viewer User",
             "password": "viewer123", "role": UserRole.VIEWER},
        ]
        
        for user_data in role_users:
            existing = db.query(User).filter(User.username == user_data["username"]).first()
            if not existing:
                user = User(
                    username=user_data["username"],
                    email=user_data["email"],
                    full_name=user_data["full_name"],
                    hashed_password=get_password_hash(user_data["password"]),
                    role=user_data["role"],
                    is_active=True,
                    tenant_id=default_tenant.id
                )
                db.add(user)
                print(f"      ✓ Created {user_data['username']} ({user_data['role'].value}) - password: {user_data['password']}")
            else:
                print(f"      ✓ {user_data['username']} already exists")
        
        db.commit()
        
        # ========================================
        # 4. Create Customer Companies (as Tenants)
        # ========================================
        print("\n[4/7] Creating Customer Companies...")
        
        # Company A (as a tenant for customers)
        company_a = db.query(Tenant).filter(Tenant.slug == "company-a").first()
        if not company_a:
            company_a = Tenant(
                name="Company A",
                slug="company-a",
                is_active=True,
                company_type="customer"
            )
            db.add(company_a)
            db.commit()
            db.refresh(company_a)
            print(f"      ✓ Created 'Company A' (ID: {company_a.id})")
        else:
            print(f"      ✓ 'Company A' already exists (ID: {company_a.id})")
        
        # Company B (as a tenant for customers)
        company_b = db.query(Tenant).filter(Tenant.slug == "company-b").first()
        if not company_b:
            company_b = Tenant(
                name="Company B",
                slug="company-b",
                is_active=True,
                company_type="customer"
            )
            db.add(company_b)
            db.commit()
            db.refresh(company_b)
            print(f"      ✓ Created 'Company B' (ID: {company_b.id})")
        else:
            print(f"      ✓ 'Company B' already exists (ID: {company_b.id})")
        
        # ========================================
        # 5. Create Customer Users
        # ========================================
        print("\n[5/7] Creating Customer Users...")
        
        customer1 = db.query(User).filter(User.username == "customer1").first()
        if not customer1:
            customer1 = User(
                username="customer1",
                email="customer1@companya.com",
                full_name="Customer One",
                hashed_password=get_password_hash("customer123"),
                role=UserRole.CUSTOMER,
                is_active=True,
                tenant_id=company_a.id  # Customer's tenant IS their company
            )
            db.add(customer1)
            print("      ✓ Created customer1 (Company A) - password: customer123")
        else:
            print("      ✓ customer1 already exists")
        
        customer2 = db.query(User).filter(User.username == "customer2").first()
        if not customer2:
            customer2 = User(
                username="customer2",
                email="customer2@companyb.com",
                full_name="Customer Two",
                hashed_password=get_password_hash("customer123"),
                role=UserRole.CUSTOMER,
                is_active=True,
                tenant_id=company_b.id  # Customer's tenant IS their company
            )
            db.add(customer2)
            print("      ✓ Created customer2 (Company B) - password: customer123")
        else:
            print("      ✓ customer2 already exists")
        
        db.commit()
        
        # Get admin for document creation
        admin = db.query(User).filter(User.username == "admin").first()
        
        # ========================================
        # 6. Create Sample Documents
        # ========================================
        print("\n[6/7] Creating Sample Documents...")
        
        documents_to_create = [
            # Public documents (visible to everyone including anonymous)
            {"title": "Public Policy Document", "doc_num": "PUB-2024-001",
             "description": "A publicly available policy document",
             "category": "Policy", "visibility": DocumentVisibility.PUBLIC,
             "content": "<h1>Public Policy</h1><p>This document is publicly accessible.</p>"},
            {"title": "Public User Guide", "doc_num": "PUB-2024-002",
             "description": "Public user guide for all users",
             "category": "Guides", "visibility": DocumentVisibility.PUBLIC,
             "content": "<h1>User Guide</h1><p>Welcome to our public user guide.</p>"},
            # Internal documents (visible to internal users only)
            {"title": "Internal Procedures", "doc_num": "INT-2024-001",
             "description": "Internal company procedures",
             "category": "Procedures", "visibility": DocumentVisibility.INTERNAL,
             "content": "<h1>Internal Procedures</h1><p>For internal use only.</p>"},
            {"title": "Internal Training Material", "doc_num": "INT-2024-002",
             "description": "Training materials for staff",
             "category": "Training", "visibility": DocumentVisibility.INTERNAL,
             "content": "<h1>Training</h1><p>Internal training content.</p>"},
            # Company A documents
            {"title": "Company A Contract", "doc_num": "COMP-A-001",
             "description": "Contract for Company A",
             "category": "Contracts", "visibility": DocumentVisibility.COMPANY,
             "content": "<h1>Company A Contract</h1><p>Confidential contract for Company A.</p>",
             "assigned_company": company_a},
            {"title": "Company A Specifications", "doc_num": "COMP-A-002",
             "description": "Technical specs for Company A",
             "category": "Technical", "visibility": DocumentVisibility.COMPANY,
             "content": "<h1>Specifications</h1><p>Technical details for Company A.</p>",
             "assigned_company": company_a},
            # Company B documents
            {"title": "Company B Agreement", "doc_num": "COMP-B-001",
             "description": "Agreement for Company B",
             "category": "Contracts", "visibility": DocumentVisibility.COMPANY,
             "content": "<h1>Company B Agreement</h1><p>Confidential agreement for Company B.</p>",
             "assigned_company": company_b},
        ]
        
        for doc_data in documents_to_create:
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
                
                # Assign company (tenant) if specified
                if doc_data.get("assigned_company"):
                    doc.assigned_companies.append(doc_data["assigned_company"])
                
                print(f"      ✓ Created '{doc_data['title']}' ({doc_data['visibility'].value})")
            else:
                print(f"      ✓ '{doc_data['title']}' already exists")
        
        db.commit()
        
        # ========================================
        # 7. Summary
        # ========================================
        print("\n[7/7] Summary...")
        
        tenant_count = db.query(Tenant).count()
        user_count = db.query(User).count()
        doc_count = db.query(Document).count()
        
        print(f"      Tenants/Companies: {tenant_count}")
        print(f"      Users: {user_count}")
        print(f"      Documents: {doc_count}")
        
        print("\n" + "=" * 60)
        print("Test Accounts")
        print("=" * 60)
        print("\nInternal Users:")
        print("  - sysadmin / sysadmin123 (System Admin)")
        print("  - admin / admin123 (Admin)")
        print("  - manager / manager123 (Manager)")
        print("  - editor / editor123 (Editor)")
        print("  - viewer / viewer123 (Viewer)")
        print("\nCustomer Users:")
        print("  - customer1 / customer123 (Customer - Company A)")
        print("  - customer2 / customer123 (Customer - Company B)")
        print("\n" + "=" * 60)
        print("✓ Seed completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        db.rollback()
        print(f"\n✗ Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_multi_tenant_data()
