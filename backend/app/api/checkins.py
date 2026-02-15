"""Mood check-ins API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_veteran
from app.db.session import get_db
from app.models.mood_checkin import MoodCheckin
from app.models.user import User
from app.schemas.mood_checkin import MoodCheckinCreate, MoodCheckinResponse

router = APIRouter(prefix="/checkins", tags=["checkins"])


@router.post("", response_model=MoodCheckinResponse)
def create_checkin(
    data: MoodCheckinCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_veteran),
):
    """Create a mood check-in. Only veterans can create."""
    checkin = MoodCheckin(
        veteran_id=current_user.id,
        mood_score=data.mood_score,
        tags=data.tags,
        note=data.note,
        wants_company=data.wants_company,
    )
    db.add(checkin)
    db.commit()
    db.refresh(checkin)
    return checkin


@router.get("/me", response_model=list[MoodCheckinResponse])
def get_my_checkins(
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's check-ins, newest first. Default limit 30."""
    stmt = (
        select(MoodCheckin)
        .where(MoodCheckin.veteran_id == current_user.id)
        .order_by(desc(MoodCheckin.created_at), desc(MoodCheckin.id))
        .limit(limit)
    )
    result = db.execute(stmt)
    return list(result.scalars().all())
