"""Presence and location API."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_veteran
from app.db.session import get_db
from app.models.buddy_presence import BuddyPresence
from app.models.user import User
from app.schemas.presence import (
    LocationUpdate,
    NearbyBuddyResponse,
    PresenceResponse,
    PresenceUpdate,
)
from app.services.geo_service import get_ranked_buddies

router = APIRouter(tags=["presence"])


@router.get("/presence/me", response_model=PresenceResponse)
def get_my_presence(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the current user's saved presence status."""
    result = db.execute(
        select(BuddyPresence).where(BuddyPresence.user_id == current_user.id)
    )
    presence = result.scalar_one_or_none()
    if not presence:
        # Return OFFLINE default if no row exists yet
        return PresenceResponse(
            user_id=current_user.id,
            status="OFFLINE",
            updated_at=datetime.now(timezone.utc),
        )
    return presence


@router.post("/presence", response_model=PresenceResponse)
def update_presence(
    data: PresenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Buddy sets availability: AVAILABLE, BUSY, or OFFLINE."""
    result = db.execute(
        select(BuddyPresence).where(BuddyPresence.user_id == current_user.id)
    )
    presence = result.scalar_one_or_none()

    if presence:
        presence.status = data.status
        presence.updated_at = datetime.now(timezone.utc)
    else:
        presence = BuddyPresence(
            user_id=current_user.id,
            status=data.status,
        )
        db.add(presence)

    db.commit()
    db.refresh(presence)
    return presence


@router.post("/location")
def update_location(
    data: LocationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """User updates their location."""
    current_user.latitude = data.latitude
    current_user.longitude = data.longitude
    db.commit()
    return {"status": "ok", "latitude": data.latitude, "longitude": data.longitude}


@router.get("/buddies/nearby", response_model=list[NearbyBuddyResponse])
def nearby_buddies(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_veteran),
):
    """Get ranked list of nearby buddies (ACCEPTED only).

    Ranking: available first, then trust desc, then distance asc.
    """
    ranked = get_ranked_buddies(db, current_user.id, limit)
    return [
        NearbyBuddyResponse(
            buddy_id=r.buddy_id,
            buddy_name=r.buddy_name,
            buddy_email=r.buddy_email,
            trust_level=r.trust_level,
            presence_status=r.presence_status,
            distance_km=r.distance_km,
        )
        for r in ranked
    ]
