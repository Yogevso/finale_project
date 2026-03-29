from __future__ import annotations

from datetime import datetime

from sqlalchemy import text

from app.infrastructure.db.lightweight_migrations import run_lightweight_migrations
from app.models import DocumentStatus, Version, VersionBumpType
from tests.factories import create_document, create_user


def test_lightweight_migrations_repair_published_document_status_drift(db):
    user = create_user(db)
    document = create_document(
        db,
        created_by=user.id,
        tenant_id=user.tenant_id,
        status=DocumentStatus.APPROVED,
    )
    db.add(
        Version(
            document_id=document.id,
            version_number=1,
            semantic_version="1.0.0",
            bump_type=VersionBumpType.MAJOR,
            content="<p>Published upload</p>",
            changes_summary="Initial publish",
            is_published=True,
            published_at=datetime.utcnow(),
            published_by=user.id,
            created_by=user.id,
        )
    )
    db.commit()

    bind = db.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    run_lightweight_migrations(engine=engine, skip_versions_semantic_migration=False)
    db.refresh(document)

    assert document.status == DocumentStatus.ACTIVE


def test_lightweight_migrations_add_feedback_anchor_text_column(db):
    bind = db.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind

    run_lightweight_migrations(engine=engine, skip_versions_semantic_migration=False)

    columns = db.execute(text("PRAGMA table_info(feedbacks)")).fetchall()
    column_names = {column[1] for column in columns}

    assert "anchor_text" in column_names
