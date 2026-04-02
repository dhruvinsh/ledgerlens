from pydantic import BaseModel

from app.schemas.item import CanonicalItemResponse


class MatchSuggestionResponse(BaseModel):
    id: str
    line_item_id: str
    line_item_name: str | None = None
    line_item_raw_name: str | None = None
    canonical_item_id: str
    canonical_item: CanonicalItemResponse | None = None
    confidence: float
    status: str
    created_at: str
    resolved_at: str | None

    model_config = {"from_attributes": True}
