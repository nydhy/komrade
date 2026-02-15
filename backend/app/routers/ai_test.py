"""AI provider test router."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.ai_service import AIServiceError, generate_structured

router = APIRouter(tags=["ai"])

TEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["summary", "confidence"],
    "properties": {
        "summary": {"type": "string"},
        "confidence": {"type": "number"},
    },
}


class AITestRequest(BaseModel):
    provider: Literal["gemini", "ollama"]
    payload: dict[str, Any] = Field(default_factory=dict)


class AITestResponse(BaseModel):
    provider: str
    data: dict[str, Any]


@router.post("/ai/test-structured", response_model=AITestResponse)
def test_structured(body: AITestRequest) -> AITestResponse:
    """Test structured output generation through configured AI provider."""
    try:
        data = generate_structured(
            provider=body.provider,
            task="Summarize this payload in one sentence and provide confidence between 0 and 1.",
            payload=body.payload,
            schema=TEST_SCHEMA,
        )
    except AIServiceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return AITestResponse(provider=body.provider, data=data)
