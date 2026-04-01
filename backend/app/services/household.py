from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    HouseholdNotFoundError,
    ValidationError,
)
from app.core.security import create_invite_token, verify_invite_token
from app.models.household import Household
from app.models.user import User
from app.repositories.household import HouseholdRepository
from app.repositories.user import UserRepository
from app.schemas.household import HouseholdCreate, HouseholdUpdate


class HouseholdService:
    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user
        self.repo = HouseholdRepository(db)
        self.user_repo = UserRepository(db)

    async def create(self, data: HouseholdCreate) -> Household:
        if self.user.household_id:
            raise ConflictError("You already belong to a household")

        household = Household(
            name=data.name,
            owner_id=self.user.id,
        )
        await self.repo.create(household)

        self.user.household_id = household.id
        await self.db.commit()

        return await self._load(household.id)

    async def get(self) -> Household:
        if not self.user.household_id:
            raise HouseholdNotFoundError("You don't belong to a household")
        household = await self.repo.get_by_id(self.user.household_id)
        if not household:
            raise HouseholdNotFoundError("Household not found")
        return household

    async def update(self, data: HouseholdUpdate) -> Household:
        household = await self.get()
        if household.owner_id != self.user.id:
            raise ForbiddenError("Only the household owner can update settings")

        if data.name is not None:
            household.name = data.name
        if data.sharing_mode is not None:
            household.sharing_mode = data.sharing_mode

        await self.repo.update(household)
        await self.db.commit()
        return await self._load(household.id)

    async def create_invite(self) -> str:
        household = await self.get()
        if household.owner_id != self.user.id:
            raise ForbiddenError("Only the household owner can create invites")
        return create_invite_token(household.id)

    async def join(self, token: str) -> Household:
        payload = verify_invite_token(token)
        if not payload:
            raise ValidationError("Invalid or expired invite token")

        household_id = payload["household_id"]
        household = await self.repo.get_by_id(household_id)
        if not household:
            raise HouseholdNotFoundError("Household not found")

        if self.user.household_id:
            raise ConflictError("You already belong to a household")

        self.user.household_id = household.id
        await self.db.commit()
        return await self._load(household.id)

    async def remove_member(self, member_id: str) -> None:
        household = await self.get()
        if household.owner_id != self.user.id:
            raise ForbiddenError("Only the household owner can remove members")
        if member_id == self.user.id:
            raise ValidationError("Cannot remove yourself from the household")

        member = await self.user_repo.get_by_id(member_id)
        if not member or member.household_id != household.id:
            raise ValidationError("User is not a member of this household")

        member.household_id = None
        await self.db.commit()

    async def _load(self, household_id: str) -> Household:
        h = await self.repo.get_by_id(household_id)
        assert h is not None
        return h
