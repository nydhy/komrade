"""User settings schemas."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class UserSettingsUpdate(BaseModel):
    quiet_hours_start: str | None = Field(default=None, description="HH:MM format, e.g. 22:00")
    quiet_hours_end: str | None = Field(default=None, description="HH:MM format, e.g. 07:00")
    share_precise_location: bool | None = None
    sos_radius_km: float | None = Field(default=None, ge=5, le=500, description="SOS radius in km (5-500)")

    @field_validator("quiet_hours_start", "quiet_hours_end")
    @classmethod
    def validate_time_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        parts = v.split(":")
        if len(parts) != 2:
            raise ValueError("Must be HH:MM format")
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError("Invalid time")
        return v


class UserSettingsResponse(BaseModel):
    user_id: int
    quiet_hours_start: str | None
    quiet_hours_end: str | None
    share_precise_location: bool
    sos_radius_km: float | None
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportCreate(BaseModel):
    reported_user_id: int
    reason: str = Field(min_length=5, max_length=500)
