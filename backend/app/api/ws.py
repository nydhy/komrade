"""WebSocket endpoint with JWT auth."""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import decode_access_token
from app.core.ws_manager import ws_manager
from app.db.session import SessionLocal
from app.services.auth_service import get_user_by_email

logger = logging.getLogger(__name__)

router = APIRouter()


def _authenticate_ws(token: str) -> int | None:
    """Validate JWT and return user_id, or None."""
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    db = SessionLocal()
    try:
        user = get_user_by_email(db, payload["sub"])
        if not user or not user.is_active:
            return None
        return user.id
    finally:
        db.close()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint. Client connects with ?token=<jwt>.
    Server pushes events: sos.created, sos.recipient_updated, sos.closed
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    user_id = _authenticate_ws(token)
    if user_id is None:
        await websocket.close(code=4003, reason="Invalid or expired token")
        return

    await ws_manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive; client can send pings
            data = await websocket.receive_text()
            # Echo pong for heartbeat
            if data == "ping":
                await websocket.send_text('{"event":"pong"}')
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(websocket, user_id)
