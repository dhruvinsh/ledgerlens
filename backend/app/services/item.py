from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.exceptions import ItemNotFoundError, ValidationError
from app.models.canonical_item import CanonicalItem
from app.models.line_item import LineItem
from app.models.match_suggestion import MatchSuggestion
from app.models.receipt import Receipt
from app.models.store import Store
from app.repositories.canonical_item import CanonicalItemRepository
from app.schemas.item import CanonicalItemUpdate, PricePoint
from app.services import storage


class ItemService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CanonicalItemRepository(db)

    async def get_by_id(self, item_id: str) -> CanonicalItem:
        item = await self.repo.get_by_id(item_id)
        if not item:
            raise ItemNotFoundError(f"Item {item_id} not found")
        return item

    async def list_items(
        self,
        search: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[CanonicalItem], int]:
        from sqlalchemy import func

        query = select(CanonicalItem)
        if search:
            query = query.where(CanonicalItem.name.ilike(f"%{search}%"))

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        query = query.order_by(CanonicalItem.name)
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def update(self, item_id: str, data: CanonicalItemUpdate) -> CanonicalItem:
        item = await self.get_by_id(item_id)

        if data.name is not None and data.name != item.name:
            old_name = item.name
            existing = [a.lower() for a in (item.aliases or [])]
            if old_name.lower() not in existing:
                item.aliases = (item.aliases or []) + [old_name]
            item.name = data.name
        if data.category is not None:
            item.category = data.category
        if data.product_url is not None:
            item.product_url = data.product_url
        if data.aliases is not None:
            item.aliases = data.aliases

        await self.repo.update(item)
        await self.db.commit()
        return item

    async def delete(self, item_id: str) -> None:
        item = await self.get_by_id(item_id)
        if item.image_path:
            storage.delete_product_image(item.id)
        await self.db.delete(item)
        await self.db.commit()

    async def merge_items(
        self, canonical_id: str, duplicate_ids: list[str]
    ) -> CanonicalItem:
        canonical = await self.get_by_id(canonical_id)

        for dup_id in duplicate_ids:
            if dup_id == canonical_id:
                raise ValidationError("Cannot merge an item into itself")

            dup = await self.get_by_id(dup_id)

            # Reassign all line items from duplicate to canonical
            await self.db.execute(
                update(LineItem)
                .where(LineItem.canonical_item_id == dup_id)
                .values(canonical_item_id=canonical_id)
            )

            # Union aliases: dup's aliases + dup's name → canonical's aliases
            existing = [a.lower() for a in (canonical.aliases or [])]
            new_aliases = list(canonical.aliases or [])
            for alias in (dup.aliases or []) + [dup.name]:
                if alias.lower() not in existing and alias.lower() != canonical.name.lower():
                    new_aliases.append(alias)
                    existing.append(alias.lower())
            canonical.aliases = new_aliases

            # Adopt category if canonical lacks one
            if not canonical.category and dup.category:
                canonical.category = dup.category

            # Adopt image if canonical lacks one
            if not canonical.image_path and dup.image_path:
                canonical.image_path = dup.image_path
                canonical.image_source = dup.image_source
                canonical.image_fetch_status = dup.image_fetch_status

            # Delete all match suggestions referencing the duplicate
            await self.db.execute(
                delete(MatchSuggestion).where(
                    MatchSuggestion.canonical_item_id == dup_id
                )
            )

            # Hard-delete the duplicate (image cleanup only if we didn't adopt it)
            if dup.image_path and dup.image_path != canonical.image_path:
                storage.delete_product_image(dup.id)
            await self.db.delete(dup)

        await self.db.flush()
        return canonical

    async def upload_image(
        self, item_id: str, file_content: bytes, filename: str
    ) -> CanonicalItem:
        item = await self.get_by_id(item_id)
        relative_path = await storage.save_product_image(file_content, filename, item_id)
        item.image_path = relative_path
        item.image_source = "user"
        item.image_fetch_status = None
        await self.repo.update(item)
        await self.db.commit()
        return item

    async def delete_image(self, item_id: str) -> CanonicalItem:
        item = await self.get_by_id(item_id)
        if item.image_path:
            storage.delete_product_image(item.id)
        item.image_path = None
        item.image_source = None
        item.image_fetch_status = None
        await self.repo.update(item)
        await self.db.commit()
        return item

    async def get_price_history(
        self,
        item_id: str,
        store_ids: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[PricePoint]:
        from datetime import date

        item = await self.get_by_id(item_id)

        query = (
            select(LineItem, Receipt, Store)
            .join(Receipt, LineItem.receipt_id == Receipt.id)
            .outerjoin(Store, Receipt.store_id == Store.id)
            .where(
                LineItem.canonical_item_id == item_id,
                LineItem.total_price.isnot(None),
                Receipt.transaction_date.isnot(None),
                Receipt.status.in_(["processed", "reviewed"]),
            )
        )

        if store_ids:
            query = query.where(Receipt.store_id.in_(store_ids))
        if date_from:
            query = query.where(Receipt.transaction_date >= date.fromisoformat(date_from))
        if date_to:
            query = query.where(Receipt.transaction_date <= date.fromisoformat(date_to))

        query = query.order_by(Receipt.transaction_date.asc())
        result = await self.db.execute(query)
        rows = result.all()

        return [
            PricePoint(
                date=receipt.transaction_date.isoformat(),
                price=li.total_price,
                store_name=store.name if store else "Unknown",
                receipt_id=receipt.id,
            )
            for li, receipt, store in rows
            if li.total_price is not None and receipt.transaction_date is not None
        ]
