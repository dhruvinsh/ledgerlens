from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.time import utc_now
from app.models.match_suggestion import MatchSuggestion


class MatchSuggestionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, suggestion_id: str) -> MatchSuggestion | None:
        result = await self.db.execute(
            select(MatchSuggestion)
            .options(
                joinedload(MatchSuggestion.canonical_item),
                joinedload(MatchSuggestion.line_item),
            )
            .where(MatchSuggestion.id == suggestion_id)
        )
        return result.unique().scalar_one_or_none()

    async def list_pending(
        self, page: int = 1, per_page: int = 20
    ) -> tuple[list[MatchSuggestion], int]:
        from sqlalchemy import func

        base = select(MatchSuggestion).where(MatchSuggestion.status == "pending")

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        query = (
            base.options(
                joinedload(MatchSuggestion.canonical_item),
                joinedload(MatchSuggestion.line_item),
            )
            .order_by(MatchSuggestion.confidence.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await self.db.execute(query)
        return list(result.unique().scalars().all()), total

    async def list_for_item(self, canonical_item_id: str) -> list[MatchSuggestion]:
        result = await self.db.execute(
            select(MatchSuggestion)
            .options(joinedload(MatchSuggestion.canonical_item))
            .where(
                MatchSuggestion.canonical_item_id == canonical_item_id,
                MatchSuggestion.status == "pending",
            )
            .order_by(MatchSuggestion.confidence.desc())
        )
        return list(result.unique().scalars().all())

    async def accept(self, suggestion: MatchSuggestion) -> None:
        suggestion.status = "accepted"
        suggestion.resolved_at = utc_now()
        await self.db.flush()

    async def reject(self, suggestion: MatchSuggestion) -> None:
        suggestion.status = "rejected"
        suggestion.resolved_at = utc_now()
        await self.db.flush()

    async def pending_count(self) -> int:
        from sqlalchemy import func

        result = await self.db.execute(
            select(func.count())
            .select_from(MatchSuggestion)
            .where(MatchSuggestion.status == "pending")
        )
        return result.scalar() or 0
