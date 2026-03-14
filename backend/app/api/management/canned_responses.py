"""Canned response CRUD endpoints for support agents (Wave X.1 — X1-103/104)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.permissions import require_internal_user
from app.models import CannedResponse, User
from app.schemas.chat import (
    CannedResponseCreate,
    CannedResponseListResponse,
    CannedResponseResponse,
    CannedResponseUpdate,
)

router = APIRouter()


def _to_response(cr: CannedResponse) -> CannedResponseResponse:
    return CannedResponseResponse(
        id=cr.id,
        title=cr.title,
        content=cr.content,
        category=cr.category,
        created_by=cr.created_by,
        creator_name=cr.creator.full_name if cr.creator else None,
        tenant_id=cr.tenant_id,
        created_at=cr.created_at,
        updated_at=cr.updated_at,
    )


@router.get("/support/canned-responses", response_model=CannedResponseListResponse)
def list_canned_responses(
    category: str | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_internal_user),
):
    """List canned responses for the current user's tenant."""
    q = db.query(CannedResponse).filter(CannedResponse.tenant_id == current_user.tenant_id)
    if category:
        q = q.filter(CannedResponse.category == category)
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            (CannedResponse.title.ilike(pattern)) | (CannedResponse.content.ilike(pattern))
        )
    q = q.order_by(CannedResponse.title)
    items = q.all()
    return CannedResponseListResponse(items=[_to_response(cr) for cr in items], total=len(items))


@router.post(
    "/support/canned-responses",
    response_model=CannedResponseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_canned_response(
    body: CannedResponseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_internal_user),
):
    """Create a new canned response."""
    cr = CannedResponse(
        title=body.title,
        content=body.content,
        category=body.category,
        created_by=current_user.id,
        tenant_id=current_user.tenant_id,
    )
    db.add(cr)
    db.commit()
    db.refresh(cr)
    return _to_response(cr)


@router.patch("/support/canned-responses/{response_id}", response_model=CannedResponseResponse)
def update_canned_response(
    response_id: int,
    body: CannedResponseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_internal_user),
):
    """Update an existing canned response."""
    cr = (
        db.query(CannedResponse)
        .filter(CannedResponse.id == response_id, CannedResponse.tenant_id == current_user.tenant_id)
        .first()
    )
    if not cr:
        raise HTTPException(status_code=404, detail="Canned response not found")
    if body.title is not None:
        cr.title = body.title
    if body.content is not None:
        cr.content = body.content
    if body.category is not None:
        cr.category = body.category
    db.commit()
    db.refresh(cr)
    return _to_response(cr)


@router.delete("/support/canned-responses/{response_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_canned_response(
    response_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_internal_user),
):
    """Delete a canned response."""
    cr = (
        db.query(CannedResponse)
        .filter(CannedResponse.id == response_id, CannedResponse.tenant_id == current_user.tenant_id)
        .first()
    )
    if not cr:
        raise HTTPException(status_code=404, detail="Canned response not found")
    db.delete(cr)
    db.commit()
