"""Buddy link schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BuddyLinkBase(BaseModel):
    trust_level: int = Field(ge=1, le=5, default=3)


class BuddyInviteRequest(BaseModel):
    buddy_email: str | None = None
    buddy_id: int | None = None
    trust_level: int = Field(ge=1, le=5, default=3)


class BuddyLinkResponse(BaseModel):
    id: int
    veteran_id: int
    buddy_id: int
    status: str
    trust_level: int
    created_at: datetime

    model_config = {"from_attributes": True}


class BuddyLinkWithUser(BuddyLinkResponse):
    """Buddy link with the other person's info (buddy when veteran, veteran when buddy)."""

    other_email: str = ""
    other_name: str = ""
    other_latitude: float | None = None
    other_longitude: float | None = None
    other_location_label: str | None = None
    other_presence_status: str | None = None
