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
    name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


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
