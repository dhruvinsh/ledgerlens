from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.canonical_item import CanonicalItem


class CanonicalItemRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, item_id: str) -> CanonicalItem | None:
        result = await self.db.execute(
            select(CanonicalItem).where(CanonicalItem.id == item_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> CanonicalItem | None:
        result = await self.db.execute(
            select(CanonicalItem).where(func.lower(CanonicalItem.name) == name.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_alias(self, alias: str) -> CanonicalItem | None:
        """Search for an item where alias appears in the JSON aliases array."""
        # For SQLite, use JSON functions; for Postgres, use array operators
        all_items = await self.list_all()
        lower_alias = alias.lower()
        for item in all_items:
            if any(a.lower() == lower_alias for a in (item.aliases or [])):
                return item
        return None

    async def list_all(self) -> list[CanonicalItem]:
        result = await self.db.execute(
            select(CanonicalItem).order_by(CanonicalItem.name)
        )
        return list(result.scalars().all())

    async def create(self, item: CanonicalItem) -> CanonicalItem:
        self.db.add(item)
        await self.db.flush()
        return item

    async def update(self, item: CanonicalItem) -> None:
        await self.db.flush()
