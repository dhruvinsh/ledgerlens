from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundError
from app.models.line_item import LineItem
from app.models.receipt import Receipt
from app.models.user import User
from app.schemas.receipt import LineItemResponse, LineItemUpdate
from app.services.scope import receipt_visibility

router = APIRouter(prefix="/line-items", tags=["line-items"])


@router.patch("/{line_item_id}", response_model=LineItemResponse)
async def update_line_item(
    line_item_id: str,
    body: LineItemUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LineItemResponse:
    # Load line item with its receipt in one query, scoped to user visibility
    result = await db.execute(
        select(LineItem)
        .join(Receipt, LineItem.receipt_id == Receipt.id)
        .options(joinedload(LineItem.canonical_item))
        .where(LineItem.id == line_item_id, receipt_visibility(user))
    )
    li = result.unique().scalar_one_or_none()
    if not li:
        raise NotFoundError("Line item not found")

    if body.name is not None:
        li.name = body.name
    if body.quantity is not None:
        li.quantity = body.quantity
    if body.unit_price is not None:
        li.unit_price = body.unit_price
    if body.total_price is not None:
        li.total_price = body.total_price
    if body.canonical_item_id is not None:
        li.canonical_item_id = body.canonical_item_id

    li.is_corrected = True
    await db.flush()
    await db.commit()

    return LineItemResponse.model_validate(li)
