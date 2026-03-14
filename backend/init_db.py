"""Database Initialization Script"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import SessionLocal, init_db
from app.models import User, UserRole
from app.security import get_password_hash


def create_initial_users(db: Session):
    """Create initial admin and test users"""

    # Check if admin already exists
    admin = db.query(User).filter(User.username == "admin").first()
    if admin:
        print("Admin user already exists")
        return

    # Create admin user
    admin = User(
        email="admin@portal.com",
        username="admin",
        full_name="System Administrator",
        hashed_password=get_password_hash("admin123"),
        role=UserRole.ADMIN,
        is_active=True
    )
    db.add(admin)

    # Create editor user
    editor = User(
        email="editor@portal.com",
        username="editor",
        full_name="Document Editor",
        hashed_password=get_password_hash("editor123"),
        role=UserRole.EDITOR,
        is_active=True
    )
    db.add(editor)

    # Create viewer user
    viewer = User(
        email="viewer@portal.com",
        username="viewer",
        full_name="Document Viewer",
        hashed_password=get_password_hash("viewer123"),
        role=UserRole.VIEWER,
        is_active=True
    )
    db.add(viewer)

    db.commit()
    print("✅ Created initial users:")
    print("   - admin / admin123 (Admin)")
    print("   - editor / editor123 (Editor)")
    print("   - viewer / viewer123 (Viewer)")


def main():
    """Initialize database and create initial data"""
    print("🚀 Initializing database...")

    # Create all tables
    init_db()
    print("✅ Database tables created")

    # Create FTS5 virtual table for full-text search
    db = SessionLocal()
    try:
        # Create FTS5 table for document search
        db.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                title,
                description,
                category,
                tags
            )
        """))
        db.commit()
        print("✅ FTS5 search index created")

        create_initial_users(db)
    finally:
        db.close()

    print("✅ Database initialization complete!")


if __name__ == "__main__":
    main()
