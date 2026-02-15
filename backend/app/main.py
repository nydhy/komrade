"""komrade FastAPI application."""

from __future__ import annotations

import logging

from fastapi import FastAPI

from app.api import auth, buddies, checkins, health, journey, presence, sos, ws
from app.api import settings as settings_api
from app.core.config import settings
from app.routers import ai_test, stt, translate

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(buddies.router)
app.include_router(checkins.router)
app.include_router(sos.router)
app.include_router(presence.router)
app.include_router(settings_api.router)
app.include_router(ws.router)
app.include_router(journey.router)
app.include_router(ai_test.router)
app.include_router(translate.router)
app.include_router(stt.router)
