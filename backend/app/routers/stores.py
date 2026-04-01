from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.user import User
from app.schemas.pagination import PaginatedResponse
from app.schemas.store import StoreResponse, StoreUpdate
from app.services.store import StoreService

router = APIRouter(prefix="/stores", tags=["stores"])


def _to_response(store) -> StoreResponse:  # type: ignore[no-untyped-def]
    return StoreResponse(
        id=store.id,
        name=store.name,
        address=store.address,
        chain=store.chain,
        latitude=store.latitude,
        longitude=store.longitude,
        is_verified=store.is_verified,
        created_at=store.created_at.isoformat(),
    )


@router.get("", response_model=PaginatedResponse[StoreResponse])
async def list_stores(
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[StoreResponse]:
    svc = StoreService(db)
    stores, total = await svc.list_stores(search=search, page=page, per_page=per_page)
    return PaginatedResponse(
        items=[_to_response(s) for s in stores],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{store_id}", response_model=StoreResponse)
async def get_store(
    store_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StoreResponse:
    svc = StoreService(db)
    store = await svc.get_by_id(store_id)
    return _to_response(store)


@router.patch("/{store_id}", response_model=StoreResponse)
async def update_store(
    store_id: str,
    body: StoreUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> StoreResponse:
    svc = StoreService(db)
    store = await svc.update(store_id, body)
    return _to_response(store)
