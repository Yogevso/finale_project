"""Company Maintenance API - System Admin tasks for company lifecycle management."""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.permissions import require_system_admin
from app.models import (
    Document,
    DocumentStatus,
    DocumentVisibility,
    Invitation,
    InvitationStatus,
    Tenant,
    User,
    UserRole,
    document_company_assignments,
)

router = APIRouter(prefix="/companies/maintenance", tags=["Company Maintenance"])


def _parse_settings(tenant: Tenant) -> dict:
    """Parse tenant settings JSON safely."""
    if not tenant.settings:
        return {}
    try:
        parsed = json.loads(tenant.settings)
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _hierarchy_parent_id(tenant: Tenant) -> Optional[int]:
    """Read hierarchy parent company id from tenant settings."""
    settings = _parse_settings(tenant)
    hierarchy = settings.get("hierarchy")
    if not isinstance(hierarchy, dict):
        return None
    parent_id = hierarchy.get("parent_company_id")
    if isinstance(parent_id, int):
        return parent_id
    if isinstance(parent_id, str) and parent_id.isdigit():
        return int(parent_id)
    return None


def _set_hierarchy_parent_id(tenant: Tenant, parent_company_id: Optional[int]) -> None:
    """Write hierarchy parent company id into tenant settings."""
    settings = _parse_settings(tenant)
    hierarchy = settings.get("hierarchy")
    if not isinstance(hierarchy, dict):
        hierarchy = {}

    if parent_company_id is None:
        hierarchy.pop("parent_company_id", None)
    else:
        hierarchy["parent_company_id"] = parent_company_id

    if hierarchy:
        settings["hierarchy"] = hierarchy
    else:
        settings.pop("hierarchy", None)

    tenant.settings = json.dumps(settings, sort_keys=True)


def _would_create_hierarchy_cycle(
    db: Session,
    *,
    company_id: int,
    parent_company_id: int,
) -> bool:
    """Return True when assigning parent would introduce a cycle."""
    seen = set()
    current_id: Optional[int] = parent_company_id
    while current_id is not None:
        if current_id == company_id:
            return True
        if current_id in seen:
            # Existing malformed cycle in chain; do not allow further mutation.
            return True
        seen.add(current_id)
        current = db.query(Tenant).filter(Tenant.id == current_id).first()
        if current is None:
            return False
        current_id = _hierarchy_parent_id(current)
    return False


def _build_hierarchy_snapshot(db: Session, company: Tenant) -> dict:
    """Build hierarchy baseline snapshot for one company."""
    parent_company_id = _hierarchy_parent_id(company)
    parent = None
    if parent_company_id is not None:
        parent = db.query(Tenant).filter(Tenant.id == parent_company_id).first()

    all_companies = db.query(Tenant).all()
    children = [tenant for tenant in all_companies if _hierarchy_parent_id(tenant) == company.id]

    cycle_detected = False
    ancestry_chain = [company.id]
    seen = {company.id}
    current_parent_id = parent_company_id
    while current_parent_id is not None:
        if current_parent_id in seen:
            cycle_detected = True
            break
        seen.add(current_parent_id)
        ancestry_chain.append(current_parent_id)
        current = db.query(Tenant).filter(Tenant.id == current_parent_id).first()
        if current is None:
            break
        current_parent_id = _hierarchy_parent_id(current)

    return {
        "company_id": company.id,
        "company_name": company.name,
        "parent_company_id": parent_company_id,
        "parent_company_name": parent.name if parent else None,
        "children": [
            {
                "id": child.id,
                "name": child.name,
                "is_active": child.is_active,
            }
            for child in children
        ],
        "child_count": len(children),
        "depth": len(ancestry_chain) - 1,
        "ancestry_path": list(reversed(ancestry_chain)),
        "cycle_detected": cycle_detected,
    }


# ============================================================================
# Schemas
# ============================================================================


class OrphanUserInfo(BaseModel):
    """Information about an orphaned user."""

    id: int
    email: str
    username: str
    role: str
    tenant_id: Optional[int]
    tenant_name: Optional[str]
    tenant_active: Optional[bool]
    reason: str


class OrphanInvitationInfo(BaseModel):
    """Information about an orphaned invitation."""

    id: int
    email: str
    role: str
    tenant_id: Optional[int]
    tenant_name: Optional[str]
    tenant_active: Optional[bool]
    status: str
    reason: str


class OrphanDetectorResponse(BaseModel):
    """Response from orphan detector jobs."""

    orphan_count: int
    orphans: list


class CompanyTransferValidation(BaseModel):
    """Validation result for company ownership transfer."""

    can_transfer: bool
    source_company_id: int
    target_company_id: int
    users_to_transfer: int
    documents_to_reassign: int
    invitations_to_update: int
    warnings: list[str]
    blockers: list[str]


class CompanyArchiveValidation(BaseModel):
    """Validation result for company archive operation."""

    can_archive: bool
    company_id: int
    active_users: int
    pending_invitations: int
    owned_documents: int
    assigned_documents: int
    warnings: list[str]
    blockers: list[str]


class CompanyScopeConflict(BaseModel):
    """A scope conflict for a user."""

    user_id: int
    email: str
    role: str
    current_tenant_id: Optional[int]
    conflict_type: str
    description: str


class CompanyScopeConflictReport(BaseModel):
    """Report of all company scope conflicts."""

    conflict_count: int
    conflicts: list[CompanyScopeConflict]


class CompanyHierarchyParentUpdate(BaseModel):
    """Hierarchy parent update request."""

    parent_company_id: Optional[int] = None


# ============================================================================
# Task 165: Company Deactivate Impact Report
# ============================================================================


@router.get("/deactivate-impact/{company_id}")
async def get_company_deactivate_impact(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
):
    """Return impact preview for deactivating a company."""
    company = db.query(Tenant).filter(Tenant.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    active_users = (
        db.query(User)
        .filter(
            User.tenant_id == company_id,
            User.is_active.is_(True),
        )
        .count()
    )
    pending_invitations = (
        db.query(Invitation)
        .filter(
            Invitation.tenant_id == company_id,
            Invitation.status == InvitationStatus.PENDING,
        )
        .count()
    )
    owned_documents = db.query(Document).filter(Document.tenant_id == company_id).count()
    assigned_documents = (
        db.execute(
            select(func.count())
            .select_from(document_company_assignments)
            .where(document_company_assignments.c.tenant_id == company_id)
        ).scalar()
        or 0
    )
    active_customer_visible_docs = (
        db.query(Document)
        .filter(
            Document.status == DocumentStatus.ACTIVE,
            Document.visibility == DocumentVisibility.COMPANY,
            Document.assigned_companies.any(id=company_id),
        )
        .count()
    )

    warnings = []
    if active_users:
        warnings.append(f"{active_users} active users will lose access immediately.")
    if pending_invitations:
        warnings.append(f"{pending_invitations} pending invitations should be cancelled.")
    if active_customer_visible_docs:
        warnings.append(
            f"{active_customer_visible_docs} active customer-visible documents include this company."
        )

    return {
        "company_id": company.id,
        "company_name": company.name,
        "company_is_active": company.is_active,
        "impact": {
            "active_user_count": active_users,
            "pending_invitation_count": pending_invitations,
            "owned_document_count": owned_documents,
            "assigned_document_count": assigned_documents,
            "active_customer_visible_document_count": active_customer_visible_docs,
        },
        "warnings": warnings,
        "recommended_actions": [
            "Notify customer admins before deactivation",
            "Transfer document ownership if long-term access is required",
            "Cancel or reissue pending invitations",
        ],
    }


# ============================================================================
# Task 166: Company Merge Document Reassignment Plan
# ============================================================================


@router.get("/merge-plan/{source_company_id}/{target_company_id}")
async def company_merge_reassignment_plan(
    source_company_id: int,
    target_company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
):
    """Build a dry-run merge plan for document/user/invitation reassignment."""
    blockers: list[str] = []
    warnings: list[str] = []

    source = db.query(Tenant).filter(Tenant.id == source_company_id).first()
    target = db.query(Tenant).filter(Tenant.id == target_company_id).first()

    if not source:
        blockers.append(f"Source company (id={source_company_id}) does not exist")
    if not target:
        blockers.append(f"Target company (id={target_company_id}) does not exist")
    if source_company_id == target_company_id:
        blockers.append("Source and target companies must be different")

    if blockers:
        return {
            "can_merge": False,
            "source_company_id": source_company_id,
            "target_company_id": target_company_id,
            "blockers": blockers,
            "warnings": warnings,
            "plan": [],
        }

    if target and not target.is_active:
        blockers.append(f"Target company '{target.name}' is inactive")

    owned_documents = db.query(Document).filter(Document.tenant_id == source_company_id).all()
    owned_doc_ids = [doc.id for doc in owned_documents]

    source_assigned_doc_ids = (
        db.execute(
            select(document_company_assignments.c.document_id).where(
                document_company_assignments.c.tenant_id == source_company_id
            )
        )
        .scalars()
        .all()
    )
    target_assigned_doc_ids = set(
        db.execute(
            select(document_company_assignments.c.document_id).where(
                document_company_assignments.c.tenant_id == target_company_id
            )
        )
        .scalars()
        .all()
    )

    assignment_conflicts = sorted(
        set(source_assigned_doc_ids).intersection(target_assigned_doc_ids)
    )

    users_to_transfer = db.query(User).filter(User.tenant_id == source_company_id).count()
    invitations_to_transfer = (
        db.query(Invitation)
        .filter(
            Invitation.tenant_id == source_company_id,
            Invitation.status == InvitationStatus.PENDING,
        )
        .count()
    )

    if assignment_conflicts:
        warnings.append(
            f"{len(assignment_conflicts)} documents are already assigned to both companies."
        )

    if source and source.is_active:
        warnings.append(
            "Source company is active. Plan should include deactivation after reassignment."
        )

    plan_steps = [
        {
            "step": 1,
            "action": "reassign_owned_documents",
            "description": "Move source-owned documents to target company ownership",
            "count": len(owned_doc_ids),
            "document_ids_preview": owned_doc_ids[:20],
        },
        {
            "step": 2,
            "action": "migrate_company_assignments",
            "description": "Repoint source company assignments to target company",
            "count": len(source_assigned_doc_ids),
            "already_assigned_conflicts": assignment_conflicts[:20],
        },
        {
            "step": 3,
            "action": "transfer_users",
            "description": "Move users from source company to target company",
            "count": users_to_transfer,
        },
        {
            "step": 4,
            "action": "transfer_pending_invitations",
            "description": "Update pending invitations to target company",
            "count": invitations_to_transfer,
        },
        {
            "step": 5,
            "action": "deactivate_source_company",
            "description": "Deactivate source company after successful reassignment",
            "count": 1,
        },
    ]

    return {
        "can_merge": len(blockers) == 0,
        "source_company_id": source_company_id,
        "source_company_name": source.name if source else None,
        "target_company_id": target_company_id,
        "target_company_name": target.name if target else None,
        "blockers": blockers,
        "warnings": warnings,
        "impact_summary": {
            "owned_documents": len(owned_doc_ids),
            "assigned_documents": len(source_assigned_doc_ids),
            "assignment_conflicts": len(assignment_conflicts),
            "users_to_transfer": users_to_transfer,
            "pending_invitations_to_transfer": invitations_to_transfer,
        },
        "plan": plan_steps,
    }


# ============================================================================
# Task 167: Company Rename Propagation Checks
# ============================================================================


@router.get("/rename-propagation/{company_id}")
async def company_rename_propagation_checks(
    company_id: int,
    new_name: Optional[str] = None,
    new_slug: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
):
    """Check where company rename changes propagate and detect blockers."""
    company = db.query(Tenant).filter(Tenant.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    blockers = []
    warnings = []

    if new_slug and new_slug != company.slug:
        slug_conflict = (
            db.query(Tenant).filter(Tenant.slug == new_slug, Tenant.id != company_id).first()
        )
        if slug_conflict:
            blockers.append(f"Slug '{new_slug}' is already used by company id={slug_conflict.id}")

    if not new_name and not new_slug:
        warnings.append("No new name/slug provided; returning current propagation inventory only.")

    linked_users = db.query(User).filter(User.tenant_id == company_id).count()
    linked_invitations = db.query(Invitation).filter(Invitation.tenant_id == company_id).count()
    owned_documents = db.query(Document).filter(Document.tenant_id == company_id).count()
    assigned_documents = (
        db.execute(
            select(func.count())
            .select_from(document_company_assignments)
            .where(document_company_assignments.c.tenant_id == company_id)
        ).scalar()
        or 0
    )

    return {
        "can_rename": len(blockers) == 0,
        "company_id": company_id,
        "current_name": company.name,
        "current_slug": company.slug,
        "proposed_name": new_name or company.name,
        "proposed_slug": new_slug or company.slug,
        "blockers": blockers,
        "warnings": warnings,
        "propagation_targets": {
            "tenant_row": True,
            "linked_users": linked_users,
            "linked_invitations": linked_invitations,
            "owned_documents": owned_documents,
            "assigned_documents": assigned_documents,
            "public_api_slugs": 1,
        },
    }


# ============================================================================
# Task 168: Company Deletion Hard Safety Checks
# ============================================================================


@router.get("/deletion-safety/{company_id}")
async def company_deletion_hard_safety_checks(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
):
    """Check hard-delete safety and return exact blockers."""
    company = db.query(Tenant).filter(Tenant.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    total_users = db.query(User).filter(User.tenant_id == company_id).count()
    total_invitations = db.query(Invitation).filter(Invitation.tenant_id == company_id).count()
    pending_invitations = (
        db.query(Invitation)
        .filter(
            Invitation.tenant_id == company_id,
            Invitation.status == InvitationStatus.PENDING,
        )
        .count()
    )
    owned_documents = db.query(Document).filter(Document.tenant_id == company_id).count()
    assigned_documents = (
        db.execute(
            select(func.count())
            .select_from(document_company_assignments)
            .where(document_company_assignments.c.tenant_id == company_id)
        ).scalar()
        or 0
    )

    blockers = []
    if total_users > 0:
        blockers.append(f"Company still has {total_users} linked users")
    if total_invitations > 0:
        blockers.append(f"Company still has {total_invitations} invitation records")
    if owned_documents > 0:
        blockers.append(f"Company still owns {owned_documents} documents")
    if assigned_documents > 0:
        blockers.append(f"Company is assigned to {assigned_documents} documents")

    warnings = []
    if company.is_active:
        warnings.append("Company is active; perform deactivation before hard delete.")
    if pending_invitations > 0:
        warnings.append("Pending invitations should be cancelled before deletion.")

    return {
        "company_id": company.id,
        "company_name": company.name,
        "can_hard_delete": len(blockers) == 0,
        "blockers": blockers,
        "warnings": warnings,
        "counts": {
            "users": total_users,
            "invitations_total": total_invitations,
            "invitations_pending": pending_invitations,
            "owned_documents": owned_documents,
            "assigned_documents": assigned_documents,
        },
    }


# ============================================================================
# Task 172: Company Hierarchy Support Baseline
# ============================================================================


@router.get("/hierarchy/{company_id}")
async def get_company_hierarchy_baseline(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
):
    """Return baseline hierarchy metadata for a company."""
    company = db.query(Tenant).filter(Tenant.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return _build_hierarchy_snapshot(db, company)


@router.put("/hierarchy/{company_id}/parent")
async def set_company_hierarchy_parent(
    company_id: int,
    data: CompanyHierarchyParentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
):
    """Set or clear parent company relationship in hierarchy baseline metadata."""
    company = db.query(Tenant).filter(Tenant.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    parent_company_id = data.parent_company_id

    if parent_company_id is not None:
        if parent_company_id == company_id:
            raise HTTPException(status_code=400, detail="Company cannot be parent of itself")

        parent = db.query(Tenant).filter(Tenant.id == parent_company_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent company not found")
        if not parent.is_active:
            raise HTTPException(status_code=400, detail="Parent company must be active")

        if _would_create_hierarchy_cycle(
            db,
            company_id=company_id,
            parent_company_id=parent_company_id,
        ):
            raise HTTPException(status_code=400, detail="Hierarchy cycle detected")

    _set_hierarchy_parent_id(company, parent_company_id)
    db.commit()
    db.refresh(company)

    return _build_hierarchy_snapshot(db, company)


# ============================================================================
# Task 169: Orphan Customer Detector Job
# ============================================================================


@router.get("/orphan-customers", response_model=OrphanDetectorResponse)
async def detect_orphan_customers(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
):
    """
    Detect customer users with invalid company assignments.

    Orphan conditions:
    - Customer without tenant_id (null company)
    - Customer with tenant_id pointing to non-existent company
    - Customer with tenant_id pointing to inactive company
    """
    orphans: list[OrphanUserInfo] = []

    # Find all customer users
    customers = db.query(User).filter(User.role == UserRole.CUSTOMER).all()

    for customer in customers:
        reason = None
        tenant_name = None
        tenant_active = None

        if customer.tenant_id is None:
            reason = "Customer has no company assigned (null tenant_id)"
        else:
            tenant = db.query(Tenant).filter(Tenant.id == customer.tenant_id).first()
            if not tenant:
                reason = f"Customer's company (id={customer.tenant_id}) no longer exists"
            else:
                tenant_name = tenant.name
                tenant_active = tenant.is_active
                if not tenant.is_active:
                    reason = f"Customer's company '{tenant.name}' is deactivated"

        if reason:
            orphans.append(
                OrphanUserInfo(
                    id=customer.id,
                    email=customer.email,
                    username=customer.username,
                    role=customer.role.value,
                    tenant_id=customer.tenant_id,
                    tenant_name=tenant_name,
                    tenant_active=tenant_active,
                    reason=reason,
                )
            )

    return OrphanDetectorResponse(
        orphan_count=len(orphans),
        orphans=[o.model_dump() for o in orphans],
    )


# ============================================================================
# Task 170: Orphan Invitation Detector Job
# ============================================================================


@router.get("/orphan-invitations", response_model=OrphanDetectorResponse)
async def detect_orphan_invitations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
):
    """
    Detect pending invitations with invalid company assignments.

    Orphan conditions:
    - Customer invitation without tenant_id
    - Invitation with tenant_id pointing to non-existent company
    - Pending invitation for inactive company
    """
    orphans: list[OrphanInvitationInfo] = []

    # Focus on pending invitations (active problems)
    pending_invitations = (
        db.query(Invitation).filter(Invitation.status == InvitationStatus.PENDING).all()
    )

    for invitation in pending_invitations:
        reason = None
        tenant_name = None
        tenant_active = None

        # Customer invitations must have a company
        if invitation.role == UserRole.CUSTOMER and invitation.tenant_id is None:
            reason = "Customer invitation has no company assigned"
        elif invitation.tenant_id is not None:
            tenant = db.query(Tenant).filter(Tenant.id == invitation.tenant_id).first()
            if not tenant:
                reason = f"Invitation's company (id={invitation.tenant_id}) no longer exists"
            else:
                tenant_name = tenant.name
                tenant_active = tenant.is_active
                if not tenant.is_active:
                    reason = f"Invitation's company '{tenant.name}' is deactivated"

        if reason:
            orphans.append(
                OrphanInvitationInfo(
                    id=invitation.id,
                    email=invitation.email,
                    role=invitation.role.value if invitation.role else "unknown",
                    tenant_id=invitation.tenant_id,
                    tenant_name=tenant_name,
                    tenant_active=tenant_active,
                    status=invitation.status.value,
                    reason=reason,
                )
            )

    return OrphanDetectorResponse(
        orphan_count=len(orphans),
        orphans=[o.model_dump() for o in orphans],
    )


# ============================================================================
# Task 171: Company Ownership Transfer Validation
# ============================================================================


@router.get("/transfer-validation/{source_company_id}/{target_company_id}")
async def validate_company_transfer(
    source_company_id: int,
    target_company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
) -> CompanyTransferValidation:
    """
    Validate a company ownership transfer operation.

    Checks what would happen when transferring users and documents
    from source company to target company.
    """
    warnings: list[str] = []
    blockers: list[str] = []

    # Validate companies exist
    source = db.query(Tenant).filter(Tenant.id == source_company_id).first()
    target = db.query(Tenant).filter(Tenant.id == target_company_id).first()

    if not source:
        blockers.append(f"Source company (id={source_company_id}) does not exist")
    if not target:
        blockers.append(f"Target company (id={target_company_id}) does not exist")

    if blockers:
        return CompanyTransferValidation(
            can_transfer=False,
            source_company_id=source_company_id,
            target_company_id=target_company_id,
            users_to_transfer=0,
            documents_to_reassign=0,
            invitations_to_update=0,
            warnings=warnings,
            blockers=blockers,
        )

    if not target.is_active:
        blockers.append(f"Target company '{target.name}' is deactivated")

    if source_company_id == target_company_id:
        blockers.append("Source and target companies are the same")

    # Count affected entities
    users_count = db.query(User).filter(User.tenant_id == source_company_id).count()

    # Count documents owned by source company
    documents_count = db.query(Document).filter(Document.tenant_id == source_company_id).count()

    # Count pending invitations
    invitations_count = (
        db.query(Invitation)
        .filter(
            Invitation.tenant_id == source_company_id,
            Invitation.status == InvitationStatus.PENDING,
        )
        .count()
    )

    # Warnings
    if users_count > 0:
        warnings.append(f"{users_count} users will be moved to '{target.name}'")
    if documents_count > 0:
        warnings.append(f"{documents_count} documents will be reassigned")
    if invitations_count > 0:
        warnings.append(f"{invitations_count} pending invitations will be updated")
    if source.is_active:
        warnings.append(
            f"Source company '{source.name}' is still active - consider deactivating first"
        )

    return CompanyTransferValidation(
        can_transfer=len(blockers) == 0,
        source_company_id=source_company_id,
        target_company_id=target_company_id,
        users_to_transfer=users_count,
        documents_to_reassign=documents_count,
        invitations_to_update=invitations_count,
        warnings=warnings,
        blockers=blockers,
    )


# ============================================================================
# Task 173: Company Archive and Restore Rules
# ============================================================================


@router.get("/archive-validation/{company_id}")
async def validate_company_archive(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
) -> CompanyArchiveValidation:
    """
    Validate whether a company can be safely archived.

    Returns information about what would be affected by archiving.
    """
    warnings: list[str] = []
    blockers: list[str] = []

    company = db.query(Tenant).filter(Tenant.id == company_id).first()
    if not company:
        return CompanyArchiveValidation(
            can_archive=False,
            company_id=company_id,
            active_users=0,
            pending_invitations=0,
            owned_documents=0,
            assigned_documents=0,
            warnings=[],
            blockers=[f"Company (id={company_id}) does not exist"],
        )

    if not company.is_active:
        warnings.append("Company is already deactivated")

    # Count active users
    active_users = (
        db.query(User)
        .filter(
            User.tenant_id == company_id,
            User.is_active.is_(True),
        )
        .count()
    )

    # Count pending invitations
    pending_invitations = (
        db.query(Invitation)
        .filter(
            Invitation.tenant_id == company_id,
            Invitation.status == InvitationStatus.PENDING,
        )
        .count()
    )

    # Count owned documents
    owned_documents = db.query(Document).filter(Document.tenant_id == company_id).count()

    # Count assigned documents (via the association table)
    assigned_documents = (
        db.execute(
            select(func.count())
            .select_from(document_company_assignments)
            .where(document_company_assignments.c.tenant_id == company_id)
        ).scalar()
        or 0
    )

    # Generate warnings/blockers based on counts
    if active_users > 0:
        warnings.append(f"{active_users} active users will lose access")

    if pending_invitations > 0:
        warnings.append(f"{pending_invitations} pending invitations will be cancelled")

    if owned_documents > 0:
        blockers.append(
            f"{owned_documents} documents are owned by this company - transfer ownership first"
        )

    if assigned_documents > 0:
        warnings.append(f"{assigned_documents} document assignments will be affected")

    return CompanyArchiveValidation(
        can_archive=len(blockers) == 0,
        company_id=company_id,
        active_users=active_users,
        pending_invitations=pending_invitations,
        owned_documents=owned_documents,
        assigned_documents=assigned_documents,
        warnings=warnings,
        blockers=blockers,
    )


# ============================================================================
# Task 174: Multi-Company User Policy Definition
# ============================================================================


@router.get("/multi-company-policy")
async def get_multi_company_policy(
    current_user: User = Depends(require_system_admin),
):
    """
    Get the current multi-company user policy definition.

    This defines the rules for users that could belong to multiple companies.
    Currently, the system enforces single-company binding for customers.
    """
    return {
        "policy_version": "1.0",
        "rules": {
            "customer_single_company": {
                "description": "Customer users can only belong to one company at a time",
                "enforced": True,
                "enforcement_point": "user_update, invitation_accept",
            },
            "admin_cross_company_access": {
                "description": "System admins can manage users across all companies",
                "enforced": True,
                "enforcement_point": "tenant_context",
            },
            "company_scope_isolation": {
                "description": "Regular admins can only manage users within their own company",
                "enforced": True,
                "enforcement_point": "tenant_context",
            },
        },
        "future_considerations": [
            "Multi-tenant user assignments for enterprise scenarios",
            "Company group hierarchies",
            "Cross-company document sharing policies",
        ],
    }


# ============================================================================
# Task 175: Company-Scoped Onboarding Validation
# ============================================================================


@router.get("/onboarding-validation/{company_id}")
async def validate_company_onboarding(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
):
    """
    Validate company onboarding requirements.

    Checks that a company meets minimum requirements for active use.
    """
    company = db.query(Tenant).filter(Tenant.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    requirements: list[dict] = []

    # Requirement 1: Company must be active
    requirements.append(
        {
            "requirement": "Company is active",
            "met": company.is_active,
            "severity": "blocker",
        }
    )

    # Requirement 2: Has at least one admin or manager user
    admin_count = (
        db.query(User)
        .filter(
            User.tenant_id == company_id,
            User.role.in_([UserRole.ADMIN, UserRole.MANAGER, UserRole.SYSTEM_ADMIN]),
            User.is_active.is_(True),
        )
        .count()
    )
    requirements.append(
        {
            "requirement": "Has at least one admin or manager",
            "met": admin_count > 0,
            "severity": "blocker",
            "current_value": admin_count,
        }
    )

    # Requirement 3: Has contact email (optional but recommended)
    requirements.append(
        {
            "requirement": "Has contact email configured",
            "met": company.contact_email is not None and company.contact_email != "",
            "severity": "warning",
        }
    )

    # Requirement 4: Has company logo (optional)
    requirements.append(
        {
            "requirement": "Has company logo",
            "met": company.company_logo is not None and company.company_logo != "",
            "severity": "info",
        }
    )

    # Calculate overall status
    blockers = [r for r in requirements if not r["met"] and r["severity"] == "blocker"]
    warnings = [r for r in requirements if not r["met"] and r["severity"] == "warning"]

    return {
        "company_id": company_id,
        "company_name": company.name,
        "onboarding_complete": len(blockers) == 0,
        "requirements": requirements,
        "blocker_count": len(blockers),
        "warning_count": len(warnings),
    }


# ============================================================================
# Task 176: Company Scope Conflict Resolver Tooling
# ============================================================================


@router.get("/scope-conflicts", response_model=CompanyScopeConflictReport)
async def detect_scope_conflicts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
):
    """
    Detect users with company scope conflicts.

    Identifies situations where user roles/permissions conflict with their company assignment.
    """
    conflicts: list[CompanyScopeConflict] = []

    # Find all users
    all_users = db.query(User).all()

    for user in all_users:
        # Conflict 1: Customer without company
        if user.role == UserRole.CUSTOMER and user.tenant_id is None:
            conflicts.append(
                CompanyScopeConflict(
                    user_id=user.id,
                    email=user.email,
                    role=user.role.value,
                    current_tenant_id=user.tenant_id,
                    conflict_type="missing_company",
                    description="Customer user has no company assigned",
                )
            )

        # Conflict 2: Customer assigned to inactive company
        elif user.role == UserRole.CUSTOMER and user.tenant_id:
            tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
            if tenant and not tenant.is_active:
                conflicts.append(
                    CompanyScopeConflict(
                        user_id=user.id,
                        email=user.email,
                        role=user.role.value,
                        current_tenant_id=user.tenant_id,
                        conflict_type="inactive_company",
                        description=f"Customer is assigned to inactive company '{tenant.name}'",
                    )
                )
            elif not tenant:
                conflicts.append(
                    CompanyScopeConflict(
                        user_id=user.id,
                        email=user.email,
                        role=user.role.value,
                        current_tenant_id=user.tenant_id,
                        conflict_type="deleted_company",
                        description=f"Customer is assigned to non-existent company (id={user.tenant_id})",
                    )
                )

        # Conflict 3: Non-customer with customer-only company type (if applicable)
        # This could be extended for more complex scenarios

    return CompanyScopeConflictReport(
        conflict_count=len(conflicts),
        conflicts=conflicts,
    )


@router.post("/resolve-orphan-customers")
async def resolve_orphan_customers(
    action: str,  # "deactivate" or "report_only"
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
):
    """
    Resolve orphan customer users.

    Actions:
    - report_only: Just return what would be affected
    - deactivate: Deactivate all orphan customer users
    """
    if action not in ["deactivate", "report_only"]:
        raise HTTPException(status_code=400, detail="Action must be 'deactivate' or 'report_only'")

    # Detect orphans
    orphans = []
    customers = db.query(User).filter(User.role == UserRole.CUSTOMER).all()

    for customer in customers:
        is_orphan = False

        if customer.tenant_id is None:
            is_orphan = True
        else:
            tenant = db.query(Tenant).filter(Tenant.id == customer.tenant_id).first()
            if not tenant or not tenant.is_active:
                is_orphan = True

        if is_orphan:
            orphans.append(customer)

    if action == "report_only":
        return {
            "action": "report_only",
            "orphan_count": len(orphans),
            "affected_users": [{"id": u.id, "email": u.email} for u in orphans],
        }

    # Deactivate orphans
    deactivated_count = 0
    for orphan in orphans:
        if orphan.is_active:
            orphan.is_active = False
            deactivated_count += 1

    db.commit()

    return {
        "action": "deactivate",
        "orphan_count": len(orphans),
        "deactivated_count": deactivated_count,
        "affected_users": [{"id": u.id, "email": u.email} for u in orphans],
    }


@router.post("/resolve-orphan-invitations")
async def resolve_orphan_invitations(
    action: str,  # "cancel" or "report_only"
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
):
    """
    Resolve orphan invitations.

    Actions:
    - report_only: Just return what would be affected
    - cancel: Cancel all orphan pending invitations
    """
    if action not in ["cancel", "report_only"]:
        raise HTTPException(status_code=400, detail="Action must be 'cancel' or 'report_only'")

    # Detect orphans
    orphans = []
    pending_invitations = (
        db.query(Invitation).filter(Invitation.status == InvitationStatus.PENDING).all()
    )

    for invitation in pending_invitations:
        is_orphan = False

        if invitation.role == UserRole.CUSTOMER and invitation.tenant_id is None:
            is_orphan = True
        elif invitation.tenant_id is not None:
            tenant = db.query(Tenant).filter(Tenant.id == invitation.tenant_id).first()
            if not tenant or not tenant.is_active:
                is_orphan = True

        if is_orphan:
            orphans.append(invitation)

    if action == "report_only":
        return {
            "action": "report_only",
            "orphan_count": len(orphans),
            "affected_invitations": [{"id": i.id, "email": i.email} for i in orphans],
        }

    # Cancel orphans
    cancelled_count = 0
    for orphan in orphans:
        orphan.status = InvitationStatus.CANCELLED
        cancelled_count += 1

    db.commit()

    return {
        "action": "cancel",
        "orphan_count": len(orphans),
        "cancelled_count": cancelled_count,
        "affected_invitations": [{"id": i.id, "email": i.email} for i in orphans],
    }
