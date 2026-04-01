from pydantic import BaseModel


class ModelConfigCreate(BaseModel):
    name: str
    provider_type: str
    base_url: str
    model_name: str
    api_key: str | None = None
    is_active: bool = False
    timeout_seconds: int = 30
    max_retries: int = 1


class ModelConfigUpdate(BaseModel):
    name: str | None = None
    provider_type: str | None = None
    base_url: str | None = None
    model_name: str | None = None
    api_key: str | None = None
    is_active: bool | None = None
    timeout_seconds: int | None = None
    max_retries: int | None = None


class ModelConfigResponse(BaseModel):
    id: str
    name: str
    provider_type: str
    base_url: str
    model_name: str
    is_active: bool
    timeout_seconds: int
    max_retries: int
    health_status: str | None
    last_health_check: str | None
    created_at: str

    model_config = {"from_attributes": True}
