import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.time import utc_now
from app.models.store import Store
from app.models.store_merge_suggestion import StoreMergeSuggestion


class StoreMergeSuggestionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, suggestion_id: str) -> StoreMergeSuggestion | None:
        result = await self.db.execute(
            select(StoreMergeSuggestion)
            .options(
                joinedload(StoreMergeSuggestion.store_a).selectinload(Store.aliases),
                joinedload(StoreMergeSuggestion.store_b).selectinload(Store.aliases),
            )
            .where(StoreMergeSuggestion.id == suggestion_id)
        )
        return result.unique().scalar_one_or_none()

    async def list_pending(
        self, page: int = 1, per_page: int = 20
    ) -> tuple[list[StoreMergeSuggestion], int]:
        from app.core.pagination import paginate

        query = (
            select(StoreMergeSuggestion)
            .where(StoreMergeSuggestion.status == "pending")
            .options(
                joinedload(StoreMergeSuggestion.store_a).selectinload(Store.aliases),
                joinedload(StoreMergeSuggestion.store_b).selectinload(Store.aliases),
            )
            .order_by(StoreMergeSuggestion.confidence.desc())
        )
        return await paginate(self.db, query, page, per_page)

    async def exists_for_pair(self, store_a_id: str, store_b_id: str) -> bool:
        """Check if a suggestion already exists for this pair (in either direction)."""
        result = await self.db.execute(
            select(func.count()).select_from(StoreMergeSuggestion).where(
                or_(
                    (StoreMergeSuggestion.store_a_id == store_a_id)
                    & (StoreMergeSuggestion.store_b_id == store_b_id),
                    (StoreMergeSuggestion.store_a_id == store_b_id)
                    & (StoreMergeSuggestion.store_b_id == store_a_id),
                )
            )
        )
        return (result.scalar() or 0) > 0

    async def create(
        self, store_a_id: str, store_b_id: str, confidence: float
    ) -> StoreMergeSuggestion:
        suggestion = StoreMergeSuggestion(
            id=str(uuid.uuid4()),
            store_a_id=store_a_id,
            store_b_id=store_b_id,
            confidence=confidence,
            status="pending",
        )
        self.db.add(suggestion)
        await self.db.flush()
        return suggestion

    async def accept(self, suggestion_id: str, user_id: str) -> None:
        result = await self.db.execute(
            select(StoreMergeSuggestion).where(StoreMergeSuggestion.id == suggestion_id)
        )
        suggestion = result.scalar_one()
        suggestion.status = "accepted"
        suggestion.resolved_at = utc_now()
        suggestion.resolved_by = user_id
        await self.db.flush()

    async def reject(self, suggestion_id: str, user_id: str) -> None:
        result = await self.db.execute(
            select(StoreMergeSuggestion).where(StoreMergeSuggestion.id == suggestion_id)
        )
        suggestion = result.scalar_one()
        suggestion.status = "rejected"
        suggestion.resolved_at = utc_now()
        suggestion.resolved_by = user_id
        await self.db.flush()

    async def pending_count(self) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(StoreMergeSuggestion).where(
                StoreMergeSuggestion.status == "pending"
            )
        )
        return result.scalar() or 0
