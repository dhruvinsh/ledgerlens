from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.user import User
from app.schemas.admin import ModelConfigCreate, ModelConfigResponse, ModelConfigUpdate
from app.services.admin import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


def _to_response(mc) -> ModelConfigResponse:  # type: ignore[no-untyped-def]
    return ModelConfigResponse(
        id=mc.id,
        name=mc.name,
        provider_type=mc.provider_type,
        base_url=mc.base_url,
        model_name=mc.model_name,
        is_active=mc.is_active,
        is_default=mc.is_default,
        timeout_seconds=mc.timeout_seconds,
        max_retries=mc.max_retries,
        health_status=mc.health_status,
        last_health_check=mc.last_health_check.isoformat() if mc.last_health_check else None,
        created_at=mc.created_at.isoformat(),
    )


@router.get("/models", response_model=list[ModelConfigResponse])
async def list_models(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[ModelConfigResponse]:
    svc = AdminService(db)
    models = await svc.list_models()
    return [_to_response(m) for m in models]


@router.post("/models", response_model=ModelConfigResponse, status_code=201)
async def create_model(
    body: ModelConfigCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ModelConfigResponse:
    svc = AdminService(db)
    mc = await svc.create_model(body)
    return _to_response(mc)


@router.patch("/models/{config_id}", response_model=ModelConfigResponse)
async def update_model(
    config_id: str,
    body: ModelConfigUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ModelConfigResponse:
    svc = AdminService(db)
    mc = await svc.update_model(config_id, body)
    return _to_response(mc)


@router.delete("/models/{config_id}", status_code=200)
async def delete_model(
    config_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    svc = AdminService(db)
    await svc.delete_model(config_id)
    return {"detail": "Model config deleted"}


@router.post("/models/{config_id}/test", status_code=200)
async def test_model(
    config_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    svc = AdminService(db)
    return await svc.test_model(config_id)
