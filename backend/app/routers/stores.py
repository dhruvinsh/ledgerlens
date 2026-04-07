from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.receipt import Receipt
from app.models.user import User
from app.schemas.pagination import PaginatedResponse
from app.schemas.store import (
    StoreAliasCreate,
    StoreAliasResponse,
    StoreMergeRequest,
    StoreMergeSuggestionResponse,
    StoreResponse,
    StoreUpdate,
)
from app.schemas.receipt import ReceiptListItem, receipt_to_list_item
from app.services.store import StoreService

router = APIRouter(prefix="/stores", tags=["stores"])


def _to_response(store, receipt_count: int = 0) -> StoreResponse:
    aliases = [a.alias_name for a in store.aliases] if store.aliases else []
    return StoreResponse(
        id=store.id,
        name=store.name,
        address=store.address,
        chain=store.chain,
        latitude=store.latitude,
        longitude=store.longitude,
        is_verified=store.is_verified,
        merged_into_id=store.merged_into_id,
        aliases=aliases,
        receipt_count=receipt_count,
        created_at=store.created_at.isoformat(),
    )



@router.get("/{store_id}/receipts", response_model=PaginatedResponse[ReceiptListItem])
async def get_store_receipts(
    store_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ReceiptListItem]:
    svc = StoreService(db)
    items, total = await svc.get_receipts(store_id, page=page, per_page=per_page)
    return PaginatedResponse(
        items=[receipt_to_list_item(r) for r in items],
        total=total,
        page=page,
        per_page=per_page,
    )


# ── Core CRUD ──


@router.get("", response_model=PaginatedResponse[StoreResponse])
async def list_stores(
    search: str | None = Query(None),
    chain: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[StoreResponse]:
    svc = StoreService(db)
    stores_with_counts, total = await svc.list_stores(
        search=search, chain=chain, page=page, per_page=per_page
    )
    return PaginatedResponse(
        items=[_to_response(store, count) for store, count in stores_with_counts],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/merge-suggestions", response_model=PaginatedResponse[StoreMergeSuggestionResponse])
async def list_merge_suggestions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[StoreMergeSuggestionResponse]:
    svc = StoreService(db)
    suggestions, total = await svc.suggestion_repo.list_pending(page, per_page)

    store_ids = list({s.store_a.id for s in suggestions} | {s.store_b.id for s in suggestions})
    if store_ids:
        rc = (
            select(Receipt.store_id, func.count().label("cnt"))
            .where(Receipt.store_id.in_(store_ids))
            .group_by(Receipt.store_id)
        )
        counts = {row[0]: row[1] for row in (await db.execute(rc))}
    else:
        counts = {}

    items = [
        StoreMergeSuggestionResponse(
            id=s.id,
            store_a=_to_response(s.store_a, counts.get(s.store_a.id, 0)),
            store_b=_to_response(s.store_b, counts.get(s.store_b.id, 0)),
            confidence=s.confidence,
            status=s.status,
            created_at=s.created_at.isoformat(),
        )
        for s in suggestions
    ]
    return PaginatedResponse(items=items, total=total, page=page, per_page=per_page)


@router.post("/merge-suggestions/{suggestion_id}/accept", response_model=StoreResponse)
async def accept_merge_suggestion(
    suggestion_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> StoreResponse:
    svc = StoreService(db)
    store = await svc.accept_merge_suggestion(suggestion_id, admin.id)
    count = await svc.get_receipt_count(store.id)
    return _to_response(store, count)


@router.post("/merge-suggestions/{suggestion_id}/reject")
async def reject_merge_suggestion(
    suggestion_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    svc = StoreService(db)
    await svc.reject_merge_suggestion(suggestion_id, admin.id)
    return {"detail": "Suggestion rejected"}


@router.post("/scan-duplicates")
async def scan_duplicates(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    svc = StoreService(db)
    count = await svc.scan_for_duplicates()
    return {"new_suggestions": count}


@router.get("/{store_id}", response_model=StoreResponse)
async def get_store(
    store_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StoreResponse:
    svc = StoreService(db)
    store = await svc.get_by_id_with_aliases(store_id)
    count = await svc.get_receipt_count(store_id)
    return _to_response(store, count)


@router.patch("/{store_id}", response_model=StoreResponse)
async def update_store(
    store_id: str,
    body: StoreUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> StoreResponse:
    svc = StoreService(db)
    store = await svc.update(store_id, body)
    count = await svc.get_receipt_count(store_id)
    return _to_response(store, count)


@router.delete("/{store_id}")
async def delete_store(
    store_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    svc = StoreService(db)
    await svc.delete(store_id)
    return {"detail": "Store deleted"}


@router.post("/{store_id}/merge", response_model=StoreResponse)
async def merge_stores(
    store_id: str,
    body: StoreMergeRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> StoreResponse:
    svc = StoreService(db)
    store = await svc.merge_stores(store_id, body.duplicate_ids, admin.id)
    await db.commit()
    count = await svc.get_receipt_count(store_id)
    return _to_response(store, count)


# ── Aliases ──


@router.get("/{store_id}/aliases", response_model=list[StoreAliasResponse])
async def list_aliases(
    store_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[StoreAliasResponse]:
    svc = StoreService(db)
    await svc.get_by_id(store_id)  # validate exists
    aliases = await svc.alias_repo.get_aliases_for_store(store_id)
    return [
        StoreAliasResponse(
            id=a.id,
            store_id=a.store_id,
            alias_name=a.alias_name,
            source=a.source,
            created_at=a.created_at.isoformat(),
        )
        for a in aliases
    ]


@router.post("/{store_id}/aliases", response_model=StoreAliasResponse, status_code=201)
async def add_alias(
    store_id: str,
    body: StoreAliasCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> StoreAliasResponse:
    import uuid

    from app.models.store_alias import StoreAlias

    svc = StoreService(db)
    await svc.get_by_id(store_id)  # validate exists

    alias = StoreAlias(
        id=str(uuid.uuid4()),
        store_id=store_id,
        alias_name=body.alias_name,
        alias_name_lower=body.alias_name.lower(),
        source="manual",
    )
    await svc.alias_repo.create(alias)
    await db.commit()
    return StoreAliasResponse(
        id=alias.id,
        store_id=alias.store_id,
        alias_name=alias.alias_name,
        source=alias.source,
        created_at=alias.created_at.isoformat(),
    )


@router.delete("/{store_id}/aliases/{alias_id}")
async def remove_alias(
    store_id: str,
    alias_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    svc = StoreService(db)
    await svc.get_by_id(store_id)  # validate exists
    await svc.alias_repo.delete_by_id(alias_id)
    await db.commit()
    return {"detail": "Alias removed"}
