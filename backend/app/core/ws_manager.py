"""WebSocket connection manager for real-time events."""

import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Tracks active WebSocket connections keyed by user_id."""

    def __init__(self) -> None:
        # user_id -> set of active websocket connections
        self._connections: dict[int, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int) -> None:
        await websocket.accept()
        if user_id not in self._connections:
            self._connections[user_id] = set()
        self._connections[user_id].add(websocket)
        logger.info("WS connected: user=%s (total=%s)", user_id, self.total_connections)

    def disconnect(self, websocket: WebSocket, user_id: int) -> None:
        conns = self._connections.get(user_id)
        if conns:
            conns.discard(websocket)
            if not conns:
                del self._connections[user_id]
        logger.info("WS disconnected: user=%s (total=%s)", user_id, self.total_connections)

    async def send_to_user(self, user_id: int, event: str, data: Any) -> None:
        """Send event to all connections for a user."""
        conns = self._connections.get(user_id, set())
        payload = json.dumps({"event": event, "data": data}, default=str)
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            conns.discard(ws)

    async def send_to_users(self, user_ids: list[int], event: str, data: Any) -> None:
        """Broadcast event to multiple users."""
        for uid in user_ids:
            await self.send_to_user(uid, event, data)

    @property
    def total_connections(self) -> int:
        return sum(len(c) for c in self._connections.values())


# Singleton instance used across the app
ws_manager = ConnectionManager()
