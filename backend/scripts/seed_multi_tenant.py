"""Seed script to create test tenants and users for multi-tenancy testing

Creates:
- 1 Super Admin (can access all tenants)
- 2 Test Tenants (Acme Corp, Beta Inc)
- 2 Tenant Admins (1 per tenant)
- 4 Regular Users (2 per tenant)
- Sample documents for each tenant
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db import engine, SessionLocal
from app.models import Tenant, User, UserRole, Document, DocumentStatus
from app.security import get_password_hash


def seed_multi_tenant_data():
    """Seed multi-tenant test data"""
    print("=" * 60)
    print("Multi-Tenant Seed Script")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # ========================================
        # 1. Create Super Admin
        # ========================================
        print("\n[1/5] Creating Super Admin...")
        
        super_admin = db.query(User).filter(User.username == "super_admin").first()
        if not super_admin:
            super_admin = User(
                username="super_admin",
                email="super@docportal.com",
                full_name="Super Administrator",
                hashed_password=get_password_hash("super123"),
                role=UserRole.SUPER_ADMIN,
                is_active=True,
                tenant_id=None  # Super admin has no tenant
            )
            db.add(super_admin)
            db.commit()
            print("      ✓ Created super_admin (password: super123)")
        else:
            # Update role to super_admin if not already
            if super_admin.role != UserRole.SUPER_ADMIN:
                super_admin.role = UserRole.SUPER_ADMIN
                super_admin.tenant_id = None
                db.commit()
            print("      ✓ super_admin already exists")
        
        # ========================================
        # 2. Create Tenants
        # ========================================
        print("\n[2/5] Creating Test Tenants...")
        
        # Acme Corp
        acme = db.query(Tenant).filter(Tenant.slug == "acme").first()
        if not acme:
            acme = Tenant(name="Acme Corporation", slug="acme", is_active=True)
            db.add(acme)
            db.commit()
            db.refresh(acme)
            print(f"      ✓ Created 'Acme Corporation' (ID: {acme.id})")
        else:
            print(f"      ✓ 'Acme Corporation' already exists (ID: {acme.id})")
        
        # Beta Inc
        beta = db.query(Tenant).filter(Tenant.slug == "beta").first()
        if not beta:
            beta = Tenant(name="Beta Incorporated", slug="beta", is_active=True)
            db.add(beta)
            db.commit()
            db.refresh(beta)
            print(f"      ✓ Created 'Beta Incorporated' (ID: {beta.id})")
        else:
            print(f"      ✓ 'Beta Incorporated' already exists (ID: {beta.id})")
        
        # ========================================
        # 3. Create Tenant Users
        # ========================================
        print("\n[3/5] Creating Tenant Users...")
        
        users_to_create = [
            # Acme users
            {"username": "acme_admin", "email": "admin@acme.com", "full_name": "Acme Admin",
             "password": "acme123", "role": UserRole.ADMIN, "tenant_id": acme.id},
            {"username": "acme_editor", "email": "editor@acme.com", "full_name": "Acme Editor",
             "password": "acme123", "role": UserRole.EDITOR, "tenant_id": acme.id},
            {"username": "acme_viewer", "email": "viewer@acme.com", "full_name": "Acme Viewer",
             "password": "acme123", "role": UserRole.VIEWER, "tenant_id": acme.id},
            # Beta users
            {"username": "beta_admin", "email": "admin@beta.com", "full_name": "Beta Admin",
             "password": "beta123", "role": UserRole.ADMIN, "tenant_id": beta.id},
            {"username": "beta_editor", "email": "editor@beta.com", "full_name": "Beta Editor",
             "password": "beta123", "role": UserRole.EDITOR, "tenant_id": beta.id},
            {"username": "beta_viewer", "email": "viewer@beta.com", "full_name": "Beta Viewer",
             "password": "beta123", "role": UserRole.VIEWER, "tenant_id": beta.id},
        ]
        
        for user_data in users_to_create:
            existing = db.query(User).filter(User.username == user_data["username"]).first()
            if not existing:
                user = User(
                    username=user_data["username"],
                    email=user_data["email"],
                    full_name=user_data["full_name"],
                    hashed_password=get_password_hash(user_data["password"]),
                    role=user_data["role"],
                    is_active=True,
                    tenant_id=user_data["tenant_id"]
                )
                db.add(user)
                print(f"      ✓ Created {user_data['username']} (password: {user_data['password']})")
            else:
                # Update tenant_id if not set
                if existing.tenant_id != user_data["tenant_id"]:
                    existing.tenant_id = user_data["tenant_id"]
                print(f"      ✓ {user_data['username']} already exists")
        
        db.commit()
        
        # ========================================
        # 4. Create Sample Documents
        # ========================================
        print("\n[4/5] Creating Sample Documents...")
        
        # Get admin users for document creation
        acme_admin = db.query(User).filter(User.username == "acme_admin").first()
        beta_admin = db.query(User).filter(User.username == "beta_admin").first()
        
        documents_to_create = [
            # Acme documents
            {"title": "Acme Product Catalog", "doc_num": "ACME-2024-001",
             "description": "Official product catalog for Acme Corporation",
             "category": "Products", "tenant_id": acme.id, "created_by": acme_admin.id},
            {"title": "Acme Employee Handbook", "doc_num": "ACME-2024-002",
             "description": "Employee policies and procedures for Acme",
             "category": "HR", "tenant_id": acme.id, "created_by": acme_admin.id},
            {"title": "Acme Safety Guidelines", "doc_num": "ACME-2024-003",
             "description": "Workplace safety guidelines",
             "category": "Compliance", "tenant_id": acme.id, "created_by": acme_admin.id},
            # Beta documents
            {"title": "Beta Service Agreement", "doc_num": "BETA-2024-001",
             "description": "Standard service agreement template for Beta Inc",
             "category": "Legal", "tenant_id": beta.id, "created_by": beta_admin.id},
            {"title": "Beta Technical Specs", "doc_num": "BETA-2024-002",
             "description": "Technical specifications for Beta products",
             "category": "Technical", "tenant_id": beta.id, "created_by": beta_admin.id},
            {"title": "Beta Onboarding Guide", "doc_num": "BETA-2024-003",
             "description": "New employee onboarding guide for Beta Inc",
             "category": "HR", "tenant_id": beta.id, "created_by": beta_admin.id},
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
                    tenant_id=doc_data["tenant_id"],
                    created_by=doc_data["created_by"]
                )
                db.add(doc)
                print(f"      ✓ Created '{doc_data['title']}'")
            else:
                # Update tenant_id if not set
                if existing.tenant_id != doc_data["tenant_id"]:
                    existing.tenant_id = doc_data["tenant_id"]
                print(f"      ✓ '{doc_data['title']}' already exists")
        
        db.commit()
        
        # ========================================
        # 5. Summary
        # ========================================
        print("\n[5/5] Summary...")
        
        tenant_count = db.query(Tenant).count()
        user_count = db.query(User).count()
        doc_count = db.query(Document).count()
        
        print(f"      Tenants: {tenant_count}")
        print(f"      Users: {user_count}")
        print(f"      Documents: {doc_count}")
        
        print("\n" + "=" * 60)
        print("Test Accounts")
        print("=" * 60)
        print("\nSuper Admin (all tenants):")
        print("  - super_admin / super123")
        print("\nAcme Corporation:")
        print("  - acme_admin / acme123 (Admin)")
        print("  - acme_editor / acme123 (Editor)")
        print("  - acme_viewer / acme123 (Viewer)")
        print("\nBeta Incorporated:")
        print("  - beta_admin / beta123 (Admin)")
        print("  - beta_editor / beta123 (Editor)")
        print("  - beta_viewer / beta123 (Viewer)")
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
