import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import StoreNotFoundError, ValidationError
from app.models.receipt import Receipt
from app.models.store import Store
from app.models.store_alias import StoreAlias
from app.repositories.store import StoreRepository
from app.repositories.store_alias import StoreAliasRepository
from app.repositories.store_merge_suggestion import StoreMergeSuggestionRepository
from app.schemas.store import StoreUpdate
from app.services.store_matching import StoreMatchingService


class StoreService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = StoreRepository(db)
        self.alias_repo = StoreAliasRepository(db)
        self.suggestion_repo = StoreMergeSuggestionRepository(db)

    async def get_by_id(self, store_id: str) -> Store:
        store = await self.repo.get_by_id(store_id)
        if not store:
            raise StoreNotFoundError(f"Store {store_id} not found")
        return store

    async def get_by_id_with_aliases(self, store_id: str) -> Store:
        result = await self.db.execute(
            select(Store)
            .options(selectinload(Store.aliases))
            .where(Store.id == store_id)
        )
        store = result.scalar_one_or_none()
        if not store:
            raise StoreNotFoundError(f"Store {store_id} not found")
        return store

    async def list_stores(
        self,
        search: str | None = None,
        chain: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[tuple[Store, int]], int]:
        """Returns list of (store, receipt_count) tuples and total count."""
        base = select(Store).where(Store.merged_into_id.is_(None))

        if search:
            base = base.where(Store.name.ilike(f"%{search}%"))
        if chain:
            base = base.where(func.lower(Store.chain) == chain.lower())

        count_query = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Single query: stores + receipt counts via outer join + group by
        receipt_count = (
            select(Receipt.store_id, func.count().label("cnt"))
            .group_by(Receipt.store_id)
            .subquery()
        )
        query = (
            base
            .options(selectinload(Store.aliases))
            .outerjoin(receipt_count, Store.id == receipt_count.c.store_id)
            .add_columns(func.coalesce(receipt_count.c.cnt, 0).label("receipt_count"))
            .order_by(Store.name)
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await self.db.execute(query)
        rows = result.unique().all()
        stores_with_counts = [(row[0], row[1]) for row in rows]

        return stores_with_counts, total

    async def update(self, store_id: str, data: StoreUpdate) -> Store:
        store = await self.get_by_id(store_id)

        if data.name is not None:
            store.name = data.name
        if data.address is not None:
            store.address = data.address
        if data.chain is not None:
            store.chain = data.chain
        if data.latitude is not None:
            store.latitude = data.latitude
        if data.longitude is not None:
            store.longitude = data.longitude
        if data.is_verified is not None:
            store.is_verified = data.is_verified

        await self.db.flush()
        await self.db.commit()
        return await self.get_by_id_with_aliases(store_id)

    async def merge_stores(
        self,
        canonical_id: str,
        duplicate_ids: list[str],
        user_id: str,
    ) -> Store:
        """Merge duplicate stores into the canonical store.

        1. Validate all IDs
        2. Reassign all receipts from duplicates to canonical
        3. Move all aliases from duplicates to canonical
        4. Add each duplicate's name as an alias of canonical
        5. Set merged_into_id on each duplicate
        6. Adopt chain/address from duplicate if canonical lacks them
        """
        canonical = await self.get_by_id(canonical_id)

        for dup_id in duplicate_ids:
            if dup_id == canonical_id:
                raise ValidationError("Cannot merge a store into itself")

            dup = await self.get_by_id(dup_id)

            # Reassign receipts
            await self.db.execute(
                update(Receipt)
                .where(Receipt.store_id == dup_id)
                .values(store_id=canonical_id)
            )

            # Move aliases from duplicate to canonical (skip if canonical already has it)
            dup_aliases = await self.alias_repo.get_aliases_for_store(dup_id)
            for alias in dup_aliases:
                existing = await self.alias_repo.get_by_alias(alias.alias_name)
                if existing and existing.store_id == canonical_id:
                    # Canonical already has this alias, just delete the duplicate's copy
                    await self.alias_repo.delete_by_id(alias.id)
                else:
                    # Reassign to canonical
                    alias.store_id = canonical_id
                    await self.db.flush()

            # Add duplicate's canonical name as alias
            if not await self.alias_repo.alias_exists(dup.name):
                new_alias = StoreAlias(
                    id=str(uuid.uuid4()),
                    store_id=canonical_id,
                    alias_name=dup.name,
                    alias_name_lower=dup.name.lower(),
                    source="manual",
                )
                await self.alias_repo.create(new_alias)

            # Adopt missing fields
            if not canonical.chain and dup.chain:
                canonical.chain = dup.chain
            if not canonical.address and dup.address:
                canonical.address = dup.address

            # Soft-delete duplicate
            dup.merged_into_id = canonical_id

        await self.db.flush()
        # Re-load with aliases for response
        return await self.get_by_id_with_aliases(canonical_id)

    async def accept_merge_suggestion(self, suggestion_id: str, user_id: str) -> Store:
        """Accept a merge suggestion: merge store_b into store_a."""
        suggestion = await self.suggestion_repo.get_by_id(suggestion_id)
        if not suggestion:
            raise StoreNotFoundError(f"Suggestion {suggestion_id} not found")

        result = await self.merge_stores(
            canonical_id=suggestion.store_a_id,
            duplicate_ids=[suggestion.store_b_id],
            user_id=user_id,
        )
        await self.suggestion_repo.accept(suggestion_id, user_id)
        await self.db.commit()
        return result

    async def reject_merge_suggestion(self, suggestion_id: str, user_id: str) -> None:
        await self.suggestion_repo.reject(suggestion_id, user_id)
        await self.db.commit()

    async def scan_for_duplicates(self) -> int:
        svc = StoreMatchingService(self.db)
        count = await svc.scan_for_duplicates()
        await self.db.commit()
        return count
