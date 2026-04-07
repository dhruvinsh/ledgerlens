from datetime import date

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.pagination import paginate

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
        chain: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Receipt], int]:
        if chain:
            # Use selectinload to avoid conflict with explicit join for chain filter
            query = (
                select(Receipt)
                .options(selectinload(Receipt.store))
                .join(Store, Receipt.store_id == Store.id)
                .where(visibility, func.lower(Store.chain) == chain.lower())
            )
        else:
            query = select(Receipt).options(joinedload(Receipt.store)).where(visibility)

        if status:
            query = query.where(Receipt.status == status)
        if store_id:
            query = query.where(Receipt.store_id == store_id)
        if date_from:
            query = query.where(Receipt.transaction_date >= date.fromisoformat(date_from))
        if date_to:
            query = query.where(Receipt.transaction_date <= date.fromisoformat(date_to))

        # Sort — whitelist prevents arbitrary attribute access on the model
        _SORT_COLUMNS = {
            "created_at": Receipt.created_at,
            "transaction_date": Receipt.transaction_date,
            "total": Receipt.total,
        }
        sort_col = _SORT_COLUMNS.get(sort_by, Receipt.created_at)
        if sort_dir == "asc":
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())

        return await paginate(self.db, query, page, per_page)

    async def create(self, receipt: Receipt) -> Receipt:
        self.db.add(receipt)
        await self.db.flush()
        return receipt

    async def update(self, receipt: Receipt) -> None:
        await self.db.flush()

    async def hard_delete(self, receipt: Receipt) -> None:
        await self.db.delete(receipt)
        await self.db.flush()
