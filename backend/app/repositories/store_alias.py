from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store_alias import StoreAlias


class StoreAliasRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_alias(self, name: str) -> StoreAlias | None:
        """Exact case-insensitive lookup."""
        result = await self.db.execute(
            select(StoreAlias).where(StoreAlias.alias_name_lower == name.lower())
        )
        return result.scalar_one_or_none()

    async def get_aliases_for_store(self, store_id: str) -> list[StoreAlias]:
        result = await self.db.execute(
            select(StoreAlias)
            .where(StoreAlias.store_id == store_id)
            .order_by(StoreAlias.alias_name)
        )
        return list(result.scalars().all())

    async def create(self, alias: StoreAlias) -> StoreAlias:
        self.db.add(alias)
        await self.db.flush()
        return alias

    async def delete_by_id(self, alias_id: str) -> None:
        await self.db.execute(
            delete(StoreAlias).where(StoreAlias.id == alias_id)
        )

    async def reassign(self, from_store_id: str, to_store_id: str) -> None:
        """Move all aliases from one store to another."""
        await self.db.execute(
            update(StoreAlias)
            .where(StoreAlias.store_id == from_store_id)
            .values(store_id=to_store_id)
        )

    async def alias_exists(self, name: str) -> bool:
        """Check if an alias already exists (case-insensitive)."""
        result = await self.db.execute(
            select(func.count()).select_from(StoreAlias).where(
                StoreAlias.alias_name_lower == name.lower()
            )
        )
        return (result.scalar() or 0) > 0
