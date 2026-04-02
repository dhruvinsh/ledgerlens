from pydantic import BaseModel


class ReviewCountsResponse(BaseModel):
    match_suggestions: int
    store_merges: int
