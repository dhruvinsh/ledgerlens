"""Tests for MatchingService — correctness and cache behaviour."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.canonical_item import CanonicalItem
from app.models.line_item import LineItem
from app.services.matching import MatchingService


def _make_item(name: str, aliases: list[str] | None = None, item_id: str | None = None) -> CanonicalItem:
    # Names stored in DB are title-cased (normalize_item_name always title-cases)
    item = CanonicalItem()
    item.id = item_id or f"id-{name}"
    item.name = name
    item.aliases = aliases or []
    return item


def _make_line_item(name: str = "test item") -> LineItem:
    li = LineItem()
    li.id = "li-1"
    li.name = name
    li.canonical_item_id = None
    return li


def _make_service(existing_items: list[CanonicalItem]) -> tuple[MatchingService, MagicMock]:
    """Return a MatchingService with a mocked repo pre-seeded with existing_items."""
    db = MagicMock()
    db.add = MagicMock()

    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=existing_items)
    repo.get_by_name = AsyncMock(return_value=None)
    repo.get_by_alias = AsyncMock(return_value=None)
    repo.create = AsyncMock(side_effect=lambda item: item)
    repo.update = AsyncMock()

    svc = MatchingService(db)
    svc.item_repo = repo
    return svc, repo


# ── Resolution order ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_exact_name_match():
    milk = _make_item("milk")
    svc, _ = _make_service([milk])
    li = _make_line_item()
    result = await svc.find_or_create_canonical_item("Milk", li)
    assert result is milk
    assert li.canonical_item_id == milk.id


@pytest.mark.asyncio
async def test_exact_alias_match():
    item = _make_item("whole milk", aliases=["milk 2l", "full cream milk"])
    svc, _ = _make_service([item])
    li = _make_line_item()
    result = await svc.find_or_create_canonical_item("Milk 2L", li)
    assert result is item
    assert li.canonical_item_id == item.id


@pytest.mark.asyncio
async def test_fuzzy_auto_link():
    # Item stored with title-cased name (as normalize_item_name produces).
    # Input "Wholesome Milk" normalizes to "Wholesome Milk" — distinct from "Whole Milk",
    # so it won't be caught by exact-name or exact-alias steps before reaching fuzzy.
    item = _make_item("Whole Milk")
    svc, repo = _make_service([item])
    li = _make_line_item()

    with (
        patch("app.services.matching.fuzz.token_sort_ratio", return_value=88),
        patch("app.services.matching.fuzz.partial_ratio", return_value=88),
        patch("app.services.matching.settings") as mock_settings,
    ):
        mock_settings.FUZZY_AUTO_LINK_THRESHOLD = 85
        mock_settings.FUZZY_SUGGEST_THRESHOLD = 60
        result = await svc.find_or_create_canonical_item("Wholesome Milk", li)

    assert result is item
    assert li.canonical_item_id == item.id
    repo.update.assert_called_once()  # alias "Wholesome Milk" was added


@pytest.mark.asyncio
async def test_no_match_creates_new_item():
    svc, repo = _make_service([])
    li = _make_line_item("dragon fruit")

    with patch("app.services.matching.settings") as mock_settings:
        mock_settings.FUZZY_AUTO_LINK_THRESHOLD = 85
        mock_settings.FUZZY_SUGGEST_THRESHOLD = 60
        result = await svc.find_or_create_canonical_item("dragon fruit", li)

    assert result is not None
    assert result.name == "Dragon Fruit"  # normalize_item_name title-cases
    repo.create.assert_called_once()
    assert li.canonical_item_id == result.id


# ── Cache behaviour ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_all_called_only_once_for_multiple_items():
    """list_all() must be called exactly once regardless of how many items are processed."""
    existing = [_make_item("butter"), _make_item("eggs"), _make_item("bread")]
    svc, repo = _make_service(existing)

    with patch("app.services.matching.settings") as mock_settings:
        mock_settings.FUZZY_AUTO_LINK_THRESHOLD = 85
        mock_settings.FUZZY_SUGGEST_THRESHOLD = 60
        for name in ("butter", "eggs", "bread", "milk", "cheese"):
            await svc.find_or_create_canonical_item(name)

    repo.list_all.assert_called_once()


@pytest.mark.asyncio
async def test_newly_created_item_visible_to_next_iteration():
    """An item created in iteration N must be matched by iteration N+1 without a DB call."""
    svc, repo = _make_service([])  # start empty

    with patch("app.services.matching.settings") as mock_settings:
        mock_settings.FUZZY_AUTO_LINK_THRESHOLD = 85
        mock_settings.FUZZY_SUGGEST_THRESHOLD = 60

        # First call — no match, creates "apple juice"
        li1 = _make_line_item()
        li1.id = "li-1"
        r1 = await svc.find_or_create_canonical_item("apple juice", li1)

        # Second call — should hit the in-memory cache, not the DB
        li2 = _make_line_item()
        li2.id = "li-2"
        r2 = await svc.find_or_create_canonical_item("Apple Juice", li2)

    # Both resolve to the same canonical item
    assert r1 is r2
    # list_all still called only once
    repo.list_all.assert_called_once()
    # create called only once (second call hit the cache)
    repo.create.assert_called_once()
