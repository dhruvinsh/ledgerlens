from datetime import date

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.line_item import LineItem
from app.models.receipt import Receipt
from app.models.store import Store


class ReceiptRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, receipt_id: str) -> Receipt | None:
        result = await self.db.execute(
            select(Receipt)
            .options(
                joinedload(Receipt.store),
                joinedload(Receipt.line_items).subqueryload(LineItem.canonical_item),
            )
            .where(Receipt.id == receipt_id)
        )
        return result.unique().scalar_one_or_none()

    async def get_for_user(
        self, receipt_id: str, visibility: ColumnElement[bool]
    ) -> Receipt | None:
        result = await self.db.execute(
            select(Receipt)
            .options(
                joinedload(Receipt.store),
                joinedload(Receipt.line_items).subqueryload(LineItem.canonical_item),
            )
            .where(Receipt.id == receipt_id, visibility)
        )
        return result.unique().scalar_one_or_none()

    async def list_paginated(
        self,
        visibility: ColumnElement[bool],
        status: str | None = None,
        store_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Receipt], int]:
        query = select(Receipt).options(joinedload(Receipt.store)).where(visibility)

        if status:
            query = query.where(Receipt.status == status)
        if store_id:
            query = query.where(Receipt.store_id == store_id)
        if date_from:
            query = query.where(Receipt.transaction_date >= date.fromisoformat(date_from))
        if date_to:
            query = query.where(Receipt.transaction_date <= date.fromisoformat(date_to))

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Sort
        sort_col = getattr(Receipt, sort_by, Receipt.created_at)
        if sort_dir == "asc":
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())

        # Paginate
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        receipts = list(result.unique().scalars().all())

        return receipts, total

    async def create(self, receipt: Receipt) -> Receipt:
        self.db.add(receipt)
        await self.db.flush()
        return receipt

    async def update(self, receipt: Receipt) -> None:
        await self.db.flush()

    async def hard_delete(self, receipt: Receipt) -> None:
        await self.db.delete(receipt)
        await self.db.flush()
