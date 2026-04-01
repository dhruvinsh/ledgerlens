"""Redis pub/sub bridge for pushing job status updates from Celery workers to FastAPI WebSocket clients."""

import asyncio
import json
import logging

import redis
import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

CHANNEL = "ledgerlens:job_updates"


def publish_job_update(
    user_id: str,
    job_id: str,
    status: str,
    receipt_id: str,
    stage: str | None = None,
    error_message: str | None = None,
) -> None:
    """Publish a job status update to Redis (synchronous — for use in Celery worker)."""
    try:
        r = redis.Redis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)
        payload = {
            "user_id": user_id,
            "job_id": job_id,
            "status": status,
            "receipt_id": receipt_id,
            "stage": stage,
            "error_message": error_message,
        }
        r.publish(CHANNEL, json.dumps(payload))
        r.close()
    except Exception:
        logger.warning("Failed to publish job update to Redis", exc_info=True)


async def start_job_update_subscriber() -> None:
    """Subscribe to Redis job updates and forward them to connected WebSocket clients.

    Runs as a long-lived asyncio task inside the FastAPI process.
    """
    from app.routers.ws import manager

    while True:
        try:
            async with aioredis.Redis.from_url(
                settings.CELERY_BROKER_URL, decode_responses=True
            ) as r:
                async with r.pubsub() as pubsub:
                    await pubsub.subscribe(CHANNEL)
                    logger.info(
                        "Subscribed to Redis channel %s for job updates", CHANNEL
                    )

                    async for message in pubsub.listen():
                        if message["type"] != "message":
                            continue
                        try:
                            data = json.loads(message["data"])
                            user_id = data.pop("user_id")
                            await manager.send_to_user(
                                user_id, {"type": "job_update", **data}
                            )
                        except Exception:
                            logger.warning(
                                "Failed to process job update message", exc_info=True
                            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning(
                "Redis subscriber disconnected, reconnecting in 2s", exc_info=True
            )
            await asyncio.sleep(2)
