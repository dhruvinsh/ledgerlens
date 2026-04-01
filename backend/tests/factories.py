import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.core.time import utc_now
from app.models.canonical_item import CanonicalItem
from app.models.line_item import LineItem
from app.models.receipt import Receipt
from app.models.store import Store
from app.models.user import User


async def create_user(
    db: AsyncSession,
    email: str = "user@test.com",
    display_name: str = "Test User",
    password: str = "testpass",
    role: str = "member",
) -> User:
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        display_name=display_name,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    await db.flush()
    return user


async def create_store(
    db: AsyncSession,
    name: str = "Test Store",
    created_by: str | None = None,
) -> Store:
    store = Store(
        id=str(uuid.uuid4()),
        name=name,
        created_by=created_by or str(uuid.uuid4()),
    )
    db.add(store)
    await db.flush()
    return store


async def create_receipt(
    db: AsyncSession,
    user: User,
    store: Store | None = None,
    total: int = 1000,
    status: str = "processed",
) -> Receipt:
    receipt = Receipt(
        id=str(uuid.uuid4()),
        user_id=user.id,
        household_id=user.household_id,
        store_id=store.id if store else None,
        transaction_date=date(2026, 3, 15),
        currency="CAD",
        total=total,
        source="manual",
        status=status,
    )
    db.add(receipt)
    await db.flush()
    return receipt


async def create_line_item(
    db: AsyncSession,
    receipt: Receipt,
    name: str = "Test Item",
    total_price: int = 500,
    canonical_item: CanonicalItem | None = None,
) -> LineItem:
    li = LineItem(
        id=str(uuid.uuid4()),
        receipt_id=receipt.id,
        name=name,
        quantity=1.0,
        total_price=total_price,
        canonical_item_id=canonical_item.id if canonical_item else None,
        position=0,
        created_at=utc_now(),
    )
    db.add(li)
    await db.flush()
    return li


async def create_canonical_item(
    db: AsyncSession,
    name: str = "Canonical Item",
    category: str | None = None,
) -> CanonicalItem:
    item = CanonicalItem(
        id=str(uuid.uuid4()),
        name=name,
        category=category,
        aliases=[],
    )
    db.add(item)
    await db.flush()
    return item
