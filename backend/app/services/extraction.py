import logging
import uuid
from datetime import date
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.line_item import LineItem
from app.models.receipt import Receipt
from app.repositories.canonical_item import CanonicalItemRepository
from app.repositories.line_item import LineItemRepository
from app.repositories.store import StoreRepository
from app.services import heuristic as heuristic_svc
from app.services import llm as llm_svc
from app.services import ocr as ocr_svc
from app.services.matching import MatchingService
from app.services.normalization import normalize_item_name
from app.services.storage import get_receipt_path
from app.services.store_matching import StoreMatchingService

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

    # ── Gather known entities for LLM context ──
    store_repo = StoreRepository(db)
    item_repo = CanonicalItemRepository(db)

    existing_stores = await store_repo.list_all()
    known_stores = [s.name for s in existing_stores]

    all_items = await item_repo.list_all()
    known_products = [item.name for item in all_items]

    # ── LLM extraction ──
    data = llm_svc.extract_receipt_data(
        raw_text,
        base_url=model_base_url,
        model_name=model_name,
        api_key=model_api_key,
        timeout=model_timeout,
        max_retries=model_max_retries,
        known_stores=known_stores,
        known_products=known_products,
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

    # ── Normalize & match store ──
    store_name = data.get("store_name")
    raw_store_name = data.get("raw_store_name") or store_name
    if store_name:
        store_matching_svc = StoreMatchingService(db)
        store = await store_matching_svc.find_or_create_store(
            raw_name=raw_store_name or store_name,
            address=data.get("store_address"),
            chain=data.get("store_chain"),
            created_by=receipt.user_id,
        )
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
    receipt.discount = data.get("discount_total_cents")
    receipt.payment_method = data.get("payment_method")
    receipt.is_refund = data.get("is_refund_receipt", False)

    # ── Delete existing line items and create new ones ──
    line_item_repo = LineItemRepository(db)
    await line_item_repo.delete_by_receipt_id(receipt.id)

    matching_svc = MatchingService(db)
    raw_items = data.get("line_items", [])

    for i, raw_item in enumerate(raw_items):
        raw_name = raw_item.get("raw_name")
        clean_name = raw_item.get("name", "Unknown")

        li = LineItem(
            id=str(uuid.uuid4()),
            receipt_id=receipt.id,
            name=clean_name,
            raw_name=raw_name,
            quantity=raw_item.get("quantity", 1.0),
            unit_price=raw_item.get("unit_price_cents"),
            total_price=raw_item.get("total_price_cents"),
            discount=raw_item.get("discount_cents"),
            is_refund=raw_item.get("is_refund", False),
            tax_code=raw_item.get("tax_code"),
            weight_qty=raw_item.get("weight_qty"),
            position=i,
        )
        db.add(li)
        await db.flush()

        # Match to canonical item
        canonical = await matching_svc.find_or_create_canonical_item(clean_name, li)

        # Alias seeding: if raw OCR name differs from canonical, add it as an alias
        if canonical and raw_name:
            normalized_raw = normalize_item_name(raw_name)
            if normalized_raw.lower() != canonical.name.lower():
                existing_aliases = [a.lower() for a in (canonical.aliases or [])]
                if normalized_raw.lower() not in existing_aliases:
                    canonical.aliases = (canonical.aliases or []) + [normalized_raw]
                    await item_repo.update(canonical)

    receipt.status = "processed"
