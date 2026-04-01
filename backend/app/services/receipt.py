from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, ReceiptNotFoundError
from app.models.line_item import LineItem
from app.models.receipt import Receipt
from app.models.store import Store
from app.models.user import User
from app.repositories.line_item import LineItemRepository
from app.repositories.receipt import ReceiptRepository
from app.repositories.store import StoreRepository
from app.schemas.receipt import (
    LineItemCreate,
    ManualReceiptCreate,
    ReceiptFilters,
    ReceiptUpdate,
)
from app.services import storage
from app.services.scope import receipt_visibility


class ReceiptService:
    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user
        self.repo = ReceiptRepository(db)
        self.store_repo = StoreRepository(db)
        self.line_item_repo = LineItemRepository(db)

    async def upload(self, file_content: bytes, filename: str, source: str) -> Receipt:
        receipt = Receipt(
            user_id=self.user.id,
            household_id=self.user.household_id,
            source=source,
            status="pending",
        )
        await self.repo.create(receipt)

        file_path, thumb, pages = await storage.save_receipt_file(
            file_content, filename, self.user.id, receipt.id
        )
        receipt.file_path = file_path
        receipt.thumbnail_path = thumb
        receipt.page_count = pages
        await self.db.commit()

        # Dispatch processing
        from app.services.processing import enqueue_receipt

        await enqueue_receipt(receipt.id, self.db)
        return receipt

    async def create_manual(self, data: ManualReceiptCreate) -> Receipt:
        store = None
        if data.store_name:
            store = await self.store_repo.get_by_name(data.store_name)
            if not store:
                store = Store(
                    name=data.store_name,
                    created_by=self.user.id,
                )
                await self.store_repo.create(store)

        receipt = Receipt(
            user_id=self.user.id,
            household_id=self.user.household_id,
            store_id=store.id if store else None,
            transaction_date=(
                date.fromisoformat(data.transaction_date)
                if data.transaction_date
                else None
            ),
            currency=data.currency,
            subtotal=data.subtotal,
            tax=data.tax,
            total=data.total,
            notes=data.notes,
            source="manual",
            status="processed",
        )
        await self.repo.create(receipt)

        if data.line_items:
            items = [
                LineItem(
                    receipt_id=receipt.id,
                    name=li.name,
                    quantity=li.quantity,
                    unit_price=li.unit_price,
                    total_price=li.total_price,
                )
                for li in data.line_items
            ]
            await self.line_item_repo.create_many(items)

        await self.db.commit()

        # Re-fetch with relationships
        loaded = await self.repo.get_by_id(receipt.id)
        assert loaded is not None
        return loaded

    async def get_detail(self, receipt_id: str) -> Receipt:
        vis = receipt_visibility(self.user)
        receipt = await self.repo.get_for_user(receipt_id, vis)
        if not receipt:
            raise ReceiptNotFoundError(f"Receipt {receipt_id} not found")
        return receipt

    async def list_receipts(self, filters: ReceiptFilters) -> tuple[list[Receipt], int]:
        vis = receipt_visibility(self.user)
        return await self.repo.list_paginated(
            visibility=vis,
            status=filters.status,
            store_id=filters.store_id,
            date_from=filters.date_from,
            date_to=filters.date_to,
            sort_by=filters.sort_by,
            sort_dir=filters.sort_dir,
            page=filters.page,
            per_page=filters.per_page,
        )

    async def update(self, receipt_id: str, data: ReceiptUpdate) -> Receipt:
        receipt = await self.get_detail(receipt_id)
        self._require_owner(receipt)

        if data.transaction_date is not None:
            receipt.transaction_date = date.fromisoformat(data.transaction_date)
        if data.currency is not None:
            receipt.currency = data.currency
        if data.subtotal is not None:
            receipt.subtotal = data.subtotal
        if data.tax is not None:
            receipt.tax = data.tax
        if data.total is not None:
            receipt.total = data.total
        if data.notes is not None:
            receipt.notes = data.notes
        if data.status is not None:
            receipt.status = data.status

        await self.repo.update(receipt)
        await self.db.commit()
        return receipt

    async def delete(self, receipt_id: str) -> None:
        receipt = await self.get_detail(receipt_id)
        self._require_owner(receipt)

        await self.repo.soft_delete(receipt)
        if receipt.file_path:
            storage.delete_receipt_files(self.user.id, receipt.id)
        await self.db.commit()

    def _require_owner(self, receipt: Receipt) -> None:
        if receipt.user_id != self.user.id:
            raise ForbiddenError("You can only modify your own receipts")
