from datetime import date

from sqlalchemy import ColumnElement, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.canonical_item import CanonicalItem
from app.models.line_item import LineItem
from app.models.receipt import Receipt
from app.models.store import Store
from app.models.user import User
from app.schemas.dashboard import (
    DashboardSummary,
    SpendingByCategory,
    SpendingByMonth,
    SpendingByStore,
)
from app.services.scope import receipt_visibility


class DashboardService:
    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user
        self.vis = receipt_visibility(user)

    async def get_summary(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> DashboardSummary:
        query = (
            select(
                func.count(Receipt.id).label("count"),
                func.coalesce(func.sum(Receipt.total), 0).label("total"),
            )
            .where(self.vis, Receipt.status.in_(["processed", "reviewed"]))
        )
        query = self._apply_date_filters(query, date_from, date_to)
        result = await self.db.execute(query)
        row = result.one()

        # Count distinct items
        item_query = (
            select(func.count(func.distinct(LineItem.canonical_item_id)))
            .join(Receipt, LineItem.receipt_id == Receipt.id)
            .where(self.vis, Receipt.status.in_(["processed", "reviewed"]))
        )
        total_items = (await self.db.execute(item_query)).scalar() or 0

        # Count distinct stores
        store_query = (
            select(func.count(func.distinct(Receipt.store_id)))
            .where(self.vis, Receipt.status.in_(["processed", "reviewed"]), Receipt.store_id.isnot(None))
        )
        total_stores = (await self.db.execute(store_query)).scalar() or 0

        receipt_count = row.count or 0
        total_spent = row.total or 0

        return DashboardSummary(
            total_receipts=receipt_count,
            total_spent=total_spent,
            total_items=total_items,
            total_stores=total_stores,
            avg_receipt_total=total_spent // receipt_count if receipt_count > 0 else 0,
        )

    async def spending_by_store(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[SpendingByStore]:
        query = (
            select(
                Store.id,
                Store.name,
                func.coalesce(func.sum(Receipt.total), 0).label("total"),
                func.count(Receipt.id).label("count"),
            )
            .join(Store, Receipt.store_id == Store.id)
            .where(self.vis, Receipt.status.in_(["processed", "reviewed"]))
            .group_by(Store.id, Store.name)
            .order_by(func.sum(Receipt.total).desc())
        )
        query = self._apply_date_filters(query, date_from, date_to)
        result = await self.db.execute(query)

        return [
            SpendingByStore(
                store_id=row.id,
                store_name=row.name,
                total=row.total,
                receipt_count=row.count,
            )
            for row in result.all()
        ]

    async def spending_by_month(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[SpendingByMonth]:
        # Use strftime for SQLite compatibility
        month_expr = func.strftime("%Y-%m", Receipt.transaction_date)
        query = (
            select(
                month_expr.label("month"),
                func.coalesce(func.sum(Receipt.total), 0).label("total"),
                func.count(Receipt.id).label("count"),
            )
            .where(
                self.vis,
                Receipt.status.in_(["processed", "reviewed"]),
                Receipt.transaction_date.isnot(None),
            )
            .group_by(month_expr)
            .order_by(month_expr.asc())
        )
        query = self._apply_date_filters(query, date_from, date_to)
        result = await self.db.execute(query)

        return [
            SpendingByMonth(month=row.month, total=row.total, receipt_count=row.count)
            for row in result.all()
        ]

    async def spending_by_category(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[SpendingByCategory]:
        cat_expr = func.coalesce(CanonicalItem.category, "Uncategorized")
        query = (
            select(
                cat_expr.label("category"),
                func.coalesce(func.sum(LineItem.total_price), 0).label("total"),
                func.count(LineItem.id).label("count"),
            )
            .join(Receipt, LineItem.receipt_id == Receipt.id)
            .outerjoin(CanonicalItem, LineItem.canonical_item_id == CanonicalItem.id)
            .where(self.vis, Receipt.status.in_(["processed", "reviewed"]))
            .group_by(cat_expr)
            .order_by(func.sum(LineItem.total_price).desc())
        )
        if date_from:
            query = query.where(Receipt.transaction_date >= date.fromisoformat(date_from))
        if date_to:
            query = query.where(Receipt.transaction_date <= date.fromisoformat(date_to))

        result = await self.db.execute(query)
        return [
            SpendingByCategory(category=row.category, total=row.total, item_count=row.count)
            for row in result.all()
        ]

    def _apply_date_filters(self, query, date_from: str | None, date_to: str | None):  # type: ignore[no-untyped-def]
        if date_from:
            query = query.where(Receipt.transaction_date >= date.fromisoformat(date_from))
        if date_to:
            query = query.where(Receipt.transaction_date <= date.fromisoformat(date_to))
        return query
