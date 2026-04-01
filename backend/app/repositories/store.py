from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import Store


class StoreRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, store_id: str) -> Store | None:
        result = await self.db.execute(select(Store).where(Store.id == store_id))
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Store | None:
        result = await self.db.execute(
            select(Store).where(func.lower(Store.name) == name.lower())
        )
        return result.scalar_one_or_none()

    async def create(self, store: Store) -> Store:
        self.db.add(store)
        await self.db.flush()
        return store

    async def list_all(self) -> list[Store]:
        result = await self.db.execute(select(Store).order_by(Store.name))
        return list(result.scalars().all())
