"""Database Session Management"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# Create SQLite engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # Needed for SQLite
    echo=settings.DEBUG,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database - create all tables"""
    Base.metadata.create_all(bind=engine)
    _run_lightweight_migrations()


def _run_lightweight_migrations() -> None:
    """Apply lightweight migrations for SQLite without Alembic."""
    with engine.connect() as conn:
        # Add missing columns to documents table
        columns = conn.execute(text("PRAGMA table_info(documents)")).fetchall()
        existing = {row[1] for row in columns}
        if "topic" not in existing:
            conn.execute(text("ALTER TABLE documents ADD COLUMN topic VARCHAR(150)"))
        if "platform" not in existing:
            conn.execute(text("ALTER TABLE documents ADD COLUMN platform VARCHAR(100)"))
        if "version_label" not in existing:
            conn.execute(text("ALTER TABLE documents ADD COLUMN version_label VARCHAR(50)"))
        if "parent_id" not in existing:
            conn.execute(text("ALTER TABLE documents ADD COLUMN parent_id INTEGER"))
        conn.commit()
