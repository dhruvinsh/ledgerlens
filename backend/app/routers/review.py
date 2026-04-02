from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.user import User
from app.repositories.match_suggestion import MatchSuggestionRepository
from app.repositories.store_merge_suggestion import StoreMergeSuggestionRepository
from app.schemas.review import ReviewCountsResponse

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/counts", response_model=ReviewCountsResponse)
async def get_review_counts(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ReviewCountsResponse:
    match_count = await MatchSuggestionRepository(db).pending_count()
    store_count = await StoreMergeSuggestionRepository(db).pending_count()
    return ReviewCountsResponse(
        match_suggestions=match_count,
        store_merges=store_count,
    )
