from pydantic import BaseModel


class StoreResponse(BaseModel):
    id: str
    name: str
    address: str | None
    chain: str | None
    latitude: float | None
    longitude: float | None
    is_verified: bool
    merged_into_id: str | None = None
    aliases: list[str] = []
    receipt_count: int = 0
    created_at: str

    model_config = {"from_attributes": True}


class StoreUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    chain: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_verified: bool | None = None


class StoreAliasResponse(BaseModel):
    id: str
    store_id: str
    alias_name: str
    source: str
    created_at: str

    model_config = {"from_attributes": True}


class StoreAliasCreate(BaseModel):
    alias_name: str


class StoreMergeRequest(BaseModel):
    duplicate_ids: list[str]


class StoreMergeSuggestionResponse(BaseModel):
    id: str
    store_a: StoreResponse
    store_b: StoreResponse
    confidence: float
    status: str
    created_at: str

    model_config = {"from_attributes": True}
