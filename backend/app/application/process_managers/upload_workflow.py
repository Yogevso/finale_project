"""Process manager for document upload + release-notes orchestration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

from fastapi import BackgroundTasks, UploadFile
from sqlalchemy.orm import Session

from app.models import User
from app.schemas import DocumentCreate
from app.services.document_service import DocumentService


@dataclass(frozen=True, slots=True)
class UploadWorkflowTrace:
    """Execution and compensation trace for one upload workflow run."""

    step_order: tuple[str, ...]
    compensation_order: tuple[str, ...]
    failed_step: Optional[str]
    created_document_ids: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class UploadWorkflowResult:
    """Upload workflow output payload."""

    document: Any
    trace: UploadWorkflowTrace


AttachmentUploader = Callable[..., Awaitable[Any]]


class DocumentUploadProcessManager:
    """Orchestrates parent upload + optional content/release-notes lifecycle."""

    def __init__(
        self,
        *,
        db: Session,
        document_service: DocumentService,
        attachment_uploader: AttachmentUploader,
        logger: logging.Logger | None = None,
    ) -> None:
        self.db = db
        self.document_service = document_service
        self.attachment_uploader = attachment_uploader
        self.logger = logger or logging.getLogger(__name__)
        self._last_trace: UploadWorkflowTrace | None = None

    @property
    def last_trace(self) -> UploadWorkflowTrace | None:
        return self._last_trace

    async def execute(
        self,
        *,
        parent_document_data: DocumentCreate,
        current_user: User,
        background_tasks: BackgroundTasks,
        primary_file: UploadFile,
        content_file: UploadFile | None = None,
        release_notes_file: UploadFile | None = None,
        release_notes_document_data: DocumentCreate | None = None,
    ) -> UploadWorkflowResult:
        step_order: list[str] = []
        compensation_order: list[str] = []
        created_document_ids: list[int] = []
        failed_step: str | None = None

        try:
            step_order.append("create_parent_document")
            document = self.document_service.create_document(parent_document_data, current_user)
            created_document_ids.append(document.id)

            step_order.append("attach_primary_file")
            await self.attachment_uploader(
                self.db,
                document.id,
                primary_file,
                current_user,
                background_tasks=background_tasks,
            )

            if content_file is not None:
                step_order.append("attach_content_file")
                await self.attachment_uploader(
                    self.db,
                    document.id,
                    content_file,
                    current_user,
                    background_tasks=background_tasks,
                )

            if release_notes_file is not None:
                if release_notes_document_data is None:
                    raise ValueError(
                        "release_notes_document_data is required when release_notes_file is provided"
                    )
                release_payload = release_notes_document_data
                if release_payload.parent_id is None:
                    release_payload = release_payload.model_copy(
                        update={"parent_id": document.id}
                    )

                step_order.append("create_release_notes_document")
                release_doc = self.document_service.create_document(
                    release_payload,
                    current_user,
                )
                created_document_ids.append(release_doc.id)

                step_order.append("attach_release_notes_file")
                await self.attachment_uploader(
                    self.db,
                    release_doc.id,
                    release_notes_file,
                    current_user,
                    background_tasks=background_tasks,
                )

            trace = UploadWorkflowTrace(
                step_order=tuple(step_order),
                compensation_order=tuple(compensation_order),
                failed_step=None,
                created_document_ids=tuple(created_document_ids),
            )
            self._last_trace = trace
            return UploadWorkflowResult(document=document, trace=trace)
        except Exception:
            failed_step = step_order[-1] if step_order else "initialize"
            for created_document_id in reversed(created_document_ids):
                try:
                    self.document_service.delete_document(created_document_id, current_user)
                    compensation_order.append(f"delete_document:{created_document_id}")
                except Exception as cleanup_error:  # pragma: no cover - defensive logging path
                    self.db.rollback()
                    self.logger.warning(
                        "Failed upload rollback cleanup for document_id=%s: %s",
                        created_document_id,
                        cleanup_error,
                    )

            trace = UploadWorkflowTrace(
                step_order=tuple(step_order),
                compensation_order=tuple(compensation_order),
                failed_step=failed_step,
                created_document_ids=tuple(created_document_ids),
            )
            self._last_trace = trace
            raise
