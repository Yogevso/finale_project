"""Background reconciliation for orphaned document-company assignments."""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import DefaultDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.jobs import AsyncJobBatchReport, run_polling_worker
from app.models import (
    ActionType,
    AudienceEventType,
    AuditLog,
    Document,
    DocumentVisibility,
    Tenant,
    document_company_assignments,
)

logger = logging.getLogger(__name__)

ASSIGNMENT_RECONCILER_WORKER_NAME = "assignment_reconciler"


def _load_orphaned_assignment_rows(*, db: Session, batch_size: int) -> list[tuple[int, int]]:
    stmt = (
        select(
            document_company_assignments.c.document_id,
            document_company_assignments.c.tenant_id,
        )
        .select_from(
            document_company_assignments.join(
                Tenant,
                Tenant.id == document_company_assignments.c.tenant_id,
            )
        )
        .where(Tenant.is_active.is_(False))
        .order_by(
            document_company_assignments.c.document_id.asc(),
            document_company_assignments.c.tenant_id.asc(),
        )
        .limit(max(1, int(batch_size)))
    )
    return [(int(row.document_id), int(row.tenant_id)) for row in db.execute(stmt).all()]


def process_assignment_reconciliation_batch(
    *,
    batch_size: int = 100,
    db: Session | None = None,
) -> AsyncJobBatchReport:
    """Remove inactive-company assignments from documents in one batch."""
    owns_session = db is None
    session = db or SessionLocal()
    report = AsyncJobBatchReport(worker_name=ASSIGNMENT_RECONCILER_WORKER_NAME)

    try:
        orphaned_rows = _load_orphaned_assignment_rows(
            db=session,
            batch_size=batch_size,
        )
        if not orphaned_rows:
            return report

        by_document: DefaultDict[int, set[int]] = defaultdict(set)
        for document_id, tenant_id in orphaned_rows:
            by_document[document_id].add(tenant_id)

        changed = False
        for document_id, stale_company_ids in by_document.items():
            report.attempted += 1
            document = session.query(Document).filter(Document.id == document_id).first()
            if not document:
                report.skipped += 1
                continue

            old_company_ids = sorted(company.id for company in (document.assigned_companies or []))
            new_companies = [
                company for company in (document.assigned_companies or [])
                if company.id not in stale_company_ids
            ]
            new_company_ids = sorted(company.id for company in new_companies)
            removed_company_ids = [company_id for company_id in old_company_ids if company_id not in new_company_ids]
            if not removed_company_ids:
                report.skipped += 1
                continue

            changed = True
            visibility_downgraded_to_internal = False
            document.assigned_companies = new_companies
            document.audience_version = (document.audience_version or 1) + 1
            if document.visibility == DocumentVisibility.COMPANY and not new_company_ids:
                document.visibility = DocumentVisibility.INTERNAL
                visibility_downgraded_to_internal = True

            session.add(
                AuditLog(
                    user_id=None,
                    document_id=document.id,
                    action=ActionType.UPDATE,
                    audience_event_type=AudienceEventType.ASSIGNMENT_REMOVED,
                    details=json.dumps(
                        {
                            "event": "assignment_reconciler_cleanup",
                            "removed_inactive_company_ids": removed_company_ids,
                            "remaining_company_ids": new_company_ids,
                            "visibility_downgraded_to_internal": visibility_downgraded_to_internal,
                        },
                        sort_keys=True,
                    ),
                    assignment_diff=json.dumps(
                        {
                            "old_company_ids": old_company_ids,
                            "new_company_ids": new_company_ids,
                            "added_company_ids": [],
                            "removed_company_ids": removed_company_ids,
                        },
                        sort_keys=True,
                    ),
                )
            )
            report.completed += 1
            report.recovered += len(removed_company_ids)

        if changed:
            session.commit()
        else:
            session.rollback()

        return report
    except Exception:
        session.rollback()
        raise
    finally:
        if owns_session:
            session.close()


def run_assignment_reconciler_worker(
    *,
    poll_interval_seconds: float = 60.0,
    batch_size: int = 100,
    once: bool = False,
) -> None:
    """Run polling worker for assignment reconciliation."""
    run_polling_worker(
        worker_name=ASSIGNMENT_RECONCILER_WORKER_NAME,
        logger=logger,
        poll_interval_seconds=poll_interval_seconds,
        batch_size=batch_size,
        once=once,
        process_batch=lambda size: process_assignment_reconciliation_batch(batch_size=size),
    )
