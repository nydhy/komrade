"""Mood check-in schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class MoodCheckinCreate(BaseModel):
    mood_score: int = Field(ge=1, le=5, description="Mood 1-5")
    tags: list[str] = Field(default_factory=list, max_length=20)
    note: str | None = None
    wants_company: bool = False


class MoodCheckinResponse(BaseModel):
    id: int
    veteran_id: int
    mood_score: int
    tags: list[str]
    note: str | None
    wants_company: bool
    created_at: datetime

    model_config = {"from_attributes": True}
