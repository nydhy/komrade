"""Speech-to-text endpoints."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(tags=["stt"])

MAX_AUDIO_BYTES = 10 * 1024 * 1024
ALLOWED_AUDIO_TYPES = {
    "audio/webm",
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
}
ELEVENLABS_STT_URLS = (
    "https://api.elevenlabs.io/v1/speech-to-text/convert",
    "https://api.elevenlabs.io/v1/speech-to-text",
)


class SttResponse(BaseModel):
    transcript: str


@router.post("/stt/elevenlabs", response_model=SttResponse)
async def transcribe_elevenlabs(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> SttResponse:
    """Transcribe uploaded audio with ElevenLabs Speech-to-Text."""
    _ = current_user  # endpoint is authenticated for parity with translate flow

    if not settings.elevenlabs_api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Speech-to-text is not configured. Set ELEVENLABS_API_KEY.",
        )

    if not _is_allowed_audio(audio):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Upload audio/webm or audio/wav.",
        )

    content = await audio.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty. Please record audio and try again.",
        )
    if len(content) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Audio file is too large. Max size is {MAX_AUDIO_BYTES // (1024 * 1024)} MB.",
        )

    try:
        transcript = await _convert_with_elevenlabs(
            filename=audio.filename or "recording.webm",
            content=content,
            content_type=audio.content_type or "audio/webm",
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - surface friendly API error
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Speech-to-text failed: {exc}",
        ) from exc

    return SttResponse(transcript=transcript)


def _is_allowed_audio(audio: UploadFile) -> bool:
    content_type = (audio.content_type or "").lower()
    if content_type in ALLOWED_AUDIO_TYPES:
        return True
    filename = (audio.filename or "").lower()
    return filename.endswith(".webm") or filename.endswith(".wav")


async def _convert_with_elevenlabs(filename: str, content: bytes, content_type: str) -> str:
    headers = {"xi-api-key": settings.elevenlabs_api_key.strip()}
    files = {"file": (filename, content, content_type)}
    data = {"model_id": "scribe_v1"}

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response: httpx.Response | None = None
            for url in ELEVENLABS_STT_URLS:
                candidate = await client.post(
                    url,
                    headers=headers,
                    data=data,
                    files=files,
                )
                if candidate.status_code == 404:
                    response = candidate
                    continue
                response = candidate
                break

            if response is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="ElevenLabs request failed: no response received.",
                )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        message = _extract_error_message(exc.response)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"ElevenLabs request failed: {message}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not reach ElevenLabs: {exc}",
        ) from exc

    payload: dict[str, Any] = response.json()
    transcript = payload.get("text") or payload.get("transcript") or ""
    if not isinstance(transcript, str) or not transcript.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ElevenLabs returned an empty transcript.",
        )
    return transcript.strip()


def _extract_error_message(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text or response.reason_phrase
    detail = data.get("detail")
    if isinstance(detail, str):
        return detail
    if isinstance(detail, dict):
        return str(detail)
    message = data.get("message")
    if isinstance(message, str):
        return message
    return response.reason_phrase
