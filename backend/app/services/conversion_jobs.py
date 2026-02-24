"""Durable preview-PDF conversion job queue.

This module persists conversion jobs in the database, so pending work survives
process restarts and can be handled by a dedicated worker process.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta
from typing import Optional

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import AttachmentArtifact, AttachmentConversionJob

logger = logging.getLogger(__name__)

JOB_TYPE_PREVIEW_PDF = "preview_pdf"
JOB_STATUS_PENDING = "pending"
JOB_STATUS_PROCESSING = "processing"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"

ARTIFACT_KIND_PREVIEW_PDF = "preview_pdf"
ARTIFACT_STATUS_READY = "ready"
ARTIFACT_STATUS_FAILED = "failed"
PROCESSING_TIMEOUT_SECONDS = max(
    30,
    int(os.getenv("CONVERSION_JOB_PROCESSING_TIMEOUT_SECONDS", "300")),
)


def _get_or_create_job(
    db: Session, attachment_id: int, job_type: str = JOB_TYPE_PREVIEW_PDF
) -> AttachmentConversionJob:
    job = (
        db.query(AttachmentConversionJob)
        .filter(
            AttachmentConversionJob.attachment_id == attachment_id,
            AttachmentConversionJob.job_type == job_type,
        )
        .first()
    )
    if job:
        return job

    job = AttachmentConversionJob(
        attachment_id=attachment_id,
        job_type=job_type,
        status=JOB_STATUS_PENDING,
        attempts=0,
        max_attempts=3,
    )
    db.add(job)
    db.flush()
    return job


def _set_job_pending(job: AttachmentConversionJob, *, force: bool) -> None:
    job.status = JOB_STATUS_PENDING
    job.force = bool(force or job.force)
    job.last_error = None
    job.started_at = None
    job.finished_at = None
    job.next_run_at = None


def _load_preview_artifact_status(
    db: Session, attachment_id: int
) -> tuple[Optional[str], Optional[str]]:
    artifact = (
        db.query(AttachmentArtifact)
        .filter(
            AttachmentArtifact.attachment_id == attachment_id,
            AttachmentArtifact.kind == ARTIFACT_KIND_PREVIEW_PDF,
        )
        .first()
    )
    if not artifact:
        return None, None
    return artifact.status, artifact.error


def _recover_stale_processing_jobs(db: Session, now: datetime) -> int:
    stale_before = now - timedelta(seconds=PROCESSING_TIMEOUT_SECONDS)
    stale_jobs = (
        db.query(AttachmentConversionJob)
        .filter(
            AttachmentConversionJob.job_type == JOB_TYPE_PREVIEW_PDF,
            AttachmentConversionJob.status == JOB_STATUS_PROCESSING,
            AttachmentConversionJob.started_at.isnot(None),
            AttachmentConversionJob.started_at <= stale_before,
        )
        .all()
    )

    recovered_count = 0
    for job in stale_jobs:
        recovered_count += 1
        job.started_at = None
        job.next_run_at = now
        job.last_error = "Recovered stale processing job after lease timeout"
        if int(job.attempts or 0) >= int(job.max_attempts or 3):
            job.status = JOB_STATUS_FAILED
            job.finished_at = now
            job.next_run_at = None
        else:
            job.status = JOB_STATUS_PENDING
            job.finished_at = None

    return recovered_count


def _claim_job_by_id(db: Session, job_id: int, now: datetime) -> bool:
    updated = (
        db.query(AttachmentConversionJob)
        .filter(
            AttachmentConversionJob.id == job_id,
            AttachmentConversionJob.job_type == JOB_TYPE_PREVIEW_PDF,
            AttachmentConversionJob.status == JOB_STATUS_PENDING,
            (AttachmentConversionJob.next_run_at.is_(None))
            | (AttachmentConversionJob.next_run_at <= now),
        )
        .update(
            {
                AttachmentConversionJob.status: JOB_STATUS_PROCESSING,
                AttachmentConversionJob.started_at: now,
                AttachmentConversionJob.finished_at: None,
                AttachmentConversionJob.next_run_at: None,
                AttachmentConversionJob.last_error: None,
                AttachmentConversionJob.attempts: AttachmentConversionJob.attempts + 1,
            },
            synchronize_session=False,
        )
    )
    return updated == 1


def _claim_next_runnable_job_id(db: Session, now: datetime, *, max_attempts: int = 5) -> Optional[int]:
    for _ in range(max_attempts):
        row = (
            db.query(AttachmentConversionJob.id)
            .filter(
                AttachmentConversionJob.job_type == JOB_TYPE_PREVIEW_PDF,
                AttachmentConversionJob.status == JOB_STATUS_PENDING,
                (AttachmentConversionJob.next_run_at.is_(None))
                | (AttachmentConversionJob.next_run_at <= now),
            )
            .order_by(AttachmentConversionJob.created_at.asc(), AttachmentConversionJob.id.asc())
            .first()
        )
        if not row:
            return None

        job_id = row[0]
        if _claim_job_by_id(db, job_id, now):
            return int(job_id)

    return None


def process_conversion_job(job_id: int, *, force: bool = False, claimed: bool = False) -> None:
    """Execute one persisted conversion job."""
    from app.services.attachment_service import AttachmentService

    db = SessionLocal()
    try:
        job = db.query(AttachmentConversionJob).filter(AttachmentConversionJob.id == job_id).first()
        if not job:
            return
        if claimed:
            if job.status != JOB_STATUS_PROCESSING:
                return
        else:
            now = datetime.utcnow()
            recovered = _recover_stale_processing_jobs(db, now)
            claimed_ok = _claim_job_by_id(db, job_id, now)
            if recovered or claimed_ok:
                db.commit()
            else:
                db.rollback()
            if not claimed_ok:
                return
            job = (
                db.query(AttachmentConversionJob)
                .filter(AttachmentConversionJob.id == job_id)
                .first()
            )
            if not job:
                return

        AttachmentService.generate_preview_pdf_artifact(
            job.attachment_id,
            force=bool(force or job.force),
        )

        preview_status, preview_error = _load_preview_artifact_status(db, job.attachment_id)
        if preview_status == ARTIFACT_STATUS_READY:
            job.status = JOB_STATUS_COMPLETED
            job.last_error = None
            job.force = False
            job.finished_at = datetime.utcnow()
            job.next_run_at = None
        elif preview_status == ARTIFACT_STATUS_FAILED:
            job.last_error = preview_error or "Preview conversion failed"
            if int(job.attempts or 0) < int(job.max_attempts or 3):
                backoff_seconds = min(300, 10 * int(job.attempts or 1))
                job.status = JOB_STATUS_PENDING
                job.started_at = None
                job.finished_at = None
                job.next_run_at = datetime.utcnow() + timedelta(seconds=backoff_seconds)
            else:
                job.status = JOB_STATUS_FAILED
                job.finished_at = datetime.utcnow()
        else:
            # Conservative fallback: keep pending until artifact status resolves.
            job.status = JOB_STATUS_PENDING
            job.started_at = None
            job.finished_at = None
            job.next_run_at = datetime.utcnow() + timedelta(seconds=10)

        db.commit()
    except Exception as exc:
        logger.exception("Conversion job %s failed unexpectedly", job_id)
        try:
            job = (
                db.query(AttachmentConversionJob)
                .filter(AttachmentConversionJob.id == job_id)
                .first()
            )
            if job:
                job.last_error = str(exc)
                if int(job.attempts or 0) < int(job.max_attempts or 3):
                    job.status = JOB_STATUS_PENDING
                    job.started_at = None
                    job.finished_at = None
                    job.next_run_at = datetime.utcnow() + timedelta(seconds=30)
                else:
                    job.status = JOB_STATUS_FAILED
                    job.finished_at = datetime.utcnow()
                db.commit()
        except Exception:
            logger.exception("Failed persisting conversion job failure state for %s", job_id)
    finally:
        db.close()


def process_pending_jobs_once(*, batch_size: int = 10, force: bool = False) -> int:
    """Process one batch of pending conversion jobs and return processed count."""
    processed = 0

    while processed < batch_size:
        claimed_job_id: Optional[int] = None
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            recovered = _recover_stale_processing_jobs(db, now)
            claimed_job_id = _claim_next_runnable_job_id(db, now)
            if recovered or claimed_job_id is not None:
                db.commit()
            else:
                db.rollback()
        finally:
            db.close()

        if claimed_job_id is None:
            break

        process_conversion_job(claimed_job_id, force=force, claimed=True)
        processed += 1

    return processed


def enqueue_conversion(
    attachment_id: int,
    *,
    background_tasks: Optional[BackgroundTasks] = None,
    force: bool = False,
) -> None:
    """Enqueue preview_pdf conversion as a durable DB job."""
    db = SessionLocal()
    try:
        job = _get_or_create_job(db, attachment_id=attachment_id)
        _set_job_pending(job, force=force)
        db.commit()
    finally:
        db.close()

    # Optional fast-path in request lifecycle: process one pending job asynchronously.
    if background_tasks is not None:
        background_tasks.add_task(process_pending_jobs_once, batch_size=1, force=False)


def run_conversion_worker(
    *,
    poll_interval_seconds: float = 2.0,
    batch_size: int = 10,
    once: bool = False,
    force: bool = False,
) -> None:
    """Run durable conversion worker loop.

    Intended entrypoint for a standalone process:
    `python -m app.workers.conversion_worker`
    """
    logger.info(
        "Starting durable conversion worker (poll=%ss batch=%s once=%s)",
        poll_interval_seconds,
        batch_size,
        once,
    )

    while True:
        processed = process_pending_jobs_once(batch_size=batch_size, force=force)
        if once:
            return
        if processed == 0:
            time.sleep(max(0.5, poll_interval_seconds))
