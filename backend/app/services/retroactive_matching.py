import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)


async def start_retroactive_loop(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Background loop that scans unmatched line items and runs fuzzy matching.

    Runs every RETROACTIVE_INTERVAL_SECONDS (default 300s).
    Processes RETROACTIVE_BATCH_SIZE items per cycle.
    """
    interval = settings.RETROACTIVE_INTERVAL_SECONDS
    batch_size = settings.RETROACTIVE_BATCH_SIZE

    logger.info(
        "Retroactive matching loop started (interval=%ds, batch=%d)",
        interval,
        batch_size,
    )

    while True:
        await asyncio.sleep(interval)
        try:
            await _run_batch(session_factory, batch_size)
        except Exception:
            logger.exception("Retroactive matching batch failed")


async def _run_batch(
    session_factory: async_sessionmaker[AsyncSession],
    batch_size: int,
) -> None:
    from app.models.line_item import LineItem
    from app.services.matching import MatchingService

    async with session_factory() as db:
        # Find line items with no canonical_item_id
        result = await db.execute(
            select(LineItem)
            .where(LineItem.canonical_item_id.is_(None))
            .limit(batch_size)
        )
        unmatched = list(result.scalars().all())

        if not unmatched:
            return

        logger.info("Retroactive matching: processing %d unmatched items", len(unmatched))

        svc = MatchingService(db)
        matched = 0

        for li in unmatched:
            result_item = await svc.find_or_create_canonical_item(li.name, li)
            if li.canonical_item_id:
                matched += 1

        await db.commit()
        logger.info(
            "Retroactive matching: matched %d/%d items", matched, len(unmatched)
        )
