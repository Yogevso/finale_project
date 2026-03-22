"""Durable reader-artifact conversion job queue.

This module persists conversion jobs in the database, so pending work survives
process restarts and can be handled by a dedicated worker process.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.application.process_managers import PreviewConversionProcessManager
from app.db import SessionLocal
from app.jobs import (
    AsyncJobBatchReport,
    AsyncJobDisposition,
    RetryPolicy,
    compute_retry_delay_seconds,
    evaluate_retry,
    run_polling_worker,
)
from app.models import Attachment, AttachmentArtifact, AttachmentConversionJob

logger = logging.getLogger(__name__)

JOB_TYPE_READER_HTML = "reader_html"
JOB_TYPE_PDF_EXPORT = "pdf_export"
JOB_STATUS_PENDING = "pending"
JOB_STATUS_PROCESSING = "processing"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"

ARTIFACT_KIND_READER_HTML = "reader_html"
ARTIFACT_STATUS_READY = "ready"
ARTIFACT_STATUS_FAILED = "failed"
PROCESSING_TIMEOUT_SECONDS = max(
    30,
    int(os.getenv("CONVERSION_JOB_PROCESSING_TIMEOUT_SECONDS", "300")),
)
CONVERSION_WORKER_NAME = "conversion"


def _default_retry_policy() -> RetryPolicy:
    base_delay = max(0, int(os.getenv("CONVERSION_JOB_RETRY_DELAY_SECONDS", "30")))
    max_delay = max(base_delay * 10, int(os.getenv("CONVERSION_JOB_MAX_RETRY_DELAY_SECONDS", "300")))
    multiplier = max(
        1.0,
        float(os.getenv("CONVERSION_JOB_RETRY_BACKOFF_MULTIPLIER", "2.0")),
    )
    return RetryPolicy(
        base_delay_seconds=base_delay,
        max_delay_seconds=max_delay,
        backoff_multiplier=multiplier,
    )


def _get_or_create_job(
    db: Session, attachment_id: int, job_type: str = JOB_TYPE_READER_HTML
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


def _load_reader_artifact_status(
    db: Session, attachment_id: int
) -> tuple[Optional[str], Optional[str]]:
    artifact = (
        db.query(AttachmentArtifact)
        .filter(
            AttachmentArtifact.attachment_id == attachment_id,
            AttachmentArtifact.kind == ARTIFACT_KIND_READER_HTML,
        )
        .first()
    )
    if not artifact:
        return None, None
    return artifact.status, artifact.error


def _recover_stale_processing_jobs(db: Session, now: datetime, job_type: str = JOB_TYPE_READER_HTML) -> int:
    stale_before = now - timedelta(seconds=PROCESSING_TIMEOUT_SECONDS)
    stale_jobs = (
        db.query(AttachmentConversionJob)
        .filter(
            AttachmentConversionJob.job_type == job_type,
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
            job.last_error = (
                f"[DLQ:attempt_limit_reached({int(job.attempts or 0)}/{int(job.max_attempts or 3)})] "
                f"{job.last_error}"
            )
        else:
            job.status = JOB_STATUS_PENDING
            job.finished_at = None

    return recovered_count


def _claim_job_by_id(db: Session, job_id: int, now: datetime, job_type: str = JOB_TYPE_READER_HTML) -> bool:
    updated = (
        db.query(AttachmentConversionJob)
        .filter(
            AttachmentConversionJob.id == job_id,
            AttachmentConversionJob.job_type == job_type,
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


def _claim_next_runnable_job_id(
    db: Session, now: datetime, *, max_attempts: int = 5, job_type: str = JOB_TYPE_READER_HTML
) -> Optional[int]:
    for _ in range(max_attempts):
        row = (
            db.query(AttachmentConversionJob.id)
            .filter(
                AttachmentConversionJob.job_type == job_type,
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


def _job_disposition(job: AttachmentConversionJob) -> AsyncJobDisposition:
    if job.status == JOB_STATUS_COMPLETED:
        return AsyncJobDisposition.COMPLETED
    if job.status == JOB_STATUS_FAILED:
        return AsyncJobDisposition.DEAD_LETTER
    if job.status == JOB_STATUS_PENDING:
        return AsyncJobDisposition.RETRY
    return AsyncJobDisposition.SKIPPED


def process_conversion_job(
    job_id: int,
    *,
    force: bool = False,
    claimed: bool = False,
    retry_policy: RetryPolicy | None = None,
) -> AsyncJobDisposition:
    """Execute one persisted conversion job."""
    from app.services.attachment_service import AttachmentService

    policy = retry_policy or _default_retry_policy()
    db = SessionLocal()
    try:
        job = db.query(AttachmentConversionJob).filter(AttachmentConversionJob.id == job_id).first()
        if not job:
            return AsyncJobDisposition.SKIPPED
        if claimed:
            if job.status != JOB_STATUS_PROCESSING:
                return AsyncJobDisposition.SKIPPED
        else:
            now = datetime.utcnow()
            recovered = _recover_stale_processing_jobs(db, now)
            claimed_ok = _claim_job_by_id(db, job_id, now)
            if recovered or claimed_ok:
                db.commit()
            else:
                db.rollback()
            if not claimed_ok:
                return AsyncJobDisposition.SKIPPED
            job = db.query(AttachmentConversionJob).filter(AttachmentConversionJob.id == job_id).first()
            if not job:
                return AsyncJobDisposition.SKIPPED

        retry_delay_seconds = compute_retry_delay_seconds(
            attempt_number=max(1, int(job.attempts or 1)),
            policy=policy,
        )

        workflow = PreviewConversionProcessManager(
            preview_generator=lambda attachment_id: AttachmentService.generate_reader_artifact(
                attachment_id,
                force=bool(force or job.force),
            ),
            preview_status_loader=lambda attachment_id: _load_reader_artifact_status(
                db,
                attachment_id,
            ),
            status_ready=ARTIFACT_STATUS_READY,
            status_failed=ARTIFACT_STATUS_FAILED,
            job_status_pending=JOB_STATUS_PENDING,
            job_status_completed=JOB_STATUS_COMPLETED,
            job_status_failed=JOB_STATUS_FAILED,
        )
        trace = workflow.execute(
            job,
            retry_delay_seconds=retry_delay_seconds,
            fallback_probe_delay_seconds=10,
            status_failure_retry_delay_seconds=retry_delay_seconds,
        )
        if trace.error:
            logger.exception(
                "Conversion workflow failed for job %s at step %s: %s",
                job_id,
                trace.failed_step,
                trace.error,
            )

        db.commit()
        return _job_disposition(job)
    except Exception as exc:
        logger.exception("Conversion job %s failed unexpectedly", job_id)
        db.rollback()
        job = db.query(AttachmentConversionJob).filter(AttachmentConversionJob.id == job_id).first()
        if not job or job.status != JOB_STATUS_PROCESSING:
            return AsyncJobDisposition.SKIPPED

        decision = evaluate_retry(
            attempts=int(job.attempts or 0),
            max_attempts=int(job.max_attempts or 3),
            error=str(exc),
            policy=policy,
        )
        now = datetime.utcnow()
        job.started_at = None
        if decision.disposition == AsyncJobDisposition.DEAD_LETTER:
            job.status = JOB_STATUS_FAILED
            job.finished_at = now
            job.next_run_at = None
            job.last_error = f"[DLQ:{decision.reason}] {exc}"
            db.commit()
            return AsyncJobDisposition.DEAD_LETTER

        job.status = JOB_STATUS_PENDING
        job.finished_at = None
        job.next_run_at = now + timedelta(seconds=max(0, int(decision.next_delay_seconds or 0)))
        job.last_error = str(exc)
        db.commit()
        return AsyncJobDisposition.RETRY
    finally:
        db.close()


def process_pending_jobs_batch(
    *,
    batch_size: int = 10,
    force: bool = False,
    retry_policy: RetryPolicy | None = None,
) -> AsyncJobBatchReport:
    """Process one batch of pending conversion jobs and return detailed counters."""
    report = AsyncJobBatchReport(worker_name=CONVERSION_WORKER_NAME)
    policy = retry_policy or _default_retry_policy()
    handled = 0

    while handled < max(1, int(batch_size)):
        claimed_job_id: Optional[int] = None
        recovered_count = 0
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            recovered_count = _recover_stale_processing_jobs(db, now)
            claimed_job_id = _claim_next_runnable_job_id(db, now)
            if recovered_count or claimed_job_id is not None:
                db.commit()
            else:
                db.rollback()
        finally:
            db.close()

        report.recovered += recovered_count
        if claimed_job_id is None:
            break

        handled += 1
        report.attempted += 1
        disposition = process_conversion_job(
            claimed_job_id,
            force=force,
            claimed=True,
            retry_policy=policy,
        )
        if disposition == AsyncJobDisposition.COMPLETED:
            report.completed += 1
        elif disposition == AsyncJobDisposition.RETRY:
            report.retried += 1
        elif disposition == AsyncJobDisposition.DEAD_LETTER:
            report.dead_lettered += 1
        else:
            report.skipped += 1

    return report


def process_pending_jobs_once(*, batch_size: int = 10, force: bool = False) -> int:
    """Compatibility wrapper returning attempted conversion-job count."""
    report = process_pending_jobs_batch(batch_size=batch_size, force=force)
    return report.attempted


def enqueue_conversion(
    attachment_id: int,
    *,
    background_tasks: Optional[BackgroundTasks] = None,
    force: bool = False,
) -> None:
    """Enqueue reader-artifact generation as a durable DB job."""
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


def list_dead_letter_conversion_jobs(
    *,
    limit: int = 100,
    db: Session | None = None,
) -> list[AttachmentConversionJob]:
    """List conversion jobs currently parked in DLQ/failed state."""
    owns_session = db is None
    session = db or SessionLocal()
    try:
        return (
            session.query(AttachmentConversionJob)
            .filter(
                AttachmentConversionJob.job_type == JOB_TYPE_READER_HTML,
                AttachmentConversionJob.status == JOB_STATUS_FAILED,
            )
            .order_by(AttachmentConversionJob.finished_at.desc(), AttachmentConversionJob.id.desc())
            .limit(max(1, int(limit)))
            .all()
        )
    finally:
        if owns_session:
            session.close()


def requeue_dead_letter_conversion_job(
    job_id: int,
    *,
    force: bool = False,
    reset_attempts: bool = False,
    db: Session | None = None,
) -> bool:
    """Requeue one failed conversion job for operator-driven recovery."""
    owns_session = db is None
    session = db or SessionLocal()
    try:
        job = (
            session.query(AttachmentConversionJob)
            .filter(
                AttachmentConversionJob.id == job_id,
                AttachmentConversionJob.job_type == JOB_TYPE_READER_HTML,
                AttachmentConversionJob.status == JOB_STATUS_FAILED,
            )
            .first()
        )
        if not job:
            return False

        job.status = JOB_STATUS_PENDING
        job.force = bool(force or job.force)
        job.started_at = None
        job.finished_at = None
        job.next_run_at = None
        job.last_error = None
        if reset_attempts:
            job.attempts = 0
        session.commit()
        return True
    finally:
        if owns_session:
            session.close()


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
    policy = _default_retry_policy()
    run_polling_worker(
        worker_name=CONVERSION_WORKER_NAME,
        logger=logger,
        poll_interval_seconds=poll_interval_seconds,
        batch_size=batch_size,
        once=once,
        process_batch=lambda size: process_pending_jobs_batch(
            batch_size=size,
            force=force,
            retry_policy=policy,
        ),
    )


# ---------------------------------------------------------------------------
# PDF Export Jobs (FIX-022)
# ---------------------------------------------------------------------------

PDF_EXPORT_WORKER_NAME = "pdf_export"


def _execute_pdf_export(attachment_id: int, db: Session) -> None:
    """Run the actual PDF export rendering for one attachment."""
    from app.services.pdf_export_service import render_html_to_pdf

    att = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not att:
        raise ValueError(f"Attachment {attachment_id} not found")

    reader = (
        db.query(AttachmentArtifact)
        .filter(
            AttachmentArtifact.attachment_id == attachment_id,
            AttachmentArtifact.kind == "reader_html",
            AttachmentArtifact.status == "completed",
        )
        .first()
    )
    html = reader.content_text if reader else None
    if not html:
        raise ValueError(f"No completed reader_html artifact for attachment {attachment_id}")

    pdf_bytes = render_html_to_pdf(html, title=att.original_filename or "document")
    if not pdf_bytes:
        raise RuntimeError(f"PDF render returned empty bytes for attachment {attachment_id}")

    existing = (
        db.query(AttachmentArtifact)
        .filter(
            AttachmentArtifact.attachment_id == attachment_id,
            AttachmentArtifact.kind == "pdf_export",
        )
        .first()
    )
    if existing:
        existing.content_text = None
        existing.content_json = None
        existing.size_bytes = len(pdf_bytes)
        existing.status = "completed"
        existing.mime_type = "application/pdf"
        existing.storage_key = f"pdf_export/{attachment_id}.pdf"
    else:
        existing = AttachmentArtifact(
            attachment_id=attachment_id,
            kind="pdf_export",
            status="completed",
            mime_type="application/pdf",
            size_bytes=len(pdf_bytes),
            storage_key=f"pdf_export/{attachment_id}.pdf",
        )
        db.add(existing)

    import io
    from app.services.attachment_service.common import get_storage_backend
    storage = get_storage_backend()
    storage.upload(io.BytesIO(pdf_bytes), f"pdf_export/{attachment_id}.pdf", "application/pdf")


def process_pdf_export_job(
    job_id: int,
    *,
    claimed: bool = False,
    retry_policy: RetryPolicy | None = None,
) -> AsyncJobDisposition:
    """Execute one persisted PDF export job with retry support."""
    policy = retry_policy or _default_retry_policy()
    db = SessionLocal()
    try:
        job = db.query(AttachmentConversionJob).filter(AttachmentConversionJob.id == job_id).first()
        if not job:
            return AsyncJobDisposition.SKIPPED
        if claimed:
            if job.status != JOB_STATUS_PROCESSING:
                return AsyncJobDisposition.SKIPPED
        else:
            now = datetime.utcnow()
            recovered = _recover_stale_processing_jobs(db, now, job_type=JOB_TYPE_PDF_EXPORT)
            claimed_ok = _claim_job_by_id(db, job_id, now, job_type=JOB_TYPE_PDF_EXPORT)
            if recovered or claimed_ok:
                db.commit()
            else:
                db.rollback()
            if not claimed_ok:
                return AsyncJobDisposition.SKIPPED
            job = db.query(AttachmentConversionJob).filter(AttachmentConversionJob.id == job_id).first()
            if not job:
                return AsyncJobDisposition.SKIPPED

        _execute_pdf_export(job.attachment_id, db)
        now = datetime.utcnow()
        job.status = JOB_STATUS_COMPLETED
        job.finished_at = now
        job.last_error = None
        db.commit()
        return AsyncJobDisposition.COMPLETED
    except Exception as exc:
        logger.exception("PDF export job %s failed", job_id)
        db.rollback()
        job = db.query(AttachmentConversionJob).filter(AttachmentConversionJob.id == job_id).first()
        if not job or job.status != JOB_STATUS_PROCESSING:
            return AsyncJobDisposition.SKIPPED

        decision = evaluate_retry(
            attempts=int(job.attempts or 0),
            max_attempts=int(job.max_attempts or 3),
            error=str(exc),
            policy=policy,
        )
        now = datetime.utcnow()
        job.started_at = None
        if decision.disposition == AsyncJobDisposition.DEAD_LETTER:
            job.status = JOB_STATUS_FAILED
            job.finished_at = now
            job.next_run_at = None
            job.last_error = f"[DLQ:{decision.reason}] {exc}"
            db.commit()
            return AsyncJobDisposition.DEAD_LETTER

        job.status = JOB_STATUS_PENDING
        job.finished_at = None
        job.next_run_at = now + timedelta(seconds=max(0, int(decision.next_delay_seconds or 0)))
        job.last_error = str(exc)
        db.commit()
        return AsyncJobDisposition.RETRY
    finally:
        db.close()


def process_pending_pdf_export_batch(
    *,
    batch_size: int = 10,
    retry_policy: RetryPolicy | None = None,
) -> AsyncJobBatchReport:
    """Process one batch of pending PDF export jobs."""
    report = AsyncJobBatchReport(worker_name=PDF_EXPORT_WORKER_NAME)
    policy = retry_policy or _default_retry_policy()
    handled = 0

    while handled < max(1, int(batch_size)):
        claimed_job_id: Optional[int] = None
        recovered_count = 0
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            recovered_count = _recover_stale_processing_jobs(db, now, job_type=JOB_TYPE_PDF_EXPORT)
            claimed_job_id = _claim_next_runnable_job_id(db, now, job_type=JOB_TYPE_PDF_EXPORT)
            if recovered_count or claimed_job_id is not None:
                db.commit()
            else:
                db.rollback()
        finally:
            db.close()

        report.recovered += recovered_count
        if claimed_job_id is None:
            break

        handled += 1
        report.attempted += 1
        disposition = process_pdf_export_job(claimed_job_id, claimed=True, retry_policy=policy)
        if disposition == AsyncJobDisposition.COMPLETED:
            report.completed += 1
        elif disposition == AsyncJobDisposition.RETRY:
            report.retried += 1
        elif disposition == AsyncJobDisposition.DEAD_LETTER:
            report.dead_lettered += 1
        else:
            report.skipped += 1

    return report


def enqueue_pdf_export(
    attachment_ids: list[int],
    *,
    background_tasks: Optional[BackgroundTasks] = None,
) -> None:
    """Enqueue PDF export generation as durable DB jobs."""
    db = SessionLocal()
    try:
        for attachment_id in attachment_ids:
            job = _get_or_create_job(db, attachment_id=attachment_id, job_type=JOB_TYPE_PDF_EXPORT)
            _set_job_pending(job, force=False)
        db.commit()
    finally:
        db.close()

    if background_tasks is not None:
        background_tasks.add_task(
            lambda: process_pending_pdf_export_batch(batch_size=len(attachment_ids)),
        )


def process_all_pending_batch(
    *,
    batch_size: int = 10,
    force: bool = False,
    retry_policy: RetryPolicy | None = None,
) -> AsyncJobBatchReport:
    """Process both conversion and PDF export jobs in one batch cycle."""
    conv_report = process_pending_jobs_batch(
        batch_size=batch_size, force=force, retry_policy=retry_policy,
    )
    pdf_report = process_pending_pdf_export_batch(
        batch_size=batch_size, retry_policy=retry_policy,
    )
    combined = AsyncJobBatchReport(worker_name=CONVERSION_WORKER_NAME)
    combined.attempted = conv_report.attempted + pdf_report.attempted
    combined.completed = conv_report.completed + pdf_report.completed
    combined.retried = conv_report.retried + pdf_report.retried
    combined.dead_lettered = conv_report.dead_lettered + pdf_report.dead_lettered
    combined.skipped = conv_report.skipped + pdf_report.skipped
    combined.recovered = conv_report.recovered + pdf_report.recovered
    return combined


def run_all_jobs_worker(
    *,
    poll_interval_seconds: float = 2.0,
    batch_size: int = 10,
    once: bool = False,
    force: bool = False,
) -> None:
    """Run worker loop processing both conversion and PDF export jobs."""
    policy = _default_retry_policy()
    run_polling_worker(
        worker_name=CONVERSION_WORKER_NAME,
        logger=logger,
        poll_interval_seconds=poll_interval_seconds,
        batch_size=batch_size,
        once=once,
        process_batch=lambda size: process_all_pending_batch(
            batch_size=size,
            force=force,
            retry_policy=policy,
        ),
    )
