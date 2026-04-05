import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_api_key, encrypt_api_key
from app.core.exceptions import NotFoundError
from app.core.time import utc_now
from app.models.model_config import ModelConfig
from app.repositories.model_config import ModelConfigRepository
from app.schemas.admin import ModelConfigCreate, ModelConfigUpdate

logger = logging.getLogger(__name__)


class AdminService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ModelConfigRepository(db)

    async def list_models(self) -> list[ModelConfig]:
        return await self.repo.list_all()

    async def get_model(self, config_id: str) -> ModelConfig:
        mc = await self.repo.get_by_id(config_id)
        if not mc:
            raise NotFoundError(f"Model config {config_id} not found")
        return mc

    async def create_model(self, data: ModelConfigCreate) -> ModelConfig:
        if data.is_active:
            await self.repo.deactivate_all()
        mc = ModelConfig(
            name=data.name,
            provider_type=data.provider_type,
            base_url=data.base_url,
            model_name=data.model_name,
            api_key_encrypted=encrypt_api_key(data.api_key) if data.api_key else None,
            is_active=data.is_active,
            supports_vision=data.supports_vision,
            timeout_seconds=data.timeout_seconds,
            max_retries=data.max_retries,
        )
        await self.repo.create(mc)
        await self.db.commit()
        return mc

    async def update_model(self, config_id: str, data: ModelConfigUpdate) -> ModelConfig:
        mc = await self.get_model(config_id)

        if data.name is not None:
            mc.name = data.name
        if data.provider_type is not None:
            mc.provider_type = data.provider_type
        if data.base_url is not None:
            mc.base_url = data.base_url
        if data.model_name is not None:
            mc.model_name = data.model_name
        if data.api_key is not None:
            mc.api_key_encrypted = encrypt_api_key(data.api_key)
        if data.is_active is not None:
            if data.is_active:
                await self.repo.deactivate_all()
                self.db.expire(mc, ["is_active"])
            mc.is_active = data.is_active
        if data.timeout_seconds is not None:
            mc.timeout_seconds = data.timeout_seconds
        if data.max_retries is not None:
            mc.max_retries = data.max_retries
        if data.supports_vision is not None:
            mc.supports_vision = data.supports_vision

        await self.repo.update(mc)
        await self.db.commit()
        return mc

    async def delete_model(self, config_id: str) -> None:
        mc = await self.get_model(config_id)
        await self.repo.delete(mc)
        await self.db.commit()

    async def test_model(self, config_id: str) -> dict[str, str]:
        mc = await self.get_model(config_id)

        try:
            headers = {}
            if mc.api_key_encrypted:
                headers["Authorization"] = f"Bearer {decrypt_api_key(mc.api_key_encrypted)}"
            async with httpx.AsyncClient(timeout=mc.timeout_seconds) as client:
                resp = await client.get(f"{mc.base_url}/models", headers=headers)
                resp.raise_for_status()

            mc.health_status = "healthy"
            mc.last_health_check = utc_now()
            await self.repo.update(mc)
            await self.db.commit()
            return {"status": "healthy"}

        except Exception as e:
            mc.health_status = "unhealthy"
            mc.last_health_check = utc_now()
            await self.repo.update(mc)
            await self.db.commit()
            return {"status": "unhealthy", "error": str(e)}
