from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.time import utc_now
from app.models.line_item import LineItem
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
        from app.core.pagination import paginate

        query = (
            select(MatchSuggestion)
            .where(MatchSuggestion.status == "pending")
            .options(
                joinedload(MatchSuggestion.canonical_item),
                joinedload(MatchSuggestion.line_item),
            )
            .order_by(MatchSuggestion.confidence.desc())
        )
        return await paginate(self.db, query, page, per_page)

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

    async def reject_stale_for_canonical(self, canonical_item_id: str) -> int:
        """Bulk-reject pending suggestions whose line item is already linked to
        `canonical_item_id` but the suggestion points to a different canonical item.

        Called when a user renames a canonical item to ensure stale suggestions
        can no longer override the confirmed linkage.
        """
        subq = (
            select(LineItem.id)
            .where(LineItem.canonical_item_id == canonical_item_id)
            .scalar_subquery()
        )
        result = await self.db.execute(
            update(MatchSuggestion)
            .where(
                MatchSuggestion.line_item_id.in_(subq),
                MatchSuggestion.canonical_item_id != canonical_item_id,
                MatchSuggestion.status == "pending",
            )
            .values(status="rejected", resolved_at=utc_now())
        )
        await self.db.flush()
        return result.rowcount  # type: ignore[return-value]

    async def pending_count(self) -> int:
        from sqlalchemy import func

        result = await self.db.execute(
            select(func.count())
            .select_from(MatchSuggestion)
            .where(MatchSuggestion.status == "pending")
        )
        return result.scalar() or 0
