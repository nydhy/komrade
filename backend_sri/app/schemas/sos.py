"""SOS alert schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class SosManualCreate(BaseModel):
    severity: str = Field(..., pattern="^(LOW|MED|HIGH)$")
    buddy_ids: list[int] | None = Field(default=None, description="Target specific buddies; if empty/None and not broadcast, uses auto-selection")
    broadcast: bool = Field(default=False, description="If true, send to all accepted buddies")


class SosFromCheckinCreate(BaseModel):
    severity: str = Field(default="MED", pattern="^(LOW|MED|HIGH)$")
    buddy_ids: list[int] | None = Field(default=None, description="Target specific buddies")
    broadcast: bool = Field(default=False, description="If true, send to all accepted buddies")


class SosRespondRequest(BaseModel):
    """Buddy responds to an SOS alert."""

    status: str = Field(..., pattern="^(ACCEPTED|DECLINED)$")
    message: str | None = None
    eta_minutes: int | None = Field(default=None, ge=1, le=120)


class SosRecipientResponse(BaseModel):
    id: int
    sos_alert_id: int
    buddy_id: int
    status: str
    message: str | None
    eta_minutes: int | None
    responded_at: datetime | None

    model_config = {"from_attributes": True}


class SosRecipientWithBuddy(SosRecipientResponse):
    buddy_email: str = ""
    buddy_name: str = ""


class SosAlertResponse(BaseModel):
    id: int
    veteran_id: int
    trigger_type: str
    severity: str
    status: str
    created_at: datetime
    closed_at: datetime | None
    recipients: list[SosRecipientWithBuddy] = []

    model_config = {"from_attributes": True}


class IncomingSosAlertResponse(BaseModel):
    """An SOS alert as seen by a buddy recipient."""

    alert_id: int
    veteran_id: int
    veteran_name: str
    trigger_type: str
    severity: str
    alert_status: str
    created_at: datetime
    recipient_id: int
    my_status: str
    my_message: str | None
    my_eta_minutes: int | None
    responded_at: datetime | None
