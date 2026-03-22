"""NPS Survey API — portal endpoints for submitting and checking NPS surveys."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import NpsSurvey, User, UserRole
from app.security import get_current_active_user

router = APIRouter(prefix="/portal/nps", tags=["NPS Survey"])


class NpsSubmitRequest(BaseModel):
    score: int = Field(..., ge=0, le=10)
    comment: str | None = None


@router.get("/status")
async def nps_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Check if the user should see the NPS survey (not submitted in last 90 days)."""
    cutoff = datetime.utcnow() - timedelta(days=90)
    recent = (
        db.query(NpsSurvey)
        .filter(
            NpsSurvey.user_id == current_user.id,
            NpsSurvey.created_at >= cutoff,
        )
        .first()
    )
    return {"should_show": recent is None}


@router.post("")
async def submit_nps(
    body: NpsSubmitRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Submit an NPS survey response."""
    # Enforce 90-day cooldown server-side (not just advisory via /status)
    cutoff = datetime.utcnow() - timedelta(days=90)
    recent = (
        db.query(NpsSurvey)
        .filter(
            NpsSurvey.user_id == current_user.id,
            NpsSurvey.created_at >= cutoff,
        )
        .first()
    )
    if recent is not None:
        raise HTTPException(status_code=429, detail="NPS survey already submitted within the last 90 days")

    survey = NpsSurvey(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        score=body.score,
        comment=body.comment,
    )
    db.add(survey)
    db.commit()
    return {"status": "submitted"}


@router.get("/results")
async def nps_results(
    days: int = Query(90, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get NPS results summary (for managers/admins)."""
    allowed_roles = {UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER}
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Only managers and admins can view NPS results")

    cutoff = datetime.utcnow() - timedelta(days=days)
    query = db.query(NpsSurvey.score).filter(NpsSurvey.created_at >= cutoff)

    # Tenant isolation: non-system-admins see only their own tenant's data
    if current_user.role != UserRole.SYSTEM_ADMIN:
        query = query.filter(NpsSurvey.tenant_id == current_user.tenant_id)

    surveys = query.all()
    if not surveys:
        return {"total": 0, "nps_score": None, "promoters": 0, "passives": 0, "detractors": 0}

    scores = [s[0] for s in surveys]
    total = len(scores)
    promoters = sum(1 for s in scores if s >= 9)
    detractors = sum(1 for s in scores if s <= 6)
    passives = total - promoters - detractors
    nps = round(((promoters - detractors) / total) * 100)

    return {
        "total": total,
        "nps_score": nps,
        "promoters": promoters,
        "passives": passives,
        "detractors": detractors,
    }
