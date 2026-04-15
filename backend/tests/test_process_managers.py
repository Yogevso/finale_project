"""Tests for workflow process-manager orchestration and compensation traces."""

from __future__ import annotations

import io

import pytest
from fastapi import BackgroundTasks, HTTPException, UploadFile

from app.application.process_managers import (
    DocumentUploadProcessManager,
    PreviewConversionProcessManager,
)
from app.models import Document
from app.services.document_service import DocumentService
from tests.factories import build_attachment_conversion_job, build_document_create


def _docx_upload_file(name: str) -> UploadFile:
    return UploadFile(
        filename=name,
        file=io.BytesIO(b"PK\x03\x04minimal-docx-fixture"),
        headers={
            "content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        },
    )


@pytest.mark.anyio
async def test_upload_process_manager_compensates_parent_and_child_on_release_note_failure(
    db, test_user
):
    service = DocumentService(db)
    upload_calls = {"count": 0}

    async def fake_uploader(*args, **kwargs):
        upload_calls["count"] += 1
        if upload_calls["count"] == 2:
            raise HTTPException(status_code=500, detail="release note upload failed")
        return None

    manager = DocumentUploadProcessManager(
        db=db,
        document_service=service,
        attachment_uploader=fake_uploader,
    )

    parent_data = build_document_create(
        title="PM Parent Doc",
        description="parent",
    )
    release_data = build_document_create(
        title="PM Parent Doc Release Notes",
        description="child",
        category="Release Notes",
        tags="release-notes",
        parent_id=None,
    )

    with pytest.raises(HTTPException, match="release note upload failed"):
        await manager.execute(
            parent_document_data=parent_data,
            current_user=test_user,
            background_tasks=BackgroundTasks(),
            primary_file=_docx_upload_file("parent.docx"),
            release_notes_file=_docx_upload_file("release-notes.docx"),
            release_notes_document_data=release_data,
        )

    trace = manager.last_trace
    assert trace is not None
    assert trace.failed_step == "attach_release_notes_file"
    assert len(trace.compensation_order) == 2
    assert all(step.startswith("delete_document:") for step in trace.compensation_order)
    assert db.query(Document).filter(Document.title.like("PM Parent Doc%")).count() == 0


@pytest.mark.anyio
async def test_upload_process_manager_compensates_when_after_primary_attachment_fails(
    db, test_user
):
    service = DocumentService(db)

    async def fake_uploader(*args, **kwargs):
        return None

    async def fail_after_primary(_document):
        raise HTTPException(status_code=500, detail="generated working file failed")

    manager = DocumentUploadProcessManager(
        db=db,
        document_service=service,
        attachment_uploader=fake_uploader,
    )

    with pytest.raises(HTTPException, match="generated working file failed"):
        await manager.execute(
            parent_document_data=build_document_create(
                title="PM PDF Upload",
                description="parent",
            ),
            current_user=test_user,
            background_tasks=BackgroundTasks(),
            primary_file=_docx_upload_file("parent.docx"),
            after_primary_attachment=fail_after_primary,
            after_primary_attachment_step_name="attach_generated_pdf_working_file",
        )

    trace = manager.last_trace
    assert trace is not None
    assert trace.failed_step == "attach_generated_pdf_working_file"
    assert trace.compensation_order == (f"delete_document:{trace.created_document_ids[0]}",)
    assert db.query(Document).filter(Document.title == "PM PDF Upload").count() == 0


def test_conversion_process_manager_marks_completed_when_preview_ready():
    job = build_attachment_conversion_job(
        attachment_id=42,
        job_type="reader_html",
        status="processing",
        attempts=1,
        max_attempts=3,
        force=True,
    )
    called = {"count": 0}

    manager = PreviewConversionProcessManager(
        preview_generator=lambda attachment_id: called.__setitem__("count", attachment_id),
        preview_status_loader=lambda _attachment_id: ("ready", None),
        status_ready="ready",
        status_failed="failed",
        job_status_pending="pending",
        job_status_completed="completed",
        job_status_failed="failed",
    )
    trace = manager.execute(
        job,
        retry_delay_seconds=30,
        fallback_probe_delay_seconds=10,
    )

    assert called["count"] == 42
    assert trace.failed_step is None
    assert trace.final_status == "completed"
    assert "mark_completed" in trace.step_order
    assert job.status == "completed"
    assert job.force is False


def test_conversion_process_manager_retries_on_generation_exception():
    job = build_attachment_conversion_job(
        attachment_id=7,
        job_type="reader_html",
        status="processing",
        attempts=1,
        max_attempts=3,
        force=False,
    )

    manager = PreviewConversionProcessManager(
        preview_generator=lambda _attachment_id: (_ for _ in ()).throw(RuntimeError("boom")),
        preview_status_loader=lambda _attachment_id: ("pending", None),
        status_ready="ready",
        status_failed="failed",
        job_status_pending="pending",
        job_status_completed="completed",
        job_status_failed="failed",
    )
    trace = manager.execute(
        job,
        retry_delay_seconds=0,
        fallback_probe_delay_seconds=10,
    )

    assert trace.failed_step == "generate_preview_artifact"
    assert trace.error == "boom"
    assert trace.final_status == "pending"
    assert "reset_processing_lease" in trace.compensation_order
    assert job.status == "pending"
    assert job.next_run_at is not None


def test_conversion_process_manager_marks_failed_when_attempts_exhausted():
    job = build_attachment_conversion_job(
        attachment_id=8,
        job_type="reader_html",
        status="processing",
        attempts=3,
        max_attempts=3,
        force=False,
    )

    manager = PreviewConversionProcessManager(
        preview_generator=lambda _attachment_id: (_ for _ in ()).throw(RuntimeError("terminal")),
        preview_status_loader=lambda _attachment_id: ("pending", None),
        status_ready="ready",
        status_failed="failed",
        job_status_pending="pending",
        job_status_completed="completed",
        job_status_failed="failed",
    )
    trace = manager.execute(
        job,
        retry_delay_seconds=0,
        fallback_probe_delay_seconds=10,
    )

    assert trace.final_status == "failed"
    assert "mark_failed_terminal" in trace.compensation_order
    assert job.status == "failed"
    assert job.finished_at is not None
