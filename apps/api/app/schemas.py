from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    name: str
    email: str
    hashed_password: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    lat: Optional[Decimal]
    lng: Optional[Decimal]
    created_at: datetime


class MoodCheckinCreate(BaseModel):
    user_id: uuid.UUID
    mood_score: int = Field(ge=1, le=10)
    note: Optional[str] = None


class MoodCheckinOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    mood_score: int
    note: Optional[str]
    created_at: datetime


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    name: Optional[str] = None
    full_name: Optional[str] = None
    role: str = "veteran"
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserMe(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    latitude: Optional[float]
    longitude: Optional[float]
    created_at: datetime


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class SeedUserCredentials(BaseModel):
    email: str
    password: str


class SeedResponse(BaseModel):
    primary_user: SeedUserCredentials
    buddy_users: list[SeedUserCredentials]


class LadderWeek(BaseModel):
    week: int = Field(ge=1, le=8)
    title: str
    difficulty: Literal["low", "med", "high"]
    rationale: str
    suggested_time: str


class LadderResult(BaseModel):
    weeks: list[LadderWeek] = Field(min_length=8, max_length=8)


class LadderRequest(BaseModel):
    intake: dict[str, Any]


class TranslateRequest(BaseModel):
    message: str = Field(min_length=1)
    context: Optional[dict[str, Any]] = None


class TranslateResult(BaseModel):
    generic_answer: str
    empathetic_personalized_answer: str
    safety_flag: Literal["none", "crisis"]


class LadderPlanCreateRequest(BaseModel):
    weeks: list[LadderWeek] = Field(min_length=8, max_length=8)


class LadderChallengeOut(BaseModel):
    id: uuid.UUID
    week: int
    title: str
    difficulty: str
    rationale: str
    suggested_time: Optional[str]
    status: str
    completed: bool


class LadderPlanOut(BaseModel):
    plan_id: uuid.UUID
    created_at: datetime
    challenges: list[LadderChallengeOut]


class LadderChallengeCompleteRequest(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None
    photo_url: Optional[str] = None


class LegacyMoodCheckinCreate(BaseModel):
    mood_score: int = Field(ge=1, le=5)
    tags: list[str] = Field(default_factory=list)
    note: Optional[str] = None
    wants_company: bool = False


class LegacyMoodCheckinResponse(BaseModel):
    id: uuid.UUID
    veteran_id: uuid.UUID
    mood_score: int
    tags: list[str]
    note: Optional[str]
    wants_company: bool
    created_at: datetime


class BuddyInviteRequest(BaseModel):
    buddy_email: Optional[str] = None
    buddy_id: Optional[uuid.UUID] = None
    trust_level: int = Field(default=3, ge=1, le=5)


class BuddyLinkResponse(BaseModel):
    id: uuid.UUID
    veteran_id: uuid.UUID
    buddy_id: uuid.UUID
    status: str
    trust_level: int
    created_at: datetime


class BuddyLinkWithUser(BuddyLinkResponse):
    other_email: str
    other_name: str
    other_latitude: Optional[float]
    other_longitude: Optional[float]
    other_location_label: Optional[str] = None
    other_presence_status: Optional[str]


class PresenceUpdate(BaseModel):
    status: Literal["AVAILABLE", "BUSY", "OFFLINE"]


class PresenceResponse(BaseModel):
    user_id: uuid.UUID
    status: str
    updated_at: datetime


class LocationUpdate(BaseModel):
    latitude: float
    longitude: float


class NearbyBuddyResponse(BaseModel):
    buddy_id: uuid.UUID
    buddy_name: str
    buddy_email: str
    trust_level: int
    presence_status: str
    distance_km: Optional[float]


class UserSettingsResponse(BaseModel):
    user_id: uuid.UUID
    quiet_hours_start: Optional[str]
    quiet_hours_end: Optional[str]
    share_precise_location: bool
    sos_radius_km: Optional[float]
    updated_at: datetime


class UserSettingsUpdate(BaseModel):
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    share_precise_location: Optional[bool] = None
    sos_radius_km: Optional[float] = None


class ReportCreate(BaseModel):
    reported_user_id: uuid.UUID
    reason: str


class SosManualCreate(BaseModel):
    severity: Literal["LOW", "MED", "HIGH"] = "MED"
    buddy_ids: Optional[list[uuid.UUID]] = None
    broadcast: bool = False


class SosFromCheckinCreate(BaseModel):
    severity: Literal["LOW", "MED", "HIGH"] = "MED"
    buddy_ids: Optional[list[uuid.UUID]] = None
    broadcast: bool = False


class SosRespondRequest(BaseModel):
    status: Literal["ACCEPTED", "DECLINED"]
    message: Optional[str] = None
    eta_minutes: Optional[int] = None


class SosRecipientResponse(BaseModel):
    id: uuid.UUID
    sos_alert_id: uuid.UUID
    buddy_id: uuid.UUID
    status: str
    message: Optional[str]
    eta_minutes: Optional[int]
    responded_at: Optional[datetime]
    buddy_email: str
    buddy_name: str


class SosAlertResponse(BaseModel):
    id: uuid.UUID
    veteran_id: uuid.UUID
    trigger_type: str
    severity: str
    status: str
    created_at: datetime
    closed_at: Optional[datetime]
    recipients: list[SosRecipientResponse]


class IncomingSosAlertResponse(BaseModel):
    alert_id: uuid.UUID
    veteran_id: uuid.UUID
    veteran_name: str
    trigger_type: str
    severity: str
    alert_status: str
    created_at: datetime
    recipient_id: uuid.UUID
    my_status: str
    my_message: Optional[str]
    my_eta_minutes: Optional[int]
    responded_at: Optional[datetime]
