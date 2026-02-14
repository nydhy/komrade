"""Presence and location schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class PresenceUpdate(BaseModel):
    status: str = Field(..., pattern="^(AVAILABLE|BUSY|OFFLINE)$")


class PresenceResponse(BaseModel):
    user_id: int
    status: str
    updated_at: datetime

    model_config = {"from_attributes": True}


class LocationUpdate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class NearbyBuddyResponse(BaseModel):
    buddy_id: int
    buddy_name: str
    buddy_email: str
    trust_level: int
    presence_status: str  # AVAILABLE | BUSY | OFFLINE
    distance_km: float | None  # None if no location data
