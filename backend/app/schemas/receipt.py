from pydantic import BaseModel


class CanonicalItemSummary(BaseModel):
    id: str
    name: str
    category: str | None
    aliases: list[str]
    product_url: str | None
    image_path: str | None

    model_config = {"from_attributes": True}


class LineItemResponse(BaseModel):
    id: str
    receipt_id: str
    canonical_item_id: str | None
    canonical_item: CanonicalItemSummary | None = None
    name: str
    raw_name: str | None = None
    quantity: float
    unit_price: int | None
    total_price: int | None
    discount: int | None = None
    is_refund: bool = False
    tax_code: str | None = None
    weight_qty: str | None = None
    confidence: float | None
    position: int
    is_corrected: bool

    model_config = {"from_attributes": True}


class LineItemCreate(BaseModel):
    name: str
    quantity: float = 1.0
    unit_price: int | None = None
    total_price: int | None = None
    discount: int | None = None
    is_refund: bool = False
    tax_code: str | None = None
    weight_qty: str | None = None


class LineItemUpdate(BaseModel):
    name: str | None = None
    quantity: float | None = None
    unit_price: int | None = None
    total_price: int | None = None
    discount: int | None = None
    is_refund: bool | None = None
    tax_code: str | None = None
    weight_qty: str | None = None
    canonical_item_id: str | None = None


class StoreInfo(BaseModel):
    id: str
    name: str
    chain: str | None

    model_config = {"from_attributes": True}


class ReceiptListItem(BaseModel):
    id: str
    user_id: str
    store: StoreInfo | None
    transaction_date: str | None
    currency: str
    total: int | None
    source: str
    status: str
    thumbnail_path: str | None
    page_count: int
    created_at: str

    model_config = {"from_attributes": True}


def receipt_to_list_item(r: object) -> ReceiptListItem:
    """Convert a Receipt ORM object to a ReceiptListItem schema.

    Centralised here because routers/receipts.py, routers/items.py, and
    routers/stores.py all need the same transformation.
    """
    store = getattr(r, "store", None)
    transaction_date = getattr(r, "transaction_date", None)
    return ReceiptListItem(
        id=r.id,  # type: ignore[attr-defined]
        user_id=r.user_id,  # type: ignore[attr-defined]
        store=StoreInfo(id=store.id, name=store.name, chain=store.chain) if store else None,
        transaction_date=transaction_date.isoformat() if transaction_date else None,
        currency=r.currency,  # type: ignore[attr-defined]
        total=r.total,  # type: ignore[attr-defined]
        source=r.source,  # type: ignore[attr-defined]
        status=r.status,  # type: ignore[attr-defined]
        thumbnail_path=r.thumbnail_path,  # type: ignore[attr-defined]
        page_count=r.page_count,  # type: ignore[attr-defined]
        created_at=r.created_at.isoformat(),  # type: ignore[attr-defined]
    )


class ReceiptDetail(BaseModel):
    id: str
    user_id: str
    store: StoreInfo | None
    transaction_date: str | None
    currency: str
    subtotal: int | None
    tax: int | None
    total: int | None
    discount: int | None = None
    payment_method: str | None = None
    is_refund: bool = False
    source: str
    status: str
    file_path: str | None
    thumbnail_path: str | None
    page_count: int
    ocr_confidence: float | None
    extraction_source: str | None
    raw_ocr_text: str | None
    duplicate_of: str | None
    notes: str | None
    line_items: list[LineItemResponse]
    created_at: str

    model_config = {"from_attributes": True}


class ManualReceiptCreate(BaseModel):
    store_name: str | None = None
    transaction_date: str | None = None
    currency: str = "CAD"
    subtotal: int | None = None
    tax: int | None = None
    total: int | None = None
    discount: int | None = None
    payment_method: str | None = None
    is_refund: bool = False
    notes: str | None = None
    line_items: list[LineItemCreate] = []


class ReceiptUpdate(BaseModel):
    transaction_date: str | None = None
    currency: str | None = None
    subtotal: int | None = None
    tax: int | None = None
    total: int | None = None
    discount: int | None = None
    payment_method: str | None = None
    is_refund: bool | None = None
    notes: str | None = None
    status: str | None = None


class BatchUploadError(BaseModel):
    filename: str
    detail: str


class BatchUploadResponse(BaseModel):
    receipts: list[ReceiptListItem]
    errors: list[BatchUploadError]


class ReceiptFilters(BaseModel):
    status: str | None = None
    store_id: str | None = None
    chain: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    sort_by: str = "created_at"
    sort_dir: str = "desc"
    page: int = 1
    per_page: int = 20
