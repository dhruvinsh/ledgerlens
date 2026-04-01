from collections.abc import AsyncGenerator

import httpx
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.main import app


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_engine) -> AsyncGenerator[httpx.AsyncClient, None]:
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(client: httpx.AsyncClient) -> httpx.AsyncClient:
    """A client already authenticated as admin (first user)."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "admin@test.com", "display_name": "Admin", "password": "testpass123"},
    )
    assert resp.status_code == 201
    cookie = resp.cookies.get("session_id")
    assert cookie is not None
    client.cookies.set("session_id", cookie)
    return client
