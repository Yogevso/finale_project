"""Database Session Management"""

import re

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

    def slugify(value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
        return normalized or "platform"

    with engine.connect() as conn:
        # Ensure platforms table exists for normalized platform linkage.
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS platforms (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    slug VARCHAR(120) NOT NULL UNIQUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
                """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_platforms_name ON platforms (name)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_platforms_slug ON platforms (slug)"))

        # Add missing columns to documents table for forward compatibility.
        columns = conn.execute(text("PRAGMA table_info(documents)")).fetchall()
        existing = {row[1] for row in columns}
        required_document_columns = {
            "topic": "ALTER TABLE documents ADD COLUMN topic VARCHAR(150)",
            "platform": "ALTER TABLE documents ADD COLUMN platform VARCHAR(100)",
            "platform_id": "ALTER TABLE documents ADD COLUMN platform_id INTEGER",
            "version_label": "ALTER TABLE documents ADD COLUMN version_label VARCHAR(50)",
            "parent_id": "ALTER TABLE documents ADD COLUMN parent_id INTEGER",
            "release_branch": "ALTER TABLE documents ADD COLUMN release_branch VARCHAR(100)",
        }
        for column_name, ddl in required_document_columns.items():
            if column_name not in existing:
                conn.execute(text(ddl))
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_documents_platform_id ON documents (platform_id)")
        )

        # Ensure an "Unspecified" platform exists and map legacy platform strings to IDs.
        conn.execute(
            text(
                """
                INSERT OR IGNORE INTO platforms (name, slug, created_at, updated_at)
                VALUES ('Unspecified', 'unspecified', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            )
        )
        unspecified_id = conn.execute(
            text("SELECT id FROM platforms WHERE slug = 'unspecified' LIMIT 1")
        ).scalar()

        platform_names = conn.execute(
            text(
                """
                SELECT DISTINCT TRIM(platform) AS platform_name
                FROM documents
                WHERE platform IS NOT NULL AND TRIM(platform) != ''
                """
            )
        ).fetchall()
        for row in platform_names:
            platform_name = row[0]
            if not platform_name:
                continue

            existing_platform_id = conn.execute(
                text(
                    """
                    SELECT id FROM platforms
                    WHERE LOWER(name) = LOWER(:name)
                    LIMIT 1
                    """
                ),
                {"name": platform_name},
            ).scalar()
            if existing_platform_id:
                continue

            base_slug = slugify(platform_name)
            slug = base_slug
            suffix = 2
            while conn.execute(
                text("SELECT 1 FROM platforms WHERE slug = :slug LIMIT 1"), {"slug": slug}
            ).scalar():
                slug = f"{base_slug}-{suffix}"
                suffix += 1

            conn.execute(
                text(
                    """
                    INSERT INTO platforms (name, slug, created_at, updated_at)
                    VALUES (:name, :slug, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """
                ),
                {"name": platform_name, "slug": slug},
            )

        platforms = conn.execute(text("SELECT id, name FROM platforms")).fetchall()
        for platform_id, platform_name in platforms:
            conn.execute(
                text(
                    """
                    UPDATE documents
                    SET platform_id = :platform_id
                    WHERE platform_id IS NULL
                      AND platform IS NOT NULL
                      AND LOWER(TRIM(platform)) = LOWER(:platform_name)
                    """
                ),
                {"platform_id": platform_id, "platform_name": platform_name},
            )

        # Backfill missing values to the "Unspecified" platform.
        if unspecified_id is not None:
            conn.execute(
                text(
                    """
                    UPDATE documents
                    SET platform = 'Unspecified',
                        platform_id = :platform_id
                    WHERE platform_id IS NULL
                    """
                ),
                {"platform_id": unspecified_id},
            )

        # Add attachment integrity metadata columns for byte-preserving originals.
        attachment_columns = conn.execute(text("PRAGMA table_info(attachments)")).fetchall()
        existing_attachment_columns = {row[1] for row in attachment_columns}
        required_attachment_columns = {
            "size_bytes": "ALTER TABLE attachments ADD COLUMN size_bytes INTEGER",
            "storage_key": "ALTER TABLE attachments ADD COLUMN storage_key VARCHAR(500)",
            "sha256": "ALTER TABLE attachments ADD COLUMN sha256 VARCHAR(64)",
            "reader_html_status": "ALTER TABLE attachments ADD COLUMN reader_html_status VARCHAR(20)",
            "reader_html_content": "ALTER TABLE attachments ADD COLUMN reader_html_content TEXT",
            "reader_toc_json": "ALTER TABLE attachments ADD COLUMN reader_toc_json TEXT",
            "reader_toc_source": "ALTER TABLE attachments ADD COLUMN reader_toc_source VARCHAR(20)",
            "reader_html_error": "ALTER TABLE attachments ADD COLUMN reader_html_error TEXT",
            "reader_html_generated_at": "ALTER TABLE attachments ADD COLUMN reader_html_generated_at DATETIME",
        }
        for column_name, ddl in required_attachment_columns.items():
            if column_name not in existing_attachment_columns:
                conn.execute(text(ddl))

        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_attachments_storage_key ON attachments (storage_key)"
            )
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_attachments_sha256 ON attachments (sha256)")
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_attachments_reader_html_status "
                "ON attachments (reader_html_status)"
            )
        )

        # Backfill aliases for legacy rows.
        conn.execute(
            text(
                """
                UPDATE attachments
                SET size_bytes = file_size
                WHERE size_bytes IS NULL
                  AND file_size IS NOT NULL
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE attachments
                SET storage_key = storage_path
                WHERE storage_key IS NULL
                  AND storage_path IS NOT NULL
                """
            )
        )

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
        if (
            "semantic_version" in existing_version_columns
            or "semantic_version" in required_version_columns
        ):
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
