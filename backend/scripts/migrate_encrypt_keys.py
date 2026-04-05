#!/usr/bin/env python3
"""One-time migration: re-encrypt all plaintext API keys in the database."""

import asyncio

from app.core.database import async_session_factory
from app.core.encryption import encrypt_api_key
from app.models.model_config import ModelConfig


async def main() -> None:
    async with async_session_factory() as session:
        from sqlalchemy import select

        result = await session.execute(select(ModelConfig))
        configs = list(result.scalars().all())

        migrated = 0
        for mc in configs:
            if mc.api_key_encrypted and not mc.api_key_encrypted.startswith("gAAAA"):
                mc.api_key_encrypted = encrypt_api_key(mc.api_key_encrypted)
                migrated += 1

        if migrated:
            await session.commit()
            print(f"Re-encrypted {migrated} plaintext API key(s)")
        else:
            print("All API keys are already encrypted")


if __name__ == "__main__":
    asyncio.run(main())
