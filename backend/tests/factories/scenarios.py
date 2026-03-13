"""Scenario-level fixtures composed from low-level builders."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import DocumentStatus
from tests.factories.domain import (
    create_attachment,
    create_attachment_conversion_job,
    create_document,
)


@dataclass(frozen=True)
class ConversionJobScenario:
    document_id: int
    attachment_id: int
    job_id: int


def create_conversion_job_scenario(
    db: Session,
    *,
    created_by: int,
    document_title: str = "Conversion Job Doc",
    job_type: str = "reader_html",
    job_status: str = "pending",
    job_attempts: int = 0,
    job_max_attempts: int = 3,
    started_at: datetime | None = None,
    force: bool = False,
) -> ConversionJobScenario:
    """Create a document -> attachment -> conversion job chain."""
    document = create_document(
        db,
        created_by=created_by,
        title=document_title,
        status=DocumentStatus.DRAFT,
    )
    attachment = create_attachment(
        db,
        document_id=document.id,
        uploaded_by=created_by,
        filename="conversion-source.docx",
    )
    job = create_attachment_conversion_job(
        db,
        attachment_id=attachment.id,
        job_type=job_type,
        status=job_status,
        force=force,
        attempts=job_attempts,
        max_attempts=job_max_attempts,
        started_at=started_at,
    )
    return ConversionJobScenario(
        document_id=document.id,
        attachment_id=attachment.id,
        job_id=job.id,
    )
