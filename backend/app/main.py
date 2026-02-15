"""VetBridge FastAPI application."""

from fastapi import FastAPI

from app.api import auth, buddies, checkins, health, presence, sos, ws
from app.api import settings as settings_api
from app.core.config import settings
from app.routers import ai_test

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(buddies.router)
app.include_router(checkins.router)
app.include_router(sos.router)
app.include_router(presence.router)
app.include_router(settings_api.router)
app.include_router(ws.router)
app.include_router(ai_test.router)
