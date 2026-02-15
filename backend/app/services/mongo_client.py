"""MongoDB client helpers."""

from __future__ import annotations

from typing import Any

from app.core.config import settings

_client: Any | None = None


def get_mongo_client() -> Any:
    """Return a singleton Motor client."""
    global _client
    if _client is None:
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
        except ImportError as exc:
            raise RuntimeError("motor is not installed. Add 'motor' to backend requirements.") from exc
        _client = AsyncIOMotorClient(settings.mongo_uri)
    return _client


def get_translations_collection() -> Any:
    """Return the translations collection in komrade DB."""
    client = get_mongo_client()
    return client["komrade"]["translations"]
