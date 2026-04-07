"""Reusable async pagination helper for SQLAlchemy queries."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select


async def paginate(
    db: AsyncSession,
    query: Select[Any],
    page: int,
    per_page: int,
) -> tuple[list[Any], int]:
    """Count total rows, then fetch one page of results.

    Uses unique() when collecting scalars to de-duplicate ORM objects that
    appear multiple times due to joined eager-loading (selectinload / joinedload).
    Safe to call on queries without joins — unique() is a no-op there.
    """
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(query.offset((page - 1) * per_page).limit(per_page))
    return list(result.unique().scalars().all()), total
