import httpx
import pytest


@pytest.mark.asyncio
async def test_dashboard_summary_empty(auth_client: httpx.AsyncClient):
    resp = await auth_client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_receipts"] == 0
    assert data["total_spent"] == 0


@pytest.mark.asyncio
async def test_dashboard_summary_with_receipts(auth_client: httpx.AsyncClient):
    await auth_client.post(
        "/api/v1/receipts/manual",
        json={"store_name": "A", "transaction_date": "2026-03-10", "total": 5000, "line_items": []},
    )
    await auth_client.post(
        "/api/v1/receipts/manual",
        json={"store_name": "B", "transaction_date": "2026-03-15", "total": 3000, "line_items": []},
    )

    resp = await auth_client.get("/api/v1/dashboard/summary")
    data = resp.json()
    assert data["total_receipts"] == 2
    assert data["total_spent"] == 8000
    assert data["total_stores"] == 2
    assert data["avg_receipt_total"] == 4000


@pytest.mark.asyncio
async def test_spending_by_store(auth_client: httpx.AsyncClient):
    await auth_client.post(
        "/api/v1/receipts/manual",
        json={"store_name": "Walmart", "total": 5000, "line_items": []},
    )
    await auth_client.post(
        "/api/v1/receipts/manual",
        json={"store_name": "Costco", "total": 8000, "line_items": []},
    )

    resp = await auth_client.get("/api/v1/dashboard/spending-by-store")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    names = {d["store_name"] for d in data}
    assert "Walmart" in names
    assert "Costco" in names


@pytest.mark.asyncio
async def test_spending_by_month(auth_client: httpx.AsyncClient):
    await auth_client.post(
        "/api/v1/receipts/manual",
        json={"store_name": "A", "transaction_date": "2026-03-10", "total": 3000, "line_items": []},
    )

    resp = await auth_client.get("/api/v1/dashboard/spending-by-month")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["month"] == "2026-03"


@pytest.mark.asyncio
async def test_items_crud(auth_client: httpx.AsyncClient):
    # Items list should be empty initially
    resp = await auth_client.get("/api/v1/items")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_stores_list(auth_client: httpx.AsyncClient):
    await auth_client.post(
        "/api/v1/receipts/manual",
        json={"store_name": "Metro", "total": 1000, "line_items": []},
    )

    resp = await auth_client.get("/api/v1/stores")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    names = [s["name"] for s in data["items"]]
    assert "Metro" in names


@pytest.mark.asyncio
async def test_jobs_list(auth_client: httpx.AsyncClient):
    resp = await auth_client.get("/api/v1/jobs")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_suggestions_list(auth_client: httpx.AsyncClient):
    resp = await auth_client.get("/api/v1/suggestions")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_household_not_found_initially(auth_client: httpx.AsyncClient):
    resp = await auth_client.get("/api/v1/household")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_household_create_and_get(auth_client: httpx.AsyncClient):
    resp = await auth_client.post(
        "/api/v1/household",
        json={"name": "Test Family"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Family"
    assert len(data["users"]) == 1

    resp = await auth_client.get("/api/v1/household")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Family"
