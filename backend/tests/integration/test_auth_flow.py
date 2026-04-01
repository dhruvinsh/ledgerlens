import httpx
import pytest


@pytest.mark.asyncio
async def test_register_first_user_is_admin(client: httpx.AsyncClient):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "first@test.com", "display_name": "First", "password": "secret123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "first@test.com"
    assert data["role"] == "admin"
    assert data["display_name"] == "First"
    assert "session_id" in resp.cookies


@pytest.mark.asyncio
async def test_register_second_user_is_member(client: httpx.AsyncClient):
    # First user
    await client.post(
        "/api/v1/auth/register",
        json={"email": "first@test.com", "display_name": "First", "password": "secret"},
    )
    # Second user — new client without cookies
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "second@test.com", "display_name": "Second", "password": "secret"},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "member"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: httpx.AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "dup@test.com", "display_name": "A", "password": "secret"},
    )
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "dup@test.com", "display_name": "B", "password": "secret"},
    )
    assert resp.status_code == 409
    assert "already registered" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_success(client: httpx.AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "login@test.com", "display_name": "L", "password": "pass123"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@test.com", "password": "pass123"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "login@test.com"
    assert "session_id" in resp.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(client: httpx.AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "bad@test.com", "display_name": "B", "password": "correct"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "bad@test.com", "password": "wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_authenticated(auth_client: httpx.AsyncClient):
    resp = await auth_client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@test.com"


@pytest.mark.asyncio
async def test_me_unauthenticated(client: httpx.AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout(auth_client: httpx.AsyncClient):
    resp = await auth_client.post("/api/v1/auth/logout")
    assert resp.status_code == 200

    # After logout, /me should fail
    auth_client.cookies.clear()
    resp = await auth_client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_requires_cookie(client: httpx.AsyncClient):
    # /items requires auth (not a public endpoint)
    resp = await client.get("/api/v1/items")
    assert resp.status_code == 401
