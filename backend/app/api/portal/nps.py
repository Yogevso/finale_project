"""NPS Survey API — portal endpoints for submitting and checking NPS surveys."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import NpsSurvey, User
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
    days: int = 90,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get NPS results summary (for managers/admins)."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    surveys = (
        db.query(NpsSurvey.score)
        .filter(NpsSurvey.created_at >= cutoff)
        .all()
    )
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
