import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.canonical_item import CanonicalItem
from app.repositories.canonical_item import CanonicalItemRepository
from app.services import storage

logger = logging.getLogger(__name__)


async def fetch_product_image(item: CanonicalItem, db: AsyncSession) -> None:
    """Search Google Custom Search for a product image and save it."""
    repo = CanonicalItemRepository(db)

    if not settings.GOOGLE_CSE_API_KEY or not settings.GOOGLE_CSE_CX:
        logger.warning("Google CSE not configured, skipping image fetch")
        item.image_fetch_status = "not_found"
        await repo.update(item)
        await db.commit()
        return

    item.image_fetch_status = "fetching"
    await repo.update(item)
    await db.commit()

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "key": settings.GOOGLE_CSE_API_KEY,
                    "cx": settings.GOOGLE_CSE_CX,
                    "q": item.name,
                    "searchType": "image",
                    "num": 1,
                    "imgSize": "medium",
                    "safe": "active",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        results = data.get("items", [])
        if not results:
            item.image_fetch_status = "not_found"
            await repo.update(item)
            await db.commit()
            return

        image_url = results[0]["link"]

        # Download the image
        async with httpx.AsyncClient(timeout=15) as client:
            img_resp = await client.get(image_url)
            img_resp.raise_for_status()

        # Save and resize
        relative_path = await storage.save_product_image(
            img_resp.content, "image.jpg", item.id
        )
        item.image_path = relative_path
        item.image_source = "auto"
        item.image_fetch_status = "found"
        await repo.update(item)
        await db.commit()

    except Exception as e:
        logger.warning("Image fetch failed for item %s: %s", item.id, e)
        item.image_fetch_status = "failed"
        await repo.update(item)
        await db.commit()
