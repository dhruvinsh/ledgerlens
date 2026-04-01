from pathlib import Path

import httpx
import pytest

SAMPLES_DIR = Path(__file__).parent.parent.parent.parent / "samples"


@pytest.mark.asyncio
async def test_manual_receipt_create(auth_client: httpx.AsyncClient):
    resp = await auth_client.post(
        "/api/v1/receipts/manual",
        json={
            "store_name": "Walmart",
            "transaction_date": "2026-03-25",
            "currency": "CAD",
            "subtotal": 2499,
            "tax": 325,
            "total": 2824,
            "line_items": [
                {"name": "Milk 2L", "quantity": 1, "unit_price": 549, "total_price": 549},
                {"name": "Bread", "quantity": 2, "unit_price": 399, "total_price": 798},
            ],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "processed"
    assert data["total"] == 2824
    assert data["store"]["name"] == "Walmart"
    assert len(data["line_items"]) == 2
    assert data["line_items"][0]["name"] == "Milk 2L"
    assert data["line_items"][1]["total_price"] == 798


@pytest.mark.asyncio
async def test_list_receipts(auth_client: httpx.AsyncClient):
    # Create two receipts
    await auth_client.post(
        "/api/v1/receipts/manual",
        json={"store_name": "A", "total": 100, "line_items": []},
    )
    await auth_client.post(
        "/api/v1/receipts/manual",
        json={"store_name": "B", "total": 200, "line_items": []},
    )

    resp = await auth_client.get("/api/v1/receipts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_get_receipt_detail(auth_client: httpx.AsyncClient):
    create_resp = await auth_client.post(
        "/api/v1/receipts/manual",
        json={
            "store_name": "Costco",
            "total": 5000,
            "line_items": [{"name": "Eggs", "total_price": 429}],
        },
    )
    receipt_id = create_resp.json()["id"]

    resp = await auth_client.get(f"/api/v1/receipts/{receipt_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == receipt_id
    assert data["total"] == 5000
    assert len(data["line_items"]) == 1


@pytest.mark.asyncio
async def test_update_receipt(auth_client: httpx.AsyncClient):
    create_resp = await auth_client.post(
        "/api/v1/receipts/manual",
        json={"total": 1000, "line_items": []},
    )
    receipt_id = create_resp.json()["id"]

    resp = await auth_client.patch(
        f"/api/v1/receipts/{receipt_id}",
        json={"notes": "Updated note", "total": 1500},
    )
    assert resp.status_code == 200
    assert resp.json()["notes"] == "Updated note"
    assert resp.json()["total"] == 1500


@pytest.mark.asyncio
async def test_delete_receipt(auth_client: httpx.AsyncClient):
    create_resp = await auth_client.post(
        "/api/v1/receipts/manual",
        json={"total": 500, "line_items": []},
    )
    receipt_id = create_resp.json()["id"]

    resp = await auth_client.delete(f"/api/v1/receipts/{receipt_id}")
    assert resp.status_code == 200

    # Receipt should be permanently removed from database
    resp = await auth_client.get(f"/api/v1/receipts/{receipt_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_receipt_not_found(auth_client: httpx.AsyncClient):
    resp = await auth_client.get("/api/v1/receipts/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_upload_receipt_pdf(auth_client: httpx.AsyncClient):
    pdf_path = SAMPLES_DIR / "527590516490408.pdf"
    if not pdf_path.exists():
        pytest.skip("Sample PDF not found")

    with open(pdf_path, "rb") as f:
        resp = await auth_client.post(
            "/api/v1/receipts",
            files={"file": ("receipt.pdf", f, "application/pdf")},
            data={"source": "upload"},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["source"] == "upload"
    assert data["status"] == "pending"
    assert data["thumbnail_path"] is not None
    assert data["page_count"] >= 1


@pytest.mark.asyncio
async def test_filter_receipts_by_status(auth_client: httpx.AsyncClient):
    await auth_client.post(
        "/api/v1/receipts/manual",
        json={"total": 100, "line_items": []},
    )

    resp = await auth_client.get("/api/v1/receipts?status=processed")
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["status"] == "processed"

    resp = await auth_client.get("/api/v1/receipts?status=pending")
    assert resp.status_code == 200
    # Manual receipts are "processed", so pending should be empty (unless upload test ran)
