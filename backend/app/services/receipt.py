import logging
from datetime import date

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, ReceiptNotFoundError
from app.models.line_item import LineItem
from app.models.receipt import Receipt
from app.models.user import User
from app.repositories.line_item import LineItemRepository
from app.repositories.receipt import ReceiptRepository
from app.schemas.receipt import (
    ManualReceiptCreate,
    ReceiptFilters,
    ReceiptUpdate,
)
from app.services import storage
from app.services.scope import receipt_visibility
from app.services.store_matching import StoreMatchingService

logger = logging.getLogger(__name__)

# Batch upload constants
_FILE_SIGNATURES: dict[bytes, str] = {
    b"\x25\x50\x44\x46": "application/pdf",  # %PDF
    b"\xff\xd8\xff": "image/jpeg",  # JPEG
    b"\x89\x50\x4e\x47": "image/png",  # PNG
}
_ALLOWED_BATCH_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}
_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB per file
_MAX_BATCH_TOTAL_SIZE = 50 * 1024 * 1024  # 50 MB aggregate


def _validate_magic_bytes(content: bytes) -> str | None:
    """Return detected content type or None if unrecognized."""
    for sig, ctype in _FILE_SIGNATURES.items():
        if content[: len(sig)] == sig:
            return ctype
    return None


class ReceiptService:
    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user
        self.repo = ReceiptRepository(db)
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

    async def upload_batch(
        self, files: list[UploadFile], source: str
    ) -> tuple[list[Receipt], list[dict[str, str]]]:
        """Upload multiple receipt files. Returns (receipts, errors) for partial success."""
        receipts: list[Receipt] = []
        errors: list[dict[str, str]] = []
        accepted_bytes = 0

        for f in files:
            filename = f.filename or "upload.jpg"

            # Fast pre-filter on content type (client-supplied, not authoritative)
            if f.content_type not in _ALLOWED_BATCH_CONTENT_TYPES:
                errors.append(
                    {"filename": filename, "detail": f"Unsupported file type: {f.content_type}"}
                )
                continue

            # Read one file at a time — don't buffer all into memory
            content = await f.read()

            # Per-file size limit
            if len(content) > _MAX_FILE_SIZE:
                errors.append({"filename": filename, "detail": "File exceeds 10MB limit"})
                continue

            # Magic byte validation (authoritative — content_type is client-supplied)
            detected = _validate_magic_bytes(content)
            if detected is None:
                errors.append(
                    {"filename": filename, "detail": "File content does not match a supported format"}
                )
                continue

            # Aggregate size — check before adding, increment before upload attempt
            if accepted_bytes + len(content) > _MAX_BATCH_TOTAL_SIZE:
                errors.append({"filename": filename, "detail": "Batch size limit reached"})
                continue
            accepted_bytes += len(content)

            try:
                receipt = await self.upload(content, filename, source)
                receipts.append(receipt)
            except Exception as e:
                logger.warning("Batch upload failed for %s: %s", filename, e)
                errors.append({"filename": filename, "detail": str(e)})

        return receipts, errors

    async def create_manual(self, data: ManualReceiptCreate) -> Receipt:
        store = None
        if data.store_name:
            store_matching_svc = StoreMatchingService(self.db)
            store = await store_matching_svc.find_or_create_store(
                raw_name=data.store_name,
                created_by=self.user.id,
            )

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
            discount=data.discount,
            payment_method=data.payment_method,
            is_refund=data.is_refund,
            notes=data.notes,
            source="manual",
            status="processed",
        )
        await self.repo.create(receipt)

        if data.line_items:
            import uuid

            items = [
                LineItem(
                    id=str(uuid.uuid4()),
                    receipt_id=receipt.id,
                    name=li.name,
                    quantity=li.quantity,
                    unit_price=li.unit_price,
                    total_price=li.total_price,
                    discount=li.discount,
                    is_refund=li.is_refund,
                    tax_code=li.tax_code,
                    weight_qty=li.weight_qty,
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
            chain=filters.chain,
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
        if data.discount is not None:
            receipt.discount = data.discount
        if data.payment_method is not None:
            receipt.payment_method = data.payment_method
        if data.is_refund is not None:
            receipt.is_refund = data.is_refund
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

        if receipt.file_path:
            storage.delete_receipt_files(self.user.id, receipt.id)
        await self.repo.hard_delete(receipt)
        await self.db.commit()

    def _require_owner(self, receipt: Receipt) -> None:
        if receipt.user_id != self.user.id:
            raise ForbiddenError("You can only modify your own receipts")
