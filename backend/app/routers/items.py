from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.item import (
    CanonicalItemResponse,
    CanonicalItemUpdate,
    PriceHistoryResponse,
)
from app.schemas.pagination import PaginatedResponse
from app.services.item import ItemService

router = APIRouter(prefix="/items", tags=["items"])


def _to_response(item) -> CanonicalItemResponse:  # type: ignore[no-untyped-def]
    return CanonicalItemResponse(
        id=item.id,
        name=item.name,
        category=item.category,
        aliases=item.aliases or [],
        product_url=item.product_url,
        image_path=item.image_path,
        image_source=item.image_source,
        image_fetch_status=item.image_fetch_status,
        created_at=item.created_at.isoformat(),
    )


@router.get("", response_model=PaginatedResponse[CanonicalItemResponse])
async def list_items(
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[CanonicalItemResponse]:
    svc = ItemService(db)
    items, total = await svc.list_items(search=search, page=page, per_page=per_page)
    return PaginatedResponse(
        items=[_to_response(i) for i in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{item_id}", response_model=CanonicalItemResponse)
async def get_item(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CanonicalItemResponse:
    svc = ItemService(db)
    item = await svc.get_by_id(item_id)
    return _to_response(item)


@router.get("/{item_id}/prices", response_model=PriceHistoryResponse)
async def get_price_history(
    item_id: str,
    store_ids: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PriceHistoryResponse:
    svc = ItemService(db)
    item = await svc.get_by_id(item_id)
    sid_list = store_ids.split(",") if store_ids else None
    points = await svc.get_price_history(
        item_id, store_ids=sid_list, date_from=date_from, date_to=date_to
    )
    return PriceHistoryResponse(item=_to_response(item), data_points=points)


@router.patch("/{item_id}", response_model=CanonicalItemResponse)
async def update_item(
    item_id: str,
    body: CanonicalItemUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CanonicalItemResponse:
    svc = ItemService(db)
    item = await svc.update(item_id, body)
    return _to_response(item)


@router.delete("/{item_id}", status_code=200)
async def delete_item(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    svc = ItemService(db)
    await svc.delete(item_id)
    return {"detail": "Item deleted"}


@router.post("/{item_id}/image", response_model=CanonicalItemResponse)
async def upload_image(
    item_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CanonicalItemResponse:
    svc = ItemService(db)
    content = await file.read()
    item = await svc.upload_image(item_id, content, file.filename or "image.jpg")
    return _to_response(item)


@router.delete("/{item_id}/image", response_model=CanonicalItemResponse)
async def delete_image(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CanonicalItemResponse:
    svc = ItemService(db)
    item = await svc.delete_image(item_id)
    return _to_response(item)


@router.post("/{item_id}/fetch-image", status_code=200)
async def fetch_image(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    from app.services.image_fetcher import fetch_product_image

    svc = ItemService(db)
    item = await svc.get_by_id(item_id)
    await fetch_product_image(item, db)
    return {"detail": "Image fetch initiated"}
