from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import UserResponse
from app.schemas.household import (
    HouseholdCreate,
    HouseholdResponse,
    HouseholdUpdate,
    InviteResponse,
)
from app.services.household import HouseholdService

router = APIRouter(prefix="/household", tags=["household"])


def _to_response(h) -> HouseholdResponse:  # type: ignore[no-untyped-def]
    return HouseholdResponse(
        id=h.id,
        name=h.name,
        owner_id=h.owner_id,
        sharing_mode=h.sharing_mode,
        users=[
            UserResponse(
                id=u.id,
                email=u.email,
                display_name=u.display_name,
                role=u.role,
                household_id=u.household_id,
                is_active=u.is_active,
                created_at=u.created_at.isoformat(),
            )
            for u in h.users
        ],
        created_at=h.created_at.isoformat(),
    )


@router.post("", response_model=HouseholdResponse, status_code=201)
async def create_household(
    body: HouseholdCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HouseholdResponse:
    svc = HouseholdService(db, user)
    household = await svc.create(body)
    return _to_response(household)


@router.get("", response_model=HouseholdResponse)
async def get_household(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HouseholdResponse:
    svc = HouseholdService(db, user)
    household = await svc.get()
    return _to_response(household)


@router.patch("", response_model=HouseholdResponse)
async def update_household(
    body: HouseholdUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HouseholdResponse:
    svc = HouseholdService(db, user)
    household = await svc.update(body)
    return _to_response(household)


@router.post("/invite", response_model=InviteResponse)
async def create_invite(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InviteResponse:
    svc = HouseholdService(db, user)
    token = await svc.create_invite()
    return InviteResponse(invite_url=f"/join/{token}", token=token)


@router.post("/join/{token}", response_model=HouseholdResponse)
async def join_household(
    token: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HouseholdResponse:
    svc = HouseholdService(db, user)
    household = await svc.join(token)
    return _to_response(household)


@router.delete("/members/{member_id}", status_code=200)
async def remove_member(
    member_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    svc = HouseholdService(db, user)
    await svc.remove_member(member_id)
    return {"detail": "Member removed"}
