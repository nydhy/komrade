"""Journey API."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.journey import (
    JourneyChallengeInsightsOut,
    JourneyGenerateRequest,
    JourneyGenerateResponse,
    JourneyProgressOut,
    JourneyProgressSaveRequest,
    JourneyProgressWithChallenges,
)
from app.services.journey_service import (
    generate_challenges_for_user,
    generate_challenge_insights_for_user,
    get_or_create_progress,
    list_challenges_for_user,
    save_progress_for_user,
)

router = APIRouter(prefix="/api/journey", tags=["journey"])
logger = logging.getLogger(__name__)


@router.post("/challenges/generate", response_model=JourneyGenerateResponse)
def generate_challenges(
    data: JourneyGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        challenges, blocked_terms, provider_used = generate_challenges_for_user(
            db,
            current_user.id,
            anxiety_level=data.anxiety_level,
            interests=data.interests,
            triggers=data.triggers,
            time_since_comfortable=data.time_since_comfortable,
            end_goal=data.end_goal,
            energy_times=data.energy_times,
            location=data.location,
            avoid_situations=data.avoid_situations,
            challenge_count=data.challenge_count,
        )
        return JourneyGenerateResponse(
            challenges=challenges,
            blocked_terms=blocked_terms,
            provider=provider_used,
        )
    except Exception:
        logger.exception("journey_generate_failed user_id=%s", current_user.id)
        raise


@router.get("/progress", response_model=JourneyProgressWithChallenges)
def get_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    progress = get_or_create_progress(db, current_user.id)
    db.commit()
    db.refresh(progress)
    challenges = list_challenges_for_user(db, current_user.id)
    return JourneyProgressWithChallenges(progress=JourneyProgressOut.model_validate(progress), challenges=challenges)


@router.post("/progress/save", response_model=JourneyProgressWithChallenges)
def save_progress(
    data: JourneyProgressSaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    progress = save_progress_for_user(
        db,
        current_user.id,
        challenge_id=data.challenge_id,
        completed=data.completed,
        xp_earned=data.xp_earned,
        current_feeling=data.current_feeling,
        next_step=data.next_step,
        avoidance_list=data.avoidance_list,
    )
    challenges = list_challenges_for_user(db, current_user.id)
    return JourneyProgressWithChallenges(progress=JourneyProgressOut.model_validate(progress), challenges=challenges)


@router.get("/challenges/{challenge_id}/insights", response_model=JourneyChallengeInsightsOut)
def get_challenge_insights(
    challenge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    insights = generate_challenge_insights_for_user(db, current_user.id, challenge_id)
    return JourneyChallengeInsightsOut.model_validate(insights)
