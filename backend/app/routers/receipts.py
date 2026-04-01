from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.pagination import PaginatedResponse
from app.schemas.receipt import (
    ManualReceiptCreate,
    ReceiptDetail,
    ReceiptFilters,
    ReceiptListItem,
    ReceiptUpdate,
)
from app.services.receipt import ReceiptService

router = APIRouter(prefix="/receipts", tags=["receipts"])


def _to_list_item(r) -> ReceiptListItem:  # type: ignore[no-untyped-def]
    return ReceiptListItem(
        id=r.id,
        user_id=r.user_id,
        store=r.store,
        transaction_date=r.transaction_date.isoformat() if r.transaction_date else None,
        currency=r.currency,
        total=r.total,
        source=r.source,
        status=r.status,
        thumbnail_path=r.thumbnail_path,
        page_count=r.page_count,
        created_at=r.created_at.isoformat(),
    )


def _to_detail(r) -> ReceiptDetail:  # type: ignore[no-untyped-def]
    return ReceiptDetail(
        id=r.id,
        user_id=r.user_id,
        store=r.store,
        transaction_date=r.transaction_date.isoformat() if r.transaction_date else None,
        currency=r.currency,
        subtotal=r.subtotal,
        tax=r.tax,
        total=r.total,
        source=r.source,
        status=r.status,
        file_path=r.file_path,
        thumbnail_path=r.thumbnail_path,
        page_count=r.page_count,
        ocr_confidence=r.ocr_confidence,
        extraction_source=r.extraction_source,
        raw_ocr_text=r.raw_ocr_text,
        duplicate_of=r.duplicate_of,
        notes=r.notes,
        line_items=r.line_items,
        created_at=r.created_at.isoformat(),
    )


@router.post("", response_model=ReceiptListItem, status_code=201)
async def upload_receipt(
    file: UploadFile = File(...),
    source: Literal["camera", "upload"] = Form(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReceiptListItem:
    svc = ReceiptService(db, user)
    content = await file.read()
    receipt = await svc.upload(content, file.filename or "upload.jpg", source)
    return _to_list_item(receipt)


@router.post("/manual", response_model=ReceiptDetail, status_code=201)
async def create_manual_receipt(
    body: ManualReceiptCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReceiptDetail:
    svc = ReceiptService(db, user)
    receipt = await svc.create_manual(body)
    return _to_detail(receipt)


@router.get("", response_model=PaginatedResponse[ReceiptListItem])
async def list_receipts(
    status: str | None = Query(None),
    store_id: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ReceiptListItem]:
    svc = ReceiptService(db, user)
    filters = ReceiptFilters(
        status=status,
        store_id=store_id,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        per_page=per_page,
    )
    receipts, total = await svc.list_receipts(filters)
    return PaginatedResponse(
        items=[_to_list_item(r) for r in receipts],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{receipt_id}", response_model=ReceiptDetail)
async def get_receipt(
    receipt_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReceiptDetail:
    svc = ReceiptService(db, user)
    receipt = await svc.get_detail(receipt_id)
    return _to_detail(receipt)


@router.patch("/{receipt_id}", response_model=ReceiptDetail)
async def update_receipt(
    receipt_id: str,
    body: ReceiptUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReceiptDetail:
    svc = ReceiptService(db, user)
    receipt = await svc.update(receipt_id, body)
    return _to_detail(receipt)


@router.post("/{receipt_id}/reprocess", status_code=200)
async def reprocess_receipt(
    receipt_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    from app.services.processing import enqueue_receipt

    svc = ReceiptService(db, user)
    receipt = await svc.get_detail(receipt_id)
    if receipt.user_id != user.id:
        from app.core.exceptions import ForbiddenError

        raise ForbiddenError("You can only reprocess your own receipts")
    job = await enqueue_receipt(receipt.id, db)
    return {"detail": "Reprocessing started", "job_id": job.id}


@router.delete("/{receipt_id}", status_code=200)
async def delete_receipt(
    receipt_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    svc = ReceiptService(db, user)
    await svc.delete(receipt_id)
    return {"detail": "Receipt deleted"}
