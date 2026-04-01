import asyncio
import logging

from celery import Celery
from celery.signals import worker_process_init, worker_ready

from app.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "ledgerlens",
    broker=settings.CELERY_BROKER_URL,
    include=["app.tasks.receipt_processing"],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    task_soft_time_limit=settings.TASK_SOFT_TIME_LIMIT,
    task_time_limit=settings.TASK_HARD_TIME_LIMIT,
)


@worker_process_init.connect
def on_worker_process_init(**kwargs):  # type: ignore[no-untyped-def]
    """Verify Tesseract is available when worker process starts."""
    from app.services.ocr import verify_tesseract

    try:
        verify_tesseract()
        logger.info("Tesseract OCR verified")
    except RuntimeError as e:
        logger.error("Tesseract check failed: %s", e)


@worker_ready.connect
def on_worker_ready(**kwargs):  # type: ignore[no-untyped-def]
    """Recover orphaned jobs on worker startup."""
    asyncio.run(_recover_orphaned_jobs())


async def _recover_orphaned_jobs() -> None:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from app.core.time import utc_now
    from app.repositories.processing_job import ProcessingJobRepository

    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as db:
        repo = ProcessingJobRepository(db)

        # Mark stale running jobs as failed
        stale_running = await repo.get_orphaned_running(settings.TASK_HARD_TIME_LIMIT)
        for job in stale_running:
            job.status = "failed"
            job.error_message = "Orphaned — worker restarted"
            job.completed_at = utc_now()
            logger.warning("Marked orphaned running job %s as failed", job.id)

        # Redispatch stale queued jobs
        stale_queued = await repo.get_orphaned_queued(60)
        for job in stale_queued:
            from app.tasks.receipt_processing import process_receipt_task

            process_receipt_task.delay(job.id)
            logger.info("Redispatched orphaned queued job %s", job.id)

        await db.commit()

    await engine.dispose()
