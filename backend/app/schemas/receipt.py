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
    quantity: float
    unit_price: int | None
    total_price: int | None
    confidence: float | None
    position: int
    is_corrected: bool

    model_config = {"from_attributes": True}


class LineItemCreate(BaseModel):
    name: str
    quantity: float = 1.0
    unit_price: int | None = None
    total_price: int | None = None


class LineItemUpdate(BaseModel):
    name: str | None = None
    quantity: float | None = None
    unit_price: int | None = None
    total_price: int | None = None
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


class ReceiptDetail(BaseModel):
    id: str
    user_id: str
    store: StoreInfo | None
    transaction_date: str | None
    currency: str
    subtotal: int | None
    tax: int | None
    total: int | None
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
    notes: str | None = None
    line_items: list[LineItemCreate] = []


class ReceiptUpdate(BaseModel):
    transaction_date: str | None = None
    currency: str | None = None
    subtotal: int | None = None
    tax: int | None = None
    total: int | None = None
    notes: str | None = None
    status: str | None = None


class ReceiptFilters(BaseModel):
    status: str | None = None
    store_id: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    sort_by: str = "created_at"
    sort_dir: str = "desc"
    page: int = 1
    per_page: int = 20
