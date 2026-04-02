import logging
import re
import uuid

from rapidfuzz import fuzz
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.store import Store
from app.models.store_alias import StoreAlias
from app.repositories.store import StoreRepository
from app.repositories.store_alias import StoreAliasRepository
from app.repositories.store_merge_suggestion import StoreMergeSuggestionRepository
from app.services.normalization import normalize_store_name

logger = logging.getLogger(__name__)

_STORE_NUMBER_RE = re.compile(r"\s*#?\d{3,}$")


class StoreMatchingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.store_repo = StoreRepository(db)
        self.alias_repo = StoreAliasRepository(db)
        self.suggestion_repo = StoreMergeSuggestionRepository(db)

    async def find_or_create_store(
        self,
        raw_name: str,
        address: str | None = None,
        chain: str | None = None,
        created_by: str = "",
    ) -> Store:
        """Resolve an OCR-extracted store name to a Store record.

        Resolution order:
        1. Exact name match (case-insensitive)
        2. Exact alias match
        3. Fuzzy >= auto-link threshold + address check -> link + add alias
        4. Fuzzy >= suggest threshold -> create StoreMergeSuggestion
        5. No match -> create new Store

        The raw_name (before normalization) is always saved as a StoreAlias.
        """
        normalized, detected_chain = normalize_store_name(raw_name)
        effective_chain = chain or detected_chain

        # 1. Exact name match
        existing = await self.store_repo.get_by_name(normalized)
        if existing:
            await self._ensure_alias(existing.id, raw_name)
            self._update_chain_if_missing(existing, effective_chain)
            return existing

        # 2. Exact alias match
        alias = await self.alias_repo.get_by_alias(normalized)
        if alias:
            store = await self.store_repo.get_by_id(alias.store_id)
            if store:
                await self._ensure_alias(store.id, raw_name)
                self._update_chain_if_missing(store, effective_chain)
                return store

        # 3 & 4. Fuzzy matching against all active stores
        all_stores = await self.store_repo.list_active()
        best_score = 0.0
        best_store: Store | None = None

        for candidate in all_stores:
            score = self._best_similarity(normalized, candidate)
            if score > best_score:
                best_score = score
                best_store = candidate

        if best_store and best_score >= settings.STORE_FUZZY_AUTO_LINK_THRESHOLD:
            # Address check: don't merge different locations
            if not self._addresses_compatible(address, best_store.address):
                # Different location — create new store with shared chain
                return await self._create_store(
                    normalized, address, effective_chain or best_store.chain, created_by, raw_name
                )

            # Auto-link
            await self._ensure_alias(best_store.id, raw_name)
            await self._ensure_alias(best_store.id, normalized)
            self._update_chain_if_missing(best_store, effective_chain)
            if address and not best_store.address:
                best_store.address = address
            logger.info(
                "Store auto-linked: '%s' -> '%s' (score=%.1f)",
                raw_name, best_store.name, best_score,
            )
            return best_store

        if best_store and best_score >= settings.STORE_FUZZY_SUGGEST_THRESHOLD:
            # Create the new store first, then a suggestion for admin review
            new_store = await self._create_store(
                normalized, address, effective_chain, created_by, raw_name
            )
            if not await self.suggestion_repo.exists_for_pair(best_store.id, new_store.id):
                await self.suggestion_repo.create(best_store.id, new_store.id, best_score)
                logger.info(
                    "Store merge suggested: '%s' <-> '%s' (score=%.1f)",
                    best_store.name, new_store.name, best_score,
                )
            return new_store

        # 5. No match — create new store
        return await self._create_store(
            normalized, address, effective_chain, created_by, raw_name
        )

    async def _create_store(
        self,
        name: str,
        address: str | None,
        chain: str | None,
        created_by: str,
        raw_name: str,
    ) -> Store:
        """Create a new store and seed its initial alias."""
        store = Store(
            name=name,
            address=address,
            chain=chain,
            created_by=created_by,
        )
        await self.store_repo.create(store)
        # Seed alias from raw OCR name
        await self._ensure_alias(store.id, raw_name)
        # Also alias the normalized name if different
        if raw_name.strip().lower() != name.strip().lower():
            await self._ensure_alias(store.id, name)
        return store

    async def _ensure_alias(self, store_id: str, name: str) -> None:
        """Add an alias if it doesn't already exist."""
        if not name or not name.strip():
            return
        cleaned = " ".join(name.split()).strip()
        if await self.alias_repo.alias_exists(cleaned):
            return
        alias = StoreAlias(
            id=str(uuid.uuid4()),
            store_id=store_id,
            alias_name=cleaned,
            alias_name_lower=cleaned.lower(),
            source="ocr",
        )
        await self.alias_repo.create(alias)

    def _best_similarity(self, name: str, candidate: Store) -> float:
        """Compute best fuzzy score between name and all candidate names/aliases."""
        names_to_check = [candidate.name]
        if hasattr(candidate, "aliases") and candidate.aliases:
            names_to_check += [a.alias_name for a in candidate.aliases]

        best = 0.0
        name_clean = self._strip_store_number(name.lower())
        for cand_name in names_to_check:
            cand_clean = self._strip_store_number(cand_name.lower())
            score = max(
                fuzz.token_sort_ratio(name_clean, cand_clean),
                fuzz.partial_ratio(name_clean, cand_clean),
            )
            if score > best:
                best = score
        return best

    @staticmethod
    def _strip_store_number(name: str) -> str:
        """Remove trailing store numbers like '#1234' or '5678'."""
        return _STORE_NUMBER_RE.sub("", name).strip()

    @staticmethod
    def _addresses_compatible(addr_a: str | None, addr_b: str | None) -> bool:
        """Check if two addresses are compatible (same location or one is missing).

        Returns True if:
        - Either address is missing (ambiguous, allow linking)
        - Both addresses are similar enough (token_sort_ratio >= 50)
        """
        if not addr_a or not addr_b:
            return True
        score = fuzz.token_sort_ratio(addr_a.lower(), addr_b.lower())
        return score >= 50

    @staticmethod
    def _update_chain_if_missing(store: Store, chain: str | None) -> None:
        """Set chain on store if it doesn't have one yet."""
        if chain and not store.chain:
            store.chain = chain

    async def scan_for_duplicates(self) -> int:
        """Compare all active stores pairwise. Create StoreMergeSuggestion
        for pairs above suggest threshold. Returns count of new suggestions."""
        stores = await self.store_repo.list_active()
        count = 0

        for i, store_a in enumerate(stores):
            for store_b in stores[i + 1:]:
                score = self._best_similarity(store_a.name, store_b)
                # Boost if same chain
                if store_a.chain and store_b.chain and store_a.chain.lower() == store_b.chain.lower():
                    score = min(100.0, score + 10)

                if score >= settings.STORE_FUZZY_SUGGEST_THRESHOLD:
                    if await self.suggestion_repo.exists_for_pair(store_a.id, store_b.id):
                        continue
                    await self.suggestion_repo.create(store_a.id, store_b.id, score)
                    count += 1

        return count
