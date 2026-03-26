"""Process manager for durable preview-conversion job execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Optional

from app.models import AttachmentConversionJob


@dataclass(frozen=True, slots=True)
class ConversionWorkflowTrace:
    """Execution and compensation trace for one conversion run."""

    step_order: tuple[str, ...]
    compensation_order: tuple[str, ...]
    failed_step: Optional[str]
    final_status: str
    error: Optional[str]


PreviewGenerator = Callable[[int], None]
PreviewStatusLoader = Callable[[int], tuple[Optional[str], Optional[str]]]


class PreviewConversionProcessManager:
    """Executes conversion job stage flow with deterministic compensation states."""

    def __init__(
        self,
        *,
        preview_generator: PreviewGenerator,
        preview_status_loader: PreviewStatusLoader,
        status_ready: str,
        status_failed: str,
        job_status_pending: str,
        job_status_completed: str,
        job_status_failed: str,
    ) -> None:
        self.preview_generator = preview_generator
        self.preview_status_loader = preview_status_loader
        self.status_ready = status_ready
        self.status_failed = status_failed
        self.job_status_pending = job_status_pending
        self.job_status_completed = job_status_completed
        self.job_status_failed = job_status_failed
        self._last_trace: ConversionWorkflowTrace | None = None

    @property
    def last_trace(self) -> ConversionWorkflowTrace | None:
        return self._last_trace

    def execute(
        self,
        job: AttachmentConversionJob,
        *,
        retry_delay_seconds: int,
        fallback_probe_delay_seconds: int,
        status_failure_retry_delay_seconds: int | None = None,
    ) -> ConversionWorkflowTrace:
        step_order: list[str] = []
        compensation_order: list[str] = []
        failed_step: str | None = None

        try:
            step_order.append("generate_preview_artifact")
            self.preview_generator(job.attachment_id)

            step_order.append("load_preview_status")
            preview_status, preview_error = self.preview_status_loader(job.attachment_id)

            if preview_status == self.status_ready:
                step_order.append("mark_completed")
                job.status = self.job_status_completed
                job.last_error = None
                job.force = False
                job.finished_at = datetime.utcnow()
                job.next_run_at = None
            elif preview_status == self.status_failed:
                step_order.append("handle_preview_failure")
                job.last_error = preview_error or "Preview conversion failed"
                self._schedule_retry_or_fail(
                    job,
                    retry_delay_seconds=(
                        status_failure_retry_delay_seconds
                        if status_failure_retry_delay_seconds is not None
                        else retry_delay_seconds
                    ),
                    compensation_order=compensation_order,
                )
            else:
                step_order.append("schedule_status_probe")
                job.status = self.job_status_pending
                job.started_at = None
                job.finished_at = None
                job.next_run_at = datetime.utcnow() + timedelta(
                    seconds=fallback_probe_delay_seconds
                )
                compensation_order.append("reset_processing_lease")

            trace = ConversionWorkflowTrace(
                step_order=tuple(step_order),
                compensation_order=tuple(compensation_order),
                failed_step=None,
                final_status=job.status,
                error=None,
            )
            self._last_trace = trace
            return trace
        except Exception as exc:  # policy: COMPENSATING — workflow records and propagates conversion-step failure
            failed_step = step_order[-1] if step_order else "initialize"
            self._schedule_retry_or_fail(
                job,
                retry_delay_seconds=retry_delay_seconds,
                compensation_order=compensation_order,
                override_error=str(exc),
            )
            trace = ConversionWorkflowTrace(
                step_order=tuple(step_order),
                compensation_order=tuple(compensation_order),
                failed_step=failed_step,
                final_status=job.status,
                error=str(exc),
            )
            self._last_trace = trace
            return trace

    def _schedule_retry_or_fail(
        self,
        job: AttachmentConversionJob,
        *,
        retry_delay_seconds: int,
        compensation_order: list[str],
        override_error: str | None = None,
    ) -> None:
        if override_error:
            job.last_error = override_error
        if int(job.attempts or 0) >= int(job.max_attempts or 3):
            job.status = self.job_status_failed
            job.finished_at = datetime.utcnow()
            job.next_run_at = None
            compensation_order.append("mark_failed_terminal")
            return

        job.status = self.job_status_pending
        job.started_at = None
        job.finished_at = None
        job.next_run_at = datetime.utcnow() + timedelta(seconds=max(0, retry_delay_seconds))
        compensation_order.append("reset_processing_lease")
