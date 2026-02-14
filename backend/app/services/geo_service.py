"""Geo and buddy ranking service."""

import math
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.buddy_link import BuddyLink
from app.models.buddy_presence import BuddyPresence
from app.models.user import User
from app.models.user_settings import UserSettings


@dataclass
class RankedBuddy:
    """Buddy ranked for SOS / nearby selection."""

    buddy_id: int
    buddy_name: str
    buddy_email: str
    trust_level: int
    presence_status: str  # AVAILABLE | BUSY | OFFLINE
    distance_km: float | None  # None if no location data
    rank_score: float  # Lower is better


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance between two lat/lng points in kilometers."""
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_ranked_buddies(
    db: Session,
    veteran_id: int,
    limit: int = 10,
    radius_km: float | None = None,
) -> list[RankedBuddy]:
    """
    Get veteran's accepted buddies ranked by:
      1. AVAILABLE first, then BUSY, then OFFLINE
      2. trust_level descending
      3. distance ascending (if location available)

    Blocked/pending buddies are excluded.
    """
    # Get veteran location
    veteran = db.get(User, veteran_id)
    vet_lat = veteran.latitude if veteran else None
    vet_lng = veteran.longitude if veteran else None

    # Get accepted buddy links
    links_result = db.execute(
        select(BuddyLink).where(
            BuddyLink.veteran_id == veteran_id,
            BuddyLink.status == "ACCEPTED",
        )
    )
    links = list(links_result.scalars().all())
    if not links:
        return []

    buddy_ids = [l.buddy_id for l in links]
    trust_map = {l.buddy_id: l.trust_level for l in links}

    # Get buddy users
    users_result = db.execute(select(User).where(User.id.in_(buddy_ids)))
    users = {u.id: u for u in users_result.scalars().all()}

    # Get presence
    presence_result = db.execute(
        select(BuddyPresence).where(BuddyPresence.user_id.in_(buddy_ids))
    )
    presence_map = {p.user_id: p.status for p in presence_result.scalars().all()}

    # Get settings for quiet hours filtering
    settings_result = db.execute(
        select(UserSettings).where(UserSettings.user_id.in_(buddy_ids))
    )
    settings_map = {s.user_id: s for s in settings_result.scalars().all()}

    # Filter out buddies in quiet hours
    now_utc = datetime.now(timezone.utc)
    current_hhmm = now_utc.strftime("%H:%M")

    def _in_quiet_hours(uid: int) -> bool:
        s = settings_map.get(uid)
        if not s or not s.quiet_hours_start or not s.quiet_hours_end:
            return False
        start, end = s.quiet_hours_start, s.quiet_hours_end
        if start <= end:
            return start <= current_hhmm <= end
        else:  # wraps midnight e.g. 22:00 -> 07:00
            return current_hhmm >= start or current_hhmm <= end

    # Build ranked list
    ranked: list[RankedBuddy] = []
    for bid in buddy_ids:
        u = users.get(bid)
        if not u:
            continue

        # Skip buddies in quiet hours
        if _in_quiet_hours(bid):
            continue

        pres = presence_map.get(bid, "OFFLINE")

        # Skip OFFLINE buddies — they should not appear on anyone's radar
        if pres == "OFFLINE":
            continue

        trust = trust_map.get(bid, 3)

        # Distance
        dist: float | None = None
        if vet_lat is not None and vet_lng is not None and u.latitude is not None and u.longitude is not None:
            dist = haversine_km(vet_lat, vet_lng, u.latitude, u.longitude)

        # Rank score: lower is better
        # Availability: AVAILABLE=0, BUSY=100, OFFLINE=200
        avail_score = {"AVAILABLE": 0, "BUSY": 100, "OFFLINE": 200}.get(pres, 200)
        # Trust: higher is better -> negate (5=0, 1=4)
        trust_score = (5 - trust) * 10
        # Distance: normalized (capped at 500km)
        dist_score = min(dist, 500) if dist is not None else 250  # unknown = mid-range

        score = avail_score + trust_score + dist_score

        ranked.append(
            RankedBuddy(
                buddy_id=bid,
                buddy_name=u.full_name,
                buddy_email=u.email,
                trust_level=trust,
                presence_status=pres,
                distance_km=round(dist, 2) if dist is not None else None,
                rank_score=score,
            )
        )

    # If radius specified, filter out buddies known to be beyond it
    # Buddies with unknown distance (no location) are kept (benefit of the doubt)
    if radius_km is not None:
        ranked = [r for r in ranked if r.distance_km is None or r.distance_km <= radius_km]

    ranked.sort(key=lambda r: r.rank_score)
    return ranked[:limit]
