import logging
import uuid
from datetime import date
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.line_item import LineItem
from app.models.receipt import Receipt
from app.models.store import Store
from app.repositories.line_item import LineItemRepository
from app.repositories.store import StoreRepository
from app.services import heuristic as heuristic_svc
from app.services import llm as llm_svc
from app.services import ocr as ocr_svc
from app.services.matching import MatchingService
from app.services.normalization import normalize_store_name
from app.services.storage import get_receipt_path

logger = logging.getLogger(__name__)


async def run_extraction(
    receipt: Receipt,
    db: AsyncSession,
    model_base_url: str | None = None,
    model_name: str | None = None,
    model_api_key: str | None = None,
    model_timeout: int | None = None,
    model_max_retries: int | None = None,
) -> None:
    """Full extraction pipeline: OCR → LLM/heuristic → normalize → persist.

    Modifies the receipt and creates line items in the database.
    Caller is responsible for committing.
    """
    if not receipt.file_path:
        raise ValueError("Receipt has no file to process")

    file_path = str(get_receipt_path(receipt.file_path))
    ext = Path(file_path).suffix.lower()

    # ── OCR ──
    if ext == ".pdf":
        raw_text, confidence, page_count = ocr_svc._ocr_pdf(file_path)
        receipt.page_count = page_count
    else:
        raw_text, confidence = ocr_svc._ocr_image(file_path)

    receipt.raw_ocr_text = raw_text
    receipt.ocr_confidence = confidence

    if not raw_text.strip():
        logger.warning("OCR produced no text for receipt %s", receipt.id)
        receipt.status = "failed"
        return

    # ── LLM extraction ──
    data = llm_svc.extract_receipt_data(
        raw_text,
        base_url=model_base_url,
        model_name=model_name,
        api_key=model_api_key,
        timeout=model_timeout,
        max_retries=model_max_retries,
    )

    # Fall back to heuristic if LLM returned nothing usable
    if not data or not data.get("total_cents"):
        if not data:
            logger.warning(
                "LLM returned no data for receipt %s — falling back to heuristic",
                receipt.id,
            )
        else:
            logger.warning(
                "LLM returned data without total_cents for receipt %s — falling back to heuristic",
                receipt.id,
            )
        data = heuristic_svc.extract_receipt_data(raw_text)
        receipt.extraction_source = "heuristic"
    else:
        logger.info("LLM extraction successful for receipt %s", receipt.id)
        receipt.extraction_source = "llm"

    # ── Normalize store ──
    store_repo = StoreRepository(db)
    if data.get("store_name"):
        store_name = normalize_store_name(data["store_name"])
        store = await store_repo.get_by_name(store_name)
        if not store:
            store = Store(
                name=store_name,
                address=data.get("store_address"),
                created_by=receipt.user_id,
            )
            await store_repo.create(store)
        receipt.store_id = store.id

    # ── Set receipt fields ──
    if data.get("transaction_date"):
        try:
            receipt.transaction_date = date.fromisoformat(data["transaction_date"])
        except ValueError:
            pass

    if data.get("currency"):
        receipt.currency = data["currency"]

    receipt.subtotal = data.get("subtotal_cents")
    receipt.tax = data.get("tax_cents")
    receipt.total = data.get("total_cents")

    # ── Delete existing line items and create new ones ──
    line_item_repo = LineItemRepository(db)
    await line_item_repo.delete_by_receipt_id(receipt.id)

    matching_svc = MatchingService(db)
    raw_items = data.get("line_items", [])

    for i, raw_item in enumerate(raw_items):
        li = LineItem(
            id=str(uuid.uuid4()),
            receipt_id=receipt.id,
            name=raw_item.get("name", "Unknown"),
            quantity=raw_item.get("quantity", 1.0),
            unit_price=raw_item.get("unit_price_cents"),
            total_price=raw_item.get("total_price_cents"),
            position=i,
        )
        db.add(li)
        await db.flush()

        # Match to canonical item
        await matching_svc.find_or_create_canonical_item(li.name, li)

    receipt.status = "processed"
