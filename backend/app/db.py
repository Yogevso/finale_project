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
        # Add missing columns to documents table for forward compatibility.
        columns = conn.execute(text("PRAGMA table_info(documents)")).fetchall()
        existing = {row[1] for row in columns}
        required_document_columns = {
            "topic": "ALTER TABLE documents ADD COLUMN topic VARCHAR(150)",
            "platform": "ALTER TABLE documents ADD COLUMN platform VARCHAR(100)",
            "version_label": "ALTER TABLE documents ADD COLUMN version_label VARCHAR(50)",
            "parent_id": "ALTER TABLE documents ADD COLUMN parent_id INTEGER",
            "release_branch": "ALTER TABLE documents ADD COLUMN release_branch VARCHAR(100)",
        }
        for column_name, ddl in required_document_columns.items():
            if column_name not in existing:
                conn.execute(text(ddl))

        # Add missing columns to versions table for semantic version workflow.
        version_columns = conn.execute(text("PRAGMA table_info(versions)")).fetchall()
        existing_version_columns = {row[1] for row in version_columns}
        required_version_columns = {
            "semantic_version": "ALTER TABLE versions ADD COLUMN semantic_version VARCHAR(32)",
            "bump_type": "ALTER TABLE versions ADD COLUMN bump_type VARCHAR(10) DEFAULT 'PATCH' NOT NULL",
            "published_by": "ALTER TABLE versions ADD COLUMN published_by INTEGER",
        }
        for column_name, ddl in required_version_columns.items():
            if column_name not in existing_version_columns:
                conn.execute(text(ddl))

        # Backfill semantic_version if missing on old rows.
        if "semantic_version" in existing_version_columns or "semantic_version" in required_version_columns:
            conn.execute(
                text(
                    "UPDATE versions "
                    "SET semantic_version = CASE "
                    "WHEN version_number IS NULL OR version_number < 1 THEN '1.0.0' "
                    "ELSE CAST(version_number AS TEXT) || '.0.0' END "
                    "WHERE semantic_version IS NULL OR TRIM(semantic_version) = ''"
                )
            )

        # SQLAlchemy enums in this project persist enum member names (e.g. PATCH).
        # Normalize legacy lowercase values that might exist from older writes.
        conn.execute(
            text(
                "UPDATE versions "
                "SET bump_type = CASE LOWER(COALESCE(bump_type, '')) "
                "WHEN 'major' THEN 'MAJOR' "
                "WHEN 'minor' THEN 'MINOR' "
                "WHEN 'patch' THEN 'PATCH' "
                "ELSE COALESCE(bump_type, 'PATCH') END"
            )
        )
        conn.commit()
