from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.models.user_session import UserSession


class SessionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, session_id: str) -> UserSession | None:
        result = await self.db.execute(
            select(UserSession).where(
                UserSession.id == session_id,
                UserSession.expires_at > utc_now(),
            )
        )
        return result.scalar_one_or_none()

    async def create(self, session: UserSession) -> UserSession:
        self.db.add(session)
        await self.db.flush()
        return session

    async def delete_by_id(self, session_id: str) -> None:
        await self.db.execute(
            delete(UserSession).where(UserSession.id == session_id)
        )

    async def delete_expired(self) -> None:
        await self.db.execute(
            delete(UserSession).where(UserSession.expires_at <= utc_now())
        )
