from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundError
from app.models.user import User
from app.repositories.canonical_item import CanonicalItemRepository
from app.repositories.line_item import LineItemRepository
from app.repositories.match_suggestion import MatchSuggestionRepository
from app.schemas.item import CanonicalItemResponse
from app.schemas.pagination import PaginatedResponse
from app.schemas.suggestion import MatchSuggestionResponse

router = APIRouter(prefix="/suggestions", tags=["suggestions"])


def _to_response(s) -> MatchSuggestionResponse:  # type: ignore[no-untyped-def]
    ci = None
    if s.canonical_item:
        ci = CanonicalItemResponse(
            id=s.canonical_item.id,
            name=s.canonical_item.name,
            category=s.canonical_item.category,
            aliases=s.canonical_item.aliases or [],
            product_url=s.canonical_item.product_url,
            image_path=s.canonical_item.image_path,
            image_source=s.canonical_item.image_source,
            image_fetch_status=s.canonical_item.image_fetch_status,
            created_at=s.canonical_item.created_at.isoformat(),
        )
    return MatchSuggestionResponse(
        id=s.id,
        line_item_id=s.line_item_id,
        line_item_name=s.line_item.name if s.line_item else None,
        line_item_raw_name=s.line_item.raw_name if s.line_item else None,
        canonical_item_id=s.canonical_item_id,
        canonical_item=ci,
        confidence=s.confidence,
        status=s.status,
        created_at=s.created_at.isoformat(),
        resolved_at=s.resolved_at.isoformat() if s.resolved_at else None,
    )


@router.get("", response_model=PaginatedResponse[MatchSuggestionResponse])
async def list_suggestions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[MatchSuggestionResponse]:
    repo = MatchSuggestionRepository(db)
    suggestions, total = await repo.list_pending(page=page, per_page=per_page)
    return PaginatedResponse(
        items=[_to_response(s) for s in suggestions],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("/{suggestion_id}/accept", response_model=MatchSuggestionResponse)
async def accept_suggestion(
    suggestion_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MatchSuggestionResponse:
    repo = MatchSuggestionRepository(db)
    suggestion = await repo.get_by_id(suggestion_id)
    if not suggestion:
        raise NotFoundError("Suggestion not found")

    # Link the line item to the canonical item
    li_repo = LineItemRepository(db)
    line_item = await li_repo.get_by_id(suggestion.line_item_id)
    if line_item:
        line_item.canonical_item_id = suggestion.canonical_item_id
        await li_repo.update(line_item)

    # Add name as alias
    ci_repo = CanonicalItemRepository(db)
    ci = await ci_repo.get_by_id(suggestion.canonical_item_id)
    if ci and line_item:
        existing_aliases = [a.lower() for a in (ci.aliases or [])]
        if line_item.name.lower() not in existing_aliases:
            ci.aliases = (ci.aliases or []) + [line_item.name]
            await ci_repo.update(ci)

    await repo.accept(suggestion)
    await db.commit()

    # Reload with relationship
    suggestion = await repo.get_by_id(suggestion_id)
    return _to_response(suggestion)


@router.post("/{suggestion_id}/reject", response_model=MatchSuggestionResponse)
async def reject_suggestion(
    suggestion_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MatchSuggestionResponse:
    repo = MatchSuggestionRepository(db)
    suggestion = await repo.get_by_id(suggestion_id)
    if not suggestion:
        raise NotFoundError("Suggestion not found")

    await repo.reject(suggestion)
    await db.commit()

    suggestion = await repo.get_by_id(suggestion_id)
    return _to_response(suggestion)
