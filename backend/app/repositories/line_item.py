import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.line_item import LineItem


class LineItemRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, item_id: str) -> LineItem | None:
        result = await self.db.execute(
            select(LineItem).where(LineItem.id == item_id)
        )
        return result.scalar_one_or_none()

    async def create(self, line_item: LineItem) -> LineItem:
        if not line_item.id:
            line_item.id = str(uuid.uuid4())
        self.db.add(line_item)
        await self.db.flush()
        return line_item

    async def create_many(self, items: list[LineItem]) -> list[LineItem]:
        for i, item in enumerate(items):
            if not item.id:
                item.id = str(uuid.uuid4())
            item.position = i
            self.db.add(item)
        await self.db.flush()
        return items

    async def delete_by_receipt_id(self, receipt_id: str) -> None:
        await self.db.execute(
            delete(LineItem).where(LineItem.receipt_id == receipt_id)
        )

    async def update(self, line_item: LineItem) -> None:
        await self.db.flush()
