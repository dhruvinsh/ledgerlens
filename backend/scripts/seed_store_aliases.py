#!/usr/bin/env python3
"""Seed store aliases and backfill chains.

NOTE: This logic now runs automatically as an Alembic data migration
(335bdcdbe782_seed_store_aliases_and_backfill_chains). You do NOT need to
run this script manually — `alembic upgrade head` handles it on first boot.

This script is kept only for manual re-runs (e.g., after bulk store imports)
or to trigger a duplicate scan.

Usage:
    cd backend && uv run python -m scripts.seed_store_aliases
"""

import asyncio
import uuid

from app.core.database import async_session_factory
from app.models.store_alias import StoreAlias
from app.repositories.store import StoreRepository
from app.repositories.store_alias import StoreAliasRepository
from app.services.normalization import normalize_store_name
from app.services.store_matching import StoreMatchingService


async def main() -> None:
    async with async_session_factory() as db:
        store_repo = StoreRepository(db)
        alias_repo = StoreAliasRepository(db)

        stores = await store_repo.list_all()
        aliases_created = 0
        chains_backfilled = 0

        for store in stores:
            # Seed alias from current store name
            if not await alias_repo.alias_exists(store.name):
                alias = StoreAlias(
                    id=str(uuid.uuid4()),
                    store_id=store.id,
                    alias_name=store.name,
                    alias_name_lower=store.name.lower(),
                    source="ocr",
                )
                await alias_repo.create(alias)
                aliases_created += 1

            # Backfill chain from normalization
            _, detected_chain = normalize_store_name(store.name)
            if detected_chain and not store.chain:
                store.chain = detected_chain
                chains_backfilled += 1

        await db.commit()
        print(f"Created {aliases_created} aliases for {len(stores)} stores")
        print(f"Backfilled {chains_backfilled} chain values")

        # Run duplicate scan
        matching_svc = StoreMatchingService(db)
        suggestions = await matching_svc.scan_for_duplicates()
        await db.commit()
        print(f"Created {suggestions} merge suggestions")


if __name__ == "__main__":
    asyncio.run(main())
