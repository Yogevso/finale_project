"""Tests for durable attachment conversion job queue behavior."""

from datetime import datetime, timedelta

from sqlalchemy.orm import sessionmaker

from app.models import Attachment, AttachmentConversionJob, Document, DocumentStatus
from app.services import conversion_jobs
from app.services.attachment_service import AttachmentService


def _create_job(
    db,
    *,
    test_user,
    status: str = conversion_jobs.JOB_STATUS_PENDING,
    attempts: int = 0,
    max_attempts: int = 3,
    started_at=None,
):
    document = Document(
        title=f"Conversion Job Doc {status}",
        document_number=f"DOC-CONV-{status}-{attempts}-{max_attempts}-{int(datetime.utcnow().timestamp() * 1_000_000)}",
        status=DocumentStatus.DRAFT,
        created_by=test_user.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    attachment = Attachment(
        document_id=document.id,
        filename="conversion-source.pdf",
        original_filename="conversion-source.pdf",
        file_size=10,
        size_bytes=10,
        mime_type="application/pdf",
        storage_path="/tmp/conversion-source.pdf",
        storage_key="/tmp/conversion-source.pdf",
        uploaded_by=test_user.id,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    job = AttachmentConversionJob(
        attachment_id=attachment.id,
        job_type=conversion_jobs.JOB_TYPE_PREVIEW_PDF,
        status=status,
        attempts=attempts,
        max_attempts=max_attempts,
        started_at=started_at,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def test_process_pending_jobs_claims_unique_jobs(db, test_user, monkeypatch):
    """Each worker pass should claim different jobs rather than duplicating work."""
    job_one = _create_job(db, test_user=test_user)
    job_two = _create_job(db, test_user=test_user)

    worker_session = sessionmaker(bind=db.get_bind(), autocommit=False, autoflush=False)
    monkeypatch.setattr(conversion_jobs, "SessionLocal", worker_session)

    claimed_job_ids = []

    def fake_process(job_id, *, force=False, claimed=False, retry_policy=None):  # noqa: ARG001
        claimed_job_ids.append((job_id, claimed))
        session = worker_session()
        try:
            job = session.query(AttachmentConversionJob).filter(AttachmentConversionJob.id == job_id).first()
            if job:
                job.status = conversion_jobs.JOB_STATUS_COMPLETED
                job.finished_at = datetime.utcnow()
                session.commit()
        finally:
            session.close()

    monkeypatch.setattr(conversion_jobs, "process_conversion_job", fake_process)

    processed = conversion_jobs.process_pending_jobs_once(batch_size=2)
    assert processed == 2
    assert len(claimed_job_ids) == 2
    assert claimed_job_ids[0][1] is True
    assert claimed_job_ids[1][1] is True
    assert {claimed_job_ids[0][0], claimed_job_ids[1][0]} == {job_one.id, job_two.id}


def test_recover_stale_processing_job_to_pending(db, test_user):
    """Stale processing jobs under retry limit are recovered back to pending."""
    stale_started_at = datetime.utcnow() - timedelta(
        seconds=conversion_jobs.PROCESSING_TIMEOUT_SECONDS + 60
    )
    job = _create_job(
        db,
        test_user=test_user,
        status=conversion_jobs.JOB_STATUS_PROCESSING,
        attempts=1,
        max_attempts=3,
        started_at=stale_started_at,
    )

    recovered = conversion_jobs._recover_stale_processing_jobs(db, datetime.utcnow())
    db.commit()
    db.refresh(job)

    assert recovered == 1
    assert job.status == conversion_jobs.JOB_STATUS_PENDING
    assert job.started_at is None
    assert job.next_run_at is not None


def test_recover_stale_processing_job_marks_failed_at_attempt_limit(db, test_user):
    """Stale jobs that exhausted retries should transition to failed."""
    stale_started_at = datetime.utcnow() - timedelta(
        seconds=conversion_jobs.PROCESSING_TIMEOUT_SECONDS + 60
    )
    job = _create_job(
        db,
        test_user=test_user,
        status=conversion_jobs.JOB_STATUS_PROCESSING,
        attempts=3,
        max_attempts=3,
        started_at=stale_started_at,
    )

    recovered = conversion_jobs._recover_stale_processing_jobs(db, datetime.utcnow())
    db.commit()
    db.refresh(job)

    assert recovered == 1
    assert job.status == conversion_jobs.JOB_STATUS_FAILED
    assert job.finished_at is not None
    assert job.next_run_at is None


def test_job_failure_requeues_with_backoff(db, test_user, monkeypatch):
    """Unexpected conversion crashes should not leave jobs stuck in processing."""
    job = _create_job(db, test_user=test_user)
    worker_session = sessionmaker(bind=db.get_bind(), autocommit=False, autoflush=False)
    monkeypatch.setattr(conversion_jobs, "SessionLocal", worker_session)

    def raise_conversion_error(_attachment_id, force=False):  # noqa: ARG001
        raise RuntimeError("forced conversion failure")

    monkeypatch.setattr(
        AttachmentService,
        "generate_preview_pdf_artifact",
        staticmethod(raise_conversion_error),
    )

    processed = conversion_jobs.process_pending_jobs_once(batch_size=1)
    db.refresh(job)

    assert processed == 1
    assert job.status == conversion_jobs.JOB_STATUS_PENDING
    assert job.started_at is None
    assert job.next_run_at is not None
    assert "forced conversion failure" in (job.last_error or "")


def test_conversion_dead_letter_entries_are_listed_and_requeueable(db, test_user):
    job = _create_job(
        db,
        test_user=test_user,
        status=conversion_jobs.JOB_STATUS_FAILED,
        attempts=3,
        max_attempts=3,
    )
    job.last_error = "[DLQ:attempt_limit_reached(3/3)] failed permanently"
    db.commit()

    failed_jobs = conversion_jobs.list_dead_letter_conversion_jobs(db=db, limit=10)
    assert len(failed_jobs) == 1
    assert failed_jobs[0].id == job.id

    requeued = conversion_jobs.requeue_dead_letter_conversion_job(
        job.id,
        db=db,
        force=True,
        reset_attempts=True,
    )
    assert requeued is True
    db.refresh(job)
    assert job.status == conversion_jobs.JOB_STATUS_PENDING
    assert job.last_error is None
    assert job.attempts == 0
    assert job.force is True
