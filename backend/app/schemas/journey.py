"""Journey schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


def _parse_structured_description(description: str | None) -> dict[str, Any]:
    if not description:
        return {}

    parsed: dict[str, Any] = {}
    for line in description.splitlines():
        clean = line.strip()
        if not clean:
            continue
        if clean.startswith("Duration: "):
            parsed["duration"] = clean.removeprefix("Duration: ").strip()
        elif clean.startswith("Best times (but whenever works): "):
            raw = clean.removeprefix("Best times (but whenever works): ")
            parsed["recommended_times"] = [item.strip() for item in raw.split(";") if item.strip()]
        elif clean.startswith("Suggestions near you: "):
            raw = clean.removeprefix("Suggestions near you: ")
            parsed["suggested_locations"] = [item.strip() for item in raw.split(";") if item.strip()]
        elif clean.startswith("Interaction required: "):
            parsed["interaction_required"] = clean.removeprefix("Interaction required: ").strip()
        elif clean.startswith("Comfort zone: "):
            parsed["comfort_zone"] = clean.removeprefix("Comfort zone: ").strip()
        elif clean.startswith("What this builds: "):
            parsed["what_this_builds"] = clean.removeprefix("What this builds: ").strip()
        elif clean.startswith("Why this works: "):
            parsed["why_this_works"] = clean.removeprefix("Why this works: ").strip()
        elif clean.startswith("Exit strategy: "):
            parsed["exit_strategy"] = clean.removeprefix("Exit strategy: ").strip()
        elif clean.startswith("You can also: "):
            raw = clean.removeprefix("You can also: ")
            parsed["you_can_also"] = [item.strip() for item in raw.split(";") if item.strip()]
        elif clean.startswith("If easier needed: "):
            parsed.setdefault("modifications", {})["if_easier_needed"] = clean.removeprefix("If easier needed: ").strip()
        elif clean.startswith("If ready for more: "):
            parsed.setdefault("modifications", {})["if_ready_for_more"] = clean.removeprefix("If ready for more: ").strip()
    return parsed


class JourneyChallengeOut(BaseModel):
    id: int
    title: str
    description: str | None
    difficulty: str
    xp_reward: int
    is_completed: bool
    sort_order: int
    created_at: datetime
    completed_at: datetime | None
    challenge_number: int | None = None
    duration: str | None = None
    recommended_times: list[str] = Field(default_factory=list)
    suggested_locations: list[str] = Field(default_factory=list)
    interaction_required: str | None = None
    comfort_zone: str | None = None
    what_this_builds: str | None = None
    why_this_works: str | None = None
    exit_strategy: str | None = None
    you_can_also: list[str] = Field(default_factory=list)
    modifications: dict[str, str] | None = None

    @model_validator(mode="before")
    @classmethod
    def hydrate_optional_fields(cls, value: Any) -> Any:
        if isinstance(value, dict):
            data = dict(value)
            description = data.get("description")
            data.update({k: v for k, v in _parse_structured_description(description).items() if k not in data or not data.get(k)})
            if not data.get("challenge_number") and data.get("sort_order"):
                data["challenge_number"] = data["sort_order"]
            return data

        data = {
            "id": getattr(value, "id"),
            "title": getattr(value, "title"),
            "description": getattr(value, "description", None),
            "difficulty": getattr(value, "difficulty"),
            "xp_reward": getattr(value, "xp_reward"),
            "is_completed": getattr(value, "is_completed"),
            "sort_order": getattr(value, "sort_order"),
            "created_at": getattr(value, "created_at"),
            "completed_at": getattr(value, "completed_at", None),
        }
        data.update(_parse_structured_description(data.get("description")))
        data["challenge_number"] = data.get("sort_order")
        return data

    model_config = {"from_attributes": True}


class JourneyGenerateRequest(BaseModel):
    anxiety_level: int = Field(ge=1, le=10)
    interests: list[str] = Field(min_length=1, max_length=12)
    triggers: list[str] = Field(default_factory=list, max_length=20)
    time_since_comfortable: str | None = Field(default=None, max_length=60)
    end_goal: str | None = Field(default=None, max_length=120)
    energy_times: list[str] = Field(default_factory=list, max_length=8)
    location: str | None = Field(default=None, max_length=120)
    avoid_situations: str | None = Field(default=None, max_length=300)
    challenge_count: int = Field(default=6, ge=1, le=12)

    @field_validator("interests", "triggers")
    @classmethod
    def normalize_lists(cls, values: list[str]) -> list[str]:
        normalized = [v.strip() for v in values if v and v.strip()]
        # Keep insertion order while deduplicating.
        return list(dict.fromkeys(normalized))


class JourneyGenerateResponse(BaseModel):
    challenges: list[JourneyChallengeOut]
    blocked_terms: list[str]
    provider: str


class JourneyProgressSaveRequest(BaseModel):
    challenge_id: int | None = None
    completed: bool = False
    xp_earned: int = Field(default=0, ge=0, le=1000)
    current_feeling: str | None = Field(default=None, max_length=50)
    next_step: str | None = Field(default=None, max_length=100)
    avoidance_list: list[str] | None = Field(default=None, max_length=30)

    @field_validator("avoidance_list")
    @classmethod
    def normalize_avoidance_list(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        normalized = [v.strip() for v in values if v and v.strip()]
        return list(dict.fromkeys(normalized))


class JourneyProgressOut(BaseModel):
    user_id: int
    active_challenge_id: int | None
    xp_total: int
    level: int
    current_streak: int
    best_streak: int
    current_feeling: str | None
    next_step: str | None
    avoidance_list: list[str]
    updated_at: datetime

    model_config = {"from_attributes": True}


class JourneyProgressWithChallenges(BaseModel):
    progress: JourneyProgressOut
    challenges: list[JourneyChallengeOut]


class JourneyInsightTimelineItem(BaseModel):
    date_label: str
    feeling: str
    xp: int


class JourneyChallengeInsightsOut(BaseModel):
    challenge_id: int
    modal_subtitle: str
    success_timeline: list[JourneyInsightTimelineItem]
    what_you_built: list[str]
    memory_quote: str
    full_breakdown: list[str]
    what_youll_build_skill: str
    what_youll_build_prepares_for: str
    practical_best_time: str
    practical_duration: str
    practical_near_you: str
    exit_strategy: str
    modification_easier: str
    modification_harder: str
