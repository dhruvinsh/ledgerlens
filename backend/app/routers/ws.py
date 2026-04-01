import json
import logging
from collections import defaultdict

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import async_session_factory
from app.core.security import verify_session_token
from app.repositories.session import SessionRepository
from app.repositories.user import UserRepository

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections keyed by user_id."""

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[user_id].append(websocket)
        logger.info("WS connected: user=%s (total=%d)", user_id, len(self._connections[user_id]))

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        conns = self._connections.get(user_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self._connections.pop(user_id, None)
        logger.info("WS disconnected: user=%s", user_id)

    async def send_to_user(self, user_id: str, data: dict) -> None:
        conns = self._connections.get(user_id, [])
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            conns.remove(ws)
        if not conns:
            self._connections.pop(user_id, None)


# Singleton — importable by other modules to push messages
manager = ConnectionManager()


async def _authenticate_ws(
    session_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> str | None:
    """Validate session token and return user_id, or None."""
    raw_id = verify_session_token(session_id)
    if not raw_id:
        return None

    async with session_factory() as db:
        session_repo = SessionRepository(db)
        session = await session_repo.get_by_id(raw_id)
        if not session:
            return None

        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(session.user_id)
        if not user or not user.is_active:
            return None

        return user.id


@router.websocket("/ws/jobs")
async def websocket_jobs(
    websocket: WebSocket,
    session_id: str | None = Query(default=None),
) -> None:
    # Accept session_id from query param or cookie (cookie is preferred for httpOnly)
    token = session_id or websocket.cookies.get("session_id")
    if not token:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    user_id = await _authenticate_ws(token, async_session_factory)
    if not user_id:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await manager.connect(user_id, websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(user_id, websocket)
