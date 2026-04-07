"""Tests for line item PATCH endpoint — ownership and access control."""

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import create_receipt, create_line_item, create_user


@pytest.mark.asyncio
async def test_update_own_line_item(auth_client: httpx.AsyncClient, db_session: AsyncSession):
    """Owner can update a line item on their own receipt."""
    # auth_client is already registered as admin; create a receipt via API
    create_resp = await auth_client.post(
        "/api/v1/receipts/manual",
        json={
            "total": 1000,
            "line_items": [{"name": "Milk", "quantity": 1, "total_price": 499}],
        },
    )
    assert create_resp.status_code == 201
    receipt_data = create_resp.json()
    line_item_id = receipt_data["line_items"][0]["id"]

    resp = await auth_client.patch(
        f"/api/v1/line-items/{line_item_id}",
        json={"name": "Milk 2L", "total_price": 549},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Milk 2L"
    assert data["total_price"] == 549
    assert data["is_corrected"] is True


@pytest.mark.asyncio
async def test_update_line_item_on_other_users_receipt_returns_404(
    client: httpx.AsyncClient, db_session: AsyncSession
):
    """A user cannot update a line item belonging to another user's receipt."""
    # Create user A with a receipt + line item directly in DB
    user_a = await create_user(db_session, email="usera@test.com")
    receipt_a = await create_receipt(db_session, user=user_a)
    li = await create_line_item(db_session, receipt=receipt_a, name="Secret Item")
    await db_session.commit()

    # Register and authenticate user B
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "userb@test.com", "display_name": "User B", "password": "pass123"},
    )
    assert reg.status_code == 201
    client.cookies.set("session_id", reg.cookies["session_id"])

    # User B tries to modify user A's line item
    resp = await client.patch(
        f"/api/v1/line-items/{li.id}",
        json={"name": "Tampered"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_nonexistent_line_item_returns_404(auth_client: httpx.AsyncClient):
    """Patching a completely non-existent ID returns 404."""
    resp = await auth_client.patch(
        "/api/v1/line-items/00000000-0000-0000-0000-000000000000",
        json={"name": "Ghost"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_line_item_partial_fields(auth_client: httpx.AsyncClient, db_session: AsyncSession):
    """Only provided fields are updated; others remain unchanged."""
    create_resp = await auth_client.post(
        "/api/v1/receipts/manual",
        json={
            "total": 800,
            "line_items": [{"name": "Eggs", "quantity": 2, "unit_price": 300, "total_price": 600}],
        },
    )
    assert create_resp.status_code == 201
    li_id = create_resp.json()["line_items"][0]["id"]

    resp = await auth_client.patch(
        f"/api/v1/line-items/{li_id}",
        json={"unit_price": 350},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["unit_price"] == 350
    assert data["name"] == "Eggs"       # unchanged
    assert data["quantity"] == 2.0      # unchanged
    assert data["total_price"] == 600   # unchanged
