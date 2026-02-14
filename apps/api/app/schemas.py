from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

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
    hashed_password: Optional[str]
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
