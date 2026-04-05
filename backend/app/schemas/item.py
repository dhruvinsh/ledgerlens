from pydantic import BaseModel


class CanonicalItemResponse(BaseModel):
    id: str
    name: str
    category: str | None
    aliases: list[str]
    product_url: str | None
    image_path: str | None
    image_source: str | None
    image_fetch_status: str | None
    created_at: str
    receipt_count: int = 0

    model_config = {"from_attributes": True}


class CanonicalItemUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    product_url: str | None = None
    aliases: list[str] | None = None


class ItemMergeRequest(BaseModel):
    duplicate_ids: list[str]


class PricePoint(BaseModel):
    date: str
    price: int
    store_name: str
    receipt_id: str


class PriceHistoryResponse(BaseModel):
    item: CanonicalItemResponse
    data_points: list[PricePoint]
