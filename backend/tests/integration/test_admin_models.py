"""Integration tests for the admin model config endpoints."""
import pytest
import httpx


@pytest.mark.asyncio
async def test_list_models_empty(auth_client: httpx.AsyncClient):
    resp = await auth_client.get("/api/v1/admin/models")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_model_defaults(auth_client: httpx.AsyncClient):
    resp = await auth_client.post(
        "/api/v1/admin/models",
        json={
            "name": "Local Ollama",
            "provider_type": "openai",
            "base_url": "http://localhost:11434/v1",
            "model_name": "llama3.2",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Local Ollama"
    assert data["supports_vision"] is False
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_create_model_with_vision(auth_client: httpx.AsyncClient):
    resp = await auth_client.post(
        "/api/v1/admin/models",
        json={
            "name": "Vision Model",
            "provider_type": "openai",
            "base_url": "http://localhost:11434/v1",
            "model_name": "llama3.2-vision",
            "supports_vision": True,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["supports_vision"] is True


@pytest.mark.asyncio
async def test_list_models_includes_supports_vision(auth_client: httpx.AsyncClient):
    """Regression: _to_response() must include supports_vision or the endpoint 500s."""
    await auth_client.post(
        "/api/v1/admin/models",
        json={
            "name": "Test Model",
            "provider_type": "openai",
            "base_url": "http://localhost:11434/v1",
            "model_name": "llama3.2",
        },
    )
    resp = await auth_client.get("/api/v1/admin/models")
    assert resp.status_code == 200
    models = resp.json()
    assert len(models) == 1
    assert "supports_vision" in models[0]
    assert models[0]["supports_vision"] is False


@pytest.mark.asyncio
async def test_update_model_supports_vision(auth_client: httpx.AsyncClient):
    create_resp = await auth_client.post(
        "/api/v1/admin/models",
        json={
            "name": "Upgradeable",
            "provider_type": "openai",
            "base_url": "http://localhost:11434/v1",
            "model_name": "llama3.2",
            "supports_vision": False,
        },
    )
    assert create_resp.status_code == 201
    model_id = create_resp.json()["id"]

    patch_resp = await auth_client.patch(
        f"/api/v1/admin/models/{model_id}",
        json={"supports_vision": True},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["supports_vision"] is True


@pytest.mark.asyncio
async def test_update_model_supports_vision_to_false(auth_client: httpx.AsyncClient):
    create_resp = await auth_client.post(
        "/api/v1/admin/models",
        json={
            "name": "Vision Toggle",
            "provider_type": "openai",
            "base_url": "http://localhost:11434/v1",
            "model_name": "llava",
            "supports_vision": True,
        },
    )
    model_id = create_resp.json()["id"]

    patch_resp = await auth_client.patch(
        f"/api/v1/admin/models/{model_id}",
        json={"supports_vision": False},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["supports_vision"] is False
