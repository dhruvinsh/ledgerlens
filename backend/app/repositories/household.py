from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.household import Household


class HouseholdRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, household_id: str) -> Household | None:
        result = await self.db.execute(
            select(Household)
            .options(joinedload(Household.users))
            .where(Household.id == household_id)
        )
        return result.unique().scalar_one_or_none()

    async def create(self, household: Household) -> Household:
        self.db.add(household)
        await self.db.flush()
        return household

    async def update(self, household: Household) -> None:
        await self.db.flush()
