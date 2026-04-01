from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import StoreNotFoundError
from app.models.store import Store
from app.repositories.store import StoreRepository
from app.schemas.store import StoreUpdate


class StoreService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = StoreRepository(db)

    async def get_by_id(self, store_id: str) -> Store:
        store = await self.repo.get_by_id(store_id)
        if not store:
            raise StoreNotFoundError(f"Store {store_id} not found")
        return store

    async def list_stores(
        self,
        search: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Store], int]:
        query = select(Store)
        if search:
            query = query.where(Store.name.ilike(f"%{search}%"))

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        query = query.order_by(Store.name)
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        stores = list(result.scalars().all())

        return stores, total

    async def update(self, store_id: str, data: StoreUpdate) -> Store:
        store = await self.get_by_id(store_id)

        if data.name is not None:
            store.name = data.name
        if data.address is not None:
            store.address = data.address
        if data.chain is not None:
            store.chain = data.chain
        if data.latitude is not None:
            store.latitude = data.latitude
        if data.longitude is not None:
            store.longitude = data.longitude
        if data.is_verified is not None:
            store.is_verified = data.is_verified

        await self.db.flush()
        await self.db.commit()
        return store
