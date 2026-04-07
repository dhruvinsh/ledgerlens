import uuid

from rapidfuzz import fuzz
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.canonical_item import CanonicalItem
from app.models.line_item import LineItem
from app.models.match_suggestion import MatchSuggestion
from app.repositories.canonical_item import CanonicalItemRepository
from app.services.normalization import normalize_item_name


class MatchingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.item_repo = CanonicalItemRepository(db)
        self._item_cache: list[CanonicalItem] | None = None

    async def _get_all_items(self) -> list[CanonicalItem]:
        """Load all canonical items once per service instance and cache in memory.

        Callers that process multiple line items in a loop share one DB round-trip.
        New items created mid-loop are appended so subsequent iterations see them.
        """
        if self._item_cache is None:
            self._item_cache = await self.item_repo.list_all()
        return self._item_cache

    async def find_or_create_canonical_item(
        self,
        raw_name: str,
        line_item: LineItem | None = None,
    ) -> CanonicalItem | None:
        """Try to match a raw item name to an existing canonical item.

        Resolution order:
        1. Exact name match → link
        2. Exact alias match → link
        3. Fuzzy match ≥ auto_link threshold → auto-link + add as alias
        4. Fuzzy match ≥ suggest threshold → create MatchSuggestion
        5. No match → create new CanonicalItem

        Returns the matched/created CanonicalItem.
        """
        normalized = normalize_item_name(raw_name)
        lower_normalized = normalized.lower()
        all_items = await self._get_all_items()

        # 1. Exact name match (in-memory)
        for item in all_items:
            if item.name.lower() == lower_normalized:
                if line_item:
                    line_item.canonical_item_id = item.id
                return item

        # 2. Exact alias match (in-memory)
        for item in all_items:
            if any(a.lower() == lower_normalized for a in (item.aliases or [])):
                if line_item:
                    line_item.canonical_item_id = item.id
                return item

        # 3 & 4. Fuzzy matching (in-memory)
        best_score = 0.0
        best_item: CanonicalItem | None = None

        for item in all_items:
            names_to_check = [item.name] + (item.aliases or [])
            for candidate in names_to_check:
                score = max(
                    fuzz.token_sort_ratio(normalized, candidate),
                    fuzz.partial_ratio(normalized, candidate),
                )
                if score > best_score:
                    best_score = score
                    best_item = item

        if best_item and best_score >= settings.FUZZY_AUTO_LINK_THRESHOLD:
            # Auto-link and add as alias
            if line_item:
                line_item.canonical_item_id = best_item.id
            if lower_normalized not in [a.lower() for a in (best_item.aliases or [])]:
                best_item.aliases = (best_item.aliases or []) + [normalized]
                await self.item_repo.update(best_item)
                # best_item is the same object in the cache — alias update is already reflected
            return best_item

        if (
            best_item
            and best_score >= settings.FUZZY_SUGGEST_THRESHOLD
            and line_item
        ):
            # Create a suggestion
            suggestion = MatchSuggestion(
                id=str(uuid.uuid4()),
                line_item_id=line_item.id,
                canonical_item_id=best_item.id,
                confidence=best_score,
                status="pending",
            )
            self.db.add(suggestion)
            # Don't link — leave canonical_item_id null
            # Fall through to create new item below

        # 5. No match — create new canonical item
        new_item = CanonicalItem(name=normalized)
        await self.item_repo.create(new_item)
        # Append to cache so the next iteration in this batch sees the new item
        all_items.append(new_item)
        if line_item and not line_item.canonical_item_id:
            line_item.canonical_item_id = new_item.id
        return new_item
