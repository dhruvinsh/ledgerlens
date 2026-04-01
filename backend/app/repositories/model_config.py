from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model_config import ModelConfig


class ModelConfigRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, config_id: str) -> ModelConfig | None:
        result = await self.db.execute(
            select(ModelConfig).where(ModelConfig.id == config_id)
        )
        return result.scalar_one_or_none()

    async def get_active(self) -> ModelConfig | None:
        """Return the single active model."""
        result = await self.db.execute(
            select(ModelConfig).where(ModelConfig.is_active == True).limit(1)  # noqa: E712
        )
        return result.scalar_one_or_none()

    async def deactivate_all(self) -> None:
        """Set is_active=False on all models."""
        await self.db.execute(
            update(ModelConfig).values(is_active=False)
        )

    async def list_all(self) -> list[ModelConfig]:
        result = await self.db.execute(
            select(ModelConfig).order_by(ModelConfig.name)
        )
        return list(result.scalars().all())

    async def create(self, config: ModelConfig) -> ModelConfig:
        self.db.add(config)
        await self.db.flush()
        return config

    async def update(self, config: ModelConfig) -> None:
        await self.db.flush()

    async def delete(self, config: ModelConfig) -> None:
        await self.db.delete(config)
        await self.db.flush()
