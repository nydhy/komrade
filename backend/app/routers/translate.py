"""Translation Layer API (text-only)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.deps import get_current_user
from app.models.user import User
from app.services.ai_service import AIServiceError, generate_structured
from app.services.mongo_client import get_translations_collection

router = APIRouter(tags=["translate"])

TRANSLATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["generic_answer", "empathetic_personalized_answer", "safety_flag"],
    "properties": {
        "generic_answer": {"type": "string"},
        "empathetic_personalized_answer": {"type": "string"},
        "safety_flag": {"type": "string"},
    },
}

CRISIS_KEYWORDS = {
    "suicide",
    "kill myself",
    "end my life",
    "self harm",
    "hurt myself",
    "i want to die",
    "i don't want to live",
    "overdose",
}


class TranslateRequest(BaseModel):
    provider: Literal["gemini", "ollama"]
    message: str = Field(min_length=1)
    context: dict[str, Any] | None = None


class TranslateResponse(BaseModel):
    generic_answer: str
    empathetic_personalized_answer: str
    safety_flag: str


class TranslateHistoryItem(TranslateResponse):
    created_at: datetime
    user_id: int
    provider: str
    message: str
    context: dict[str, Any] | None = None


@router.post("/translate", response_model=TranslateResponse)
async def translate_text(
    body: TranslateRequest,
    current_user: User = Depends(get_current_user),
) -> TranslateResponse:
    """Generate translation-layer responses and persist log to MongoDB."""
    if _is_crisis_intent(body.message):
        result = {
            "generic_answer": "I’m really glad you reached out. You deserve immediate support right now.",
            "empathetic_personalized_answer": (
                "I’m concerned about your safety. Please contact local emergency services now, "
                "or call/text 988 (US Suicide & Crisis Lifeline) for immediate support."
            ),
            "safety_flag": "crisis",
        }
    else:
        task = (
            "Rewrite the user's message in two styles: "
            "(1) generic supportive wording, "
            "(2) empathetic personalized wording that uses any provided context. "
            "Set safety_flag to 'normal' unless direct safety concern is obvious, then 'warning'."
        )
        payload = {
            "message": body.message,
            "context": body.context or {},
            "user_id": current_user.id,
        }

        try:
            result = generate_structured(
                provider=body.provider,
                task=task,
                payload=payload,
                schema=TRANSLATION_SCHEMA,
            )
        except AIServiceError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    doc = {
        "created_at": datetime.now(timezone.utc),
        "user_id": current_user.id,
        "provider": body.provider,
        "message": body.message,
        "context": body.context,
        "generic_answer": result["generic_answer"],
        "empathetic_personalized_answer": result["empathetic_personalized_answer"],
        "safety_flag": result["safety_flag"],
    }

    collection = get_translations_collection()
    await collection.insert_one(doc)

    return TranslateResponse(**result)


@router.get("/translate/history", response_model=list[TranslateHistoryItem])
async def translate_history(
    limit: int = Query(default=10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
) -> list[TranslateHistoryItem]:
    """Return latest translation logs for the current user."""
    collection = get_translations_collection()
    cursor = collection.find({"user_id": current_user.id}).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)

    items: list[TranslateHistoryItem] = []
    for doc in docs:
        doc.pop("_id", None)
        items.append(TranslateHistoryItem(**doc))

    return items


def _is_crisis_intent(message: str) -> bool:
    text = message.lower()
    return any(keyword in text for keyword in CRISIS_KEYWORDS)
