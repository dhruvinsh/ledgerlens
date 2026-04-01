from pydantic import BaseModel


class StoreResponse(BaseModel):
    id: str
    name: str
    address: str | None
    chain: str | None
    latitude: float | None
    longitude: float | None
    is_verified: bool
    created_at: str

    model_config = {"from_attributes": True}


class StoreUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    chain: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_verified: bool | None = None
