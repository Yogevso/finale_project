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

Safety:
    - Development/test environments seed by default unless SEED_DEMO_DATA=false
    - Production/staging require SEED_DEMO_DATA=true explicit opt-in
"""
import os
import sys
from datetime import datetime

# Ensure the app module is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import SessionLocal, init_db
from app.models import (
    Document,
    DocumentStatus,
    DocumentVisibility,
    Tenant,
    Topic,
    User,
    UserRole,
    Version,
    VersionBumpType,
)
from app.security import get_password_hash


TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}
PRODUCTION_LIKE_ENVS = {"production", "staging"}
AUTO_SEED_ENVS = {"development", "dev", "test", "testing", "local"}


def _normalize_flag(value):
    if value is None:
        return None
    return str(value).strip().lower()


def should_seed_demo_data(app_env=None, explicit_flag=None):
    """Return True when demo seed data is allowed for the current environment."""
    resolved_env = _normalize_flag(app_env or os.getenv("APP_ENV")) or "development"
    normalized_flag = _normalize_flag(explicit_flag or os.getenv("SEED_DEMO_DATA"))

    if normalized_flag in TRUE_VALUES:
        return True
    if normalized_flag in FALSE_VALUES:
        return False

    if resolved_env in PRODUCTION_LIKE_ENVS:
        return False
    if resolved_env in AUTO_SEED_ENVS:
        return True
    return False


def ensure_demo_seed_allowed():
    """Fail fast when demo seed data is not allowed for the current environment."""
    if should_seed_demo_data():
        return

    resolved_env = _normalize_flag(os.getenv("APP_ENV")) or "development"
    raise RuntimeError(
        "Refusing to seed demo data in "
        f"{resolved_env}. Set SEED_DEMO_DATA=true for an explicit one-time opt-in."
    )


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
                is_email_verified=True,
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


def create_topics(db):
    """Create public topics with hero images"""
    print("\n🧭 Creating Topics...")

    topics = [
        {
            "name": "Platform",
            "slug": "platform",
            "description": "Core platform architecture, integration, and release guidance.",
            "image_url": "/topic-hero/platform.svg",
        },
        {
            "name": "Security",
            "slug": "security",
            "description": "Authentication, secure boot, and compliance considerations.",
            "image_url": "/topic-hero/security.svg",
        },
        {
            "name": "SDKs & Tools",
            "slug": "sdk-tools",
            "description": "SDKs, extension modules, and tooling resources.",
            "image_url": "/topic-hero/sdk-tools.svg",
        },
        {
            "name": "Operations",
            "slug": "operations",
            "description": "Deployment, observability, and incident response.",
            "image_url": "/topic-hero/operations.svg",
        },
        {
            "name": "Governance",
            "slug": "governance",
            "description": "Data governance, retention, and policy alignment.",
            "image_url": "/topic-hero/governance.svg",
        },
        {
            "name": "Design Systems",
            "slug": "design-systems",
            "description": "UI standards, accessibility, and content guidance.",
            "image_url": "/topic-hero/design-systems.svg",
        },
    ]

    for topic_data in topics:
        existing = db.query(Topic).filter(Topic.slug == topic_data["slug"]).first()
        if not existing:
            db.add(
                Topic(
                    name=topic_data["name"],
                    slug=topic_data["slug"],
                    description=topic_data["description"],
                    image_url=topic_data["image_url"],
                )
            )
            print(f"   ✓ Created topic {topic_data['name']}")
        else:
            updated = False
            if existing.name != topic_data["name"]:
                existing.name = topic_data["name"]
                updated = True
            if existing.description != topic_data["description"]:
                existing.description = topic_data["description"]
                updated = True
            if existing.image_url != topic_data["image_url"]:
                existing.image_url = topic_data["image_url"]
                updated = True
            if updated:
                print(f"   ✓ Updated topic {topic_data['name']}")
            else:
                print(f"   ✓ {topic_data['name']} already exists")

    db.commit()


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
            "topic": "governance",
            "platform": "Core Platform",
            "release_branch": "R580",
            "tags": "policy,governance,compliance",
            "visibility": DocumentVisibility.PUBLIC,
            "content": "<h1>Public Policy</h1><p>This document is publicly accessible to everyone.</p>"
        },
        {
            "title": "Public User Guide",
            "doc_num": "PUB-2024-002",
            "description": "Public user guide for all users",
            "category": "Guides",
            "topic": "platform",
            "platform": "Core Platform",
            "release_branch": "R580",
            "tags": "guide,getting-started,docs",
            "visibility": DocumentVisibility.PUBLIC,
            "content": "<h1>User Guide</h1><p>Welcome to our comprehensive user guide.</p>"
        },
        # Internal documents (visible to internal users only)
        {
            "title": "Internal Procedures",
            "doc_num": "INT-2024-001",
            "description": "Internal company procedures",
            "category": "Procedures",
            "topic": "operations",
            "platform": "Internal Ops",
            "release_branch": "R520",
            "tags": "internal,procedures,operations",
            "visibility": DocumentVisibility.INTERNAL,
            "content": "<h1>Internal Procedures</h1><p>This document contains internal procedures.</p>"
        },
        {
            "title": "Internal Training Material",
            "doc_num": "INT-2024-002",
            "description": "Training materials for staff",
            "category": "Training",
            "topic": "platform",
            "platform": "Internal Ops",
            "release_branch": "R520",
            "tags": "training,internal,enablement",
            "visibility": DocumentVisibility.INTERNAL,
            "content": "<h1>Training</h1><p>Training content for internal staff members.</p>"
        },
        # Company-specific documents
        {
            "title": "Company A Contract",
            "doc_num": "COMP-A-001",
            "description": "Contract for Company A",
            "category": "Contracts",
            "topic": "governance",
            "platform": "Customer Portal",
            "release_branch": "R510",
            "tags": "contract,customer,legal",
            "visibility": DocumentVisibility.COMPANY,
            "content": "<h1>Company A Contract</h1><p>Confidential contract for Company A.</p>",
            "assigned_company": company_a
        },
        {
            "title": "Company A Specifications",
            "doc_num": "COMP-A-002",
            "description": "Technical specs for Company A",
            "category": "Technical",
            "topic": "platform",
            "platform": "Customer Portal",
            "release_branch": "R510",
            "tags": "specs,technical,customer",
            "visibility": DocumentVisibility.COMPANY,
            "content": "<h1>Specifications</h1><p>Technical specifications for Company A.</p>",
            "assigned_company": company_a
        },
        {
            "title": "Company B Agreement",
            "doc_num": "COMP-B-001",
            "description": "Agreement for Company B",
            "category": "Contracts",
            "topic": "governance",
            "platform": "Customer Portal",
            "release_branch": "R510",
            "tags": "agreement,customer,legal",
            "visibility": DocumentVisibility.COMPANY,
            "content": "<h1>Company B Agreement</h1><p>Confidential agreement for Company B.</p>",
            "assigned_company": company_b
        },
    ]

    extra_public_docs = [
        ("vGPU 19 Release Overview", "PUB-2025-010", "Highlights for vGPU 19 LTS branch.", "Release Documentation", "vGPU 19", "R580"),
        ("vGPU 18 Production Notes", "PUB-2025-011", "Production branch capabilities and fixes.", "Release Documentation", "vGPU 18", "R570"),
        ("vGPU 16 LTS Guidance", "PUB-2025-012", "Long-term support guidance for vGPU 16.", "Release Documentation", "vGPU 16", "R535"),
        ("Driver Versions Matrix", "PUB-2025-013", "Driver compatibility across branches.", "Driver Versions", "vGPU 19", "R580"),
        ("Branch Compatibility Sheet", "PUB-2025-014", "Compatibility and lifecycle notes.", "Driver Versions", "vGPU 18", "R570"),
        ("Release Notes: Q1", "PUB-2025-015", "Quarterly release summary and upgrade notes.", "Release Notes", "vGPU 19", "R580"),
        ("Release Notes: Q2", "PUB-2025-016", "Quarterly release summary and upgrade notes.", "Release Notes", "vGPU 19", "R580"),
        ("Release Notes: Q3", "PUB-2025-017", "Quarterly release summary and upgrade notes.", "Release Notes", "vGPU 18", "R570"),
        ("Release Notes: Q4", "PUB-2025-018", "Quarterly release summary and upgrade notes.", "Release Notes", "vGPU 16", "R535"),
        ("Platform Integration Guide", "PUB-2025-019", "Core integration patterns and API baselines.", "Platform", "Core Platform", "R580"),
        ("Secure Boot Troubleshooting", "PUB-2025-020", "Common boot chain issues and remediation steps.", "Security", "Core Platform", "R580"),
        ("SDK Extension Modules", "PUB-2025-021", "Extend the SDK with modular components and hooks.", "SDK", "Developer Portal", "R570"),
        ("Performance Tuning Handbook", "PUB-2025-022", "Optimize throughput and latency across services.", "Performance", "Developer Portal", "R570"),
        ("Observability Quickstart", "PUB-2025-023", "Set up logs, traces, and metrics in minutes.", "Operations", "Developer Portal", "R570"),
        ("Deployment Playbook", "PUB-2025-024", "Recommended deployment workflows and rollback plans.", "Operations", "Developer Portal", "R570"),
        ("Data Governance Basics", "PUB-2025-025", "Data classification and retention best practices.", "Governance", "Developer Portal", "R535"),
        ("API Authentication Guide", "PUB-2025-026", "OAuth, JWT, and service-to-service auth patterns.", "Security", "Developer Portal", "R535"),
        ("Role-Based Access Guide", "PUB-2025-027", "Designing policies and least-privilege access.", "Security", "Developer Portal", "R535"),
        ("Incident Response Runbook", "PUB-2025-028", "Escalation, comms, and recovery procedures.", "Operations", "Developer Portal", "R535"),
        ("Client SDK Quickstart", "PUB-2025-029", "Install, configure, and ship your first build.", "SDK", "Developer Portal", "R535"),
        ("UI Design System", "PUB-2025-030", "Typography, spacing, and component guidelines.", "Design", "Developer Portal", "R535"),
        ("Accessibility Standards", "PUB-2025-031", "WCAG alignment and UI accessibility checks.", "Design", "Developer Portal", "R535"),
        ("Content Authoring Guide", "PUB-2025-032", "Best practices for clarity and consistency.", "Content", "Developer Portal", "R535"),
        ("Collaboration Features", "PUB-2025-033", "Real-time editing and review workflow.", "Collaboration", "Developer Portal", "R535"),
        ("Customer Enablement Kit", "PUB-2025-034", "Onboarding materials and enablement assets.", "Enablement", "Developer Portal", "R535"),
        ("API Reference Index", "PUB-2025-035", "Quick links to API surface areas.", "API", "Developer Portal", "R535"),
        ("Troubleshooting Matrix", "PUB-2025-036", "Known issues and resolution paths.", "Support", "Developer Portal", "R535"),
        ("Support & Access", "PUB-2025-037", "How to request access or submit tickets.", "Support", "Developer Portal", "R535"),
    ]

    for title, doc_num, description, category, platform_name, release_branch in extra_public_docs:
        topic = "platform"
        if category in ("Security",):
            topic = "security"
        elif category in ("SDK", "API"):
            topic = "sdk-tools"
        elif category in ("Operations", "Support", "Storage"):
            topic = "operations"
        elif category in ("Governance", "Compliance"):
            topic = "governance"
        elif category in ("Design", "Content"):
            topic = "design-systems"
        elif category in ("Release Documentation", "Release Notes", "Driver Versions"):
            topic = "release-management"

        documents_config.append(
            {
                "title": title,
                "doc_num": doc_num,
                "description": description,
                "category": category,
                "topic": topic,
                "platform": platform_name,
                "release_branch": release_branch,
                "tags": f"{category.lower()},docs,public",
                "visibility": DocumentVisibility.PUBLIC,
                "content": f"<h1>{title}</h1><p>{description}</p>",
            }
        )

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
                topic=doc_data.get("topic"),
                platform=doc_data.get("platform"),
                release_branch=doc_data.get("release_branch"),
                tags=doc_data.get("tags"),
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
                semantic_version="1.0.0",
                bump_type=VersionBumpType.MAJOR,
                content=doc_data["content"],
                changes_summary="Initial version",
                created_by=admin.id,
                is_published=True,
                published_at=datetime.utcnow(),
                published_by=admin.id,
            )
            db.add(version)

            # Assign company if specified
            if doc_data.get("assigned_company"):
                doc.assigned_companies.append(doc_data["assigned_company"])

            print(f"   ✓ Created '{doc_data['title']}' ({doc_data['visibility'].value})")
        else:
            updated = False
            if doc_data.get("category") and existing.category != doc_data.get("category"):
                existing.category = doc_data["category"]
                updated = True
            if doc_data.get("topic") and existing.topic != doc_data.get("topic"):
                existing.topic = doc_data["topic"]
                updated = True
            if doc_data.get("platform") and existing.platform != doc_data.get("platform"):
                existing.platform = doc_data["platform"]
                updated = True
            if doc_data.get("release_branch") and existing.release_branch != doc_data.get("release_branch"):
                existing.release_branch = doc_data["release_branch"]
                updated = True
            if doc_data.get("tags") and existing.tags != doc_data.get("tags"):
                existing.tags = doc_data["tags"]
                updated = True
            if updated:
                print(f"   ✓ Updated '{doc_data['title']}'")
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
    print("Creating test data for the Documentation Platform...")

    ensure_demo_seed_allowed()

    # Ensure schema and lightweight migrations are always applied before seeding.
    init_db()

    db = SessionLocal()

    try:
        # Step 1: Create tenants
        tenants = create_tenants(db)

        # Step 2: Create users
        users = create_users(db, tenants)

        # Step 3: Create topics
        create_topics(db)

        # Step 4: Create documents
        create_documents(db, tenants, users)

        # Step 5: Print summary
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
