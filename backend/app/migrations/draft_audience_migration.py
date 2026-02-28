"""Wave P remediation helper for invalid draft audience state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Sequence

from sqlalchemy.orm import Session, selectinload

from app.models import ActionType, AuditLog, Document, DocumentStatus, DocumentVisibility, Tenant


class DraftAudienceMigrationStrategy(str, Enum):
    """Available remediation strategies for invalid draft audience rows."""

    AUTO = "auto"
    ASSIGN_OWNER = "assign_owner"
    DEMOTE_INTERNAL = "demote_internal"


class DraftAudienceMigrationActionKind(str, Enum):
    """Concrete action the migration will take for a candidate row."""

    ASSIGN_OWNER = "assign_owner"
    DEMOTE_INTERNAL = "demote_internal"
    SKIP = "skip"


@dataclass(frozen=True, slots=True)
class DraftAudienceMigrationAction:
    """Planned remediation action for one document."""

    document_id: int
    document_number: str
    title: str
    action: DraftAudienceMigrationActionKind
    reason: str
    target_tenant_id: int | None = None


@dataclass(frozen=True, slots=True)
class DraftAudienceMigrationReport:
    """Summary of one dry-run/apply execution."""

    mode: str
    strategy: DraftAudienceMigrationStrategy
    generated_at: str
    total_candidates: int
    applied_count: int
    unresolved_count: int
    audit_entries_created: int
    planned_actions: list[DraftAudienceMigrationAction]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_candidate_documents(db: Session, *, limit: int | None = None) -> list[Document]:
    query = (
        db.query(Document)
        .options(selectinload(Document.assigned_companies))
        .filter(
            Document.status == DocumentStatus.DRAFT,
            Document.visibility == DocumentVisibility.COMPANY,
            ~Document.assigned_companies.any(),
        )
        .order_by(Document.id.asc())
    )
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def _load_active_owner_tenants(db: Session, documents: Sequence[Document]) -> dict[int, Tenant]:
    tenant_ids = sorted({document.tenant_id for document in documents if document.tenant_id is not None})
    if not tenant_ids:
        return {}

    owners = (
        db.query(Tenant)
        .filter(Tenant.id.in_(tenant_ids), Tenant.is_active.is_(True))
        .all()
    )
    return {tenant.id: tenant for tenant in owners}


def _build_planned_action(
    document: Document,
    *,
    strategy: DraftAudienceMigrationStrategy,
    active_owner_tenants: dict[int, Tenant],
) -> DraftAudienceMigrationAction:
    owner_tenant_id = document.tenant_id
    owner_tenant = (
        active_owner_tenants.get(owner_tenant_id) if owner_tenant_id is not None else None
    )

    if strategy == DraftAudienceMigrationStrategy.DEMOTE_INTERNAL:
        return DraftAudienceMigrationAction(
            document_id=document.id,
            document_number=document.document_number,
            title=document.title,
            action=DraftAudienceMigrationActionKind.DEMOTE_INTERNAL,
            reason="Configured demotion strategy",
        )

    if strategy == DraftAudienceMigrationStrategy.ASSIGN_OWNER:
        if owner_tenant is None:
            return DraftAudienceMigrationAction(
                document_id=document.id,
                document_number=document.document_number,
                title=document.title,
                action=DraftAudienceMigrationActionKind.SKIP,
                reason="Document has no active owner tenant",
            )
        return DraftAudienceMigrationAction(
            document_id=document.id,
            document_number=document.document_number,
            title=document.title,
            action=DraftAudienceMigrationActionKind.ASSIGN_OWNER,
            reason="Configured owner-assignment strategy",
            target_tenant_id=owner_tenant.id,
        )

    if owner_tenant is not None:
        return DraftAudienceMigrationAction(
            document_id=document.id,
            document_number=document.document_number,
            title=document.title,
            action=DraftAudienceMigrationActionKind.ASSIGN_OWNER,
            reason="Auto strategy assigned active owner tenant",
            target_tenant_id=owner_tenant.id,
        )
    return DraftAudienceMigrationAction(
        document_id=document.id,
        document_number=document.document_number,
        title=document.title,
        action=DraftAudienceMigrationActionKind.DEMOTE_INTERNAL,
        reason="Auto strategy demoted visibility because no active owner tenant exists",
    )


def _build_audit_details(
    action: DraftAudienceMigrationAction,
    *,
    strategy: DraftAudienceMigrationStrategy,
) -> str:
    if action.action == DraftAudienceMigrationActionKind.ASSIGN_OWNER:
        return (
            "Wave P draft audience migration: assigned owner tenant "
            f"{action.target_tenant_id} to draft company-visible document "
            f"{action.document_number} (strategy={strategy.value})"
        )
    if action.action == DraftAudienceMigrationActionKind.DEMOTE_INTERNAL:
        return (
            "Wave P draft audience migration: changed draft document "
            f"{action.document_number} visibility from company to internal "
            f"(strategy={strategy.value})"
        )
    return (
        "Wave P draft audience migration: skipped document "
        f"{action.document_number} (reason={action.reason})"
    )


def run_draft_audience_migration(
    db: Session,
    *,
    strategy: DraftAudienceMigrationStrategy = DraftAudienceMigrationStrategy.AUTO,
    apply_changes: bool = False,
    actor_user_id: int | None = None,
    limit: int | None = None,
) -> DraftAudienceMigrationReport:
    """Plan or apply remediation for draft company-visible docs missing assignments."""
    candidates = _load_candidate_documents(db, limit=limit)
    active_owner_tenants = _load_active_owner_tenants(db, candidates)
    document_by_id = {document.id: document for document in candidates}

    planned_actions = [
        _build_planned_action(
            document,
            strategy=strategy,
            active_owner_tenants=active_owner_tenants,
        )
        for document in candidates
    ]

    applied_count = 0
    audit_entries_created = 0
    now = datetime.utcnow()

    if apply_changes:
        for action in planned_actions:
            if action.action == DraftAudienceMigrationActionKind.SKIP:
                continue

            document = document_by_id[action.document_id]
            if action.action == DraftAudienceMigrationActionKind.ASSIGN_OWNER:
                owner_tenant = active_owner_tenants[action.target_tenant_id or 0]
                document.assigned_companies = [owner_tenant]
            elif action.action == DraftAudienceMigrationActionKind.DEMOTE_INTERNAL:
                document.visibility = DocumentVisibility.INTERNAL
                document.assigned_companies = []

            document.updated_at = now
            db.add(
                AuditLog(
                    user_id=actor_user_id,
                    document_id=document.id,
                    action=ActionType.SYSTEM,
                    details=_build_audit_details(action, strategy=strategy),
                )
            )
            applied_count += 1
            audit_entries_created += 1

        db.commit()

    unresolved_count = sum(
        1 for action in planned_actions if action.action == DraftAudienceMigrationActionKind.SKIP
    )

    return DraftAudienceMigrationReport(
        mode="apply" if apply_changes else "dry-run",
        strategy=strategy,
        generated_at=_utc_now_iso(),
        total_candidates=len(candidates),
        applied_count=applied_count,
        unresolved_count=unresolved_count,
        audit_entries_created=audit_entries_created,
        planned_actions=planned_actions,
    )
